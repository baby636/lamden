# TODO this file could perhaps be named better
from cilantro.constants.system_config import TRANSACTIONS_PER_SUB_BLOCK
from cilantro.constants.zmq_filters import WITNESS_MASTERNODE_FILTER
from cilantro.constants.ports import MN_NEW_BLOCK_PUB_PORT, MN_TX_PUB_PORT
from cilantro.constants.system_config import BATCH_INTERVAL, MAX_SKIP_TURNS
from cilantro.messages.signals.master import SendNextBag

from cilantro.protocol.multiprocessing.worker import Worker
from cilantro.messages.transaction.ordering import OrderingContainer
from cilantro.messages.transaction.batch import TransactionBatch

import zmq.asyncio
import asyncio


class TransactionBatcher(Worker):

    def __init__(self, queue, ip, ipc_ip, ipc_port, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue, self.ip = queue, ip

        # Create Pub socket to broadcast to witnesses
        self.pub_sock = self.manager.create_socket(socket_type=zmq.PUB, name="TxBatcher-PUB", secure=True)
        self.pub_sock.bind(port=MN_TX_PUB_PORT, ip=self.ip)

        # Create DEALER socket to talk to the BlockManager process over IPC
        self.ipc_dealer = None
        self._create_dealer_ipc(port=ipc_port, ip=ipc_ip, identity=str(0).encode())

        # TODO create PAIR socket to orchestrate w/ main process?

        self.num_bags_sent = 0

        # Start main event loop
        self.loop.run_until_complete(self.compose_transactions())

    def _create_dealer_ipc(self, port: int, ip: str, identity: bytes):
        self.log.info("Connecting to BlockAggregator's ROUTER socket with a DEALER using ip {}, port {}, and id {}"
                      .format(ip, port, identity))
        self.ipc_dealer = self.manager.create_socket(socket_type=zmq.DEALER, name="Batcher-IPC-Dealer[{}]".format(0), secure=False)
        self.ipc_dealer.setsockopt(zmq.IDENTITY, identity)
        self.ipc_dealer.connect(port=port, protocol='ipc', ip=ip)

        self.tasks.append(self.ipc_dealer.add_handler(handler_func=self.handle_ipc_msg))

    def handle_ipc_msg(self, frames):
        self.log.spam("Got msg over Dealer IPC from BlockAggregator with frames: {}".format(frames))
        assert len(frames) == 2, "Expected 2 frames: (msg_type, msg_blob). Got {} instead.".format(frames)

        msg_type = bytes_to_int(frames[0])
        msg_blob = frames[1]

        msg = MessageBase.registry[msg_type].from_bytes(msg_blob)
        self.log.debugv("Batcher received an IPC message {}".format(msg))

        if isinstance(msg, SendNextBag):
            self.log.spam("Got SendNextBag notif from block aggregator!!!")
            self.num_bags_sent = self.num_bags_sent - 1

        else:
            raise Exception("Batcher got message type {} from IPC dealer socket that it does not know how to handle"
                            .format(type(msg)))

    async def compose_transactions(self):
        self.log.important("Starting TransactionBatcher")
        self.log.debugv("Current queue size is {}".format(self.queue.qsize()))

        while True:
            num_txns = self.queue.qsize()
            if ((num_txns < TRANSACTIONS_PER_SUB_BLOCK) and (num_bags_sent > 1)) or (num_bags_sent >= 3 * NUMBLOCKS):
                await asyncio.sleep(BATCH_SLEEP_INTERVAL)
                continue

            tx_list = []
            for _ in range(min(TRANSACTIONS_PER_SUB_BLOCK, num_txns)):
                tx = OrderingContainer.from_bytes(self.queue.get())
                # self.log.spam("masternode bagging transaction from sender {}".format(tx.transaction.sender))
                tx_list.append(tx)

            batch = TransactionBatch.create(transactions=tx_list)
            self.pub_sock.send_msg(msg=batch, header=WITNESS_MASTERNODE_FILTER.encode())
            self.num_bags_sent = self.num_bags_sent + NUM_BLOCKS
            if len(tx_list):
                self.log.info("Sending {} transactions in batch".format(len(tx_list)))
            else:
                self.log.info("Sending an empty transaction batch")

