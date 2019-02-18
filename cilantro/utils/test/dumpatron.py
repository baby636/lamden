from cilantro.logger.base import get_logger
from cilantro.utils.test.god import God
from cilantro.constants.system_config import *
import os, glob
import random, requests


SSL_ENABLED = False  # TODO make this infered instead of a hard coded flag
CURRENCY_CONTRACT_NAME = 'currency'
IP_FILE_PREFIX = 'ip_masternode'


class Dumpatron:

    TX_PER_BLOCK = TRANSACTIONS_PER_SUB_BLOCK * NUM_SB_PER_BLOCK * NUM_BLOCKS
    STAMPS_AMOUNT = 10000

    def __init__(self, env_path):
        if env_path[-1] != '/':
            env_path += '/'
        assert os.path.exists(env_path), "No env dir found at path {}".format(env_path)
        assert os.path.exists(env_path + '.cache'), "No .cache dir found at path {}.cache".format(env_path)
        self.log = get_logger("Dumpatron")

        self.env_path = env_path
        self.mn_ip_dict = self._extract_mn_ips()
        self.mn_url_list = self._get_mn_urls_from_ips(self.mn_ip_dict)

        God.mn_urls = self.mn_url_list
        God.multi_master = True

    def _extract_mn_ips(self) -> dict:
        ips = {}
        pattern = "{}.cache/{}*".format(self.env_path, IP_FILE_PREFIX)
        mn_files = glob.glob(pattern)
        assert len(mn_files) > 0, "No masternode ip config files found matching glob pattern {} (did colin change the" \
                                  " way IPs are cached?)".format(pattern)

        for mn_file in mn_files:
            with open(mn_file, 'r') as f:
                mn_idx = mn_file[len(IP_FILE_PREFIX):]
                ips[mn_file[-1]] = f.read()
        return ips

    # TODO factor this out into its own function/module so it can be used in God as well
    def _get_mn_urls_from_ips(self, ips: dict) -> list:
        urls = []
        for ip in ips.values():
            if SSL_ENABLED:
                urls.append("https://{}".format(ip))
            else:
                urls.append("http://{}:8080".format(ip))
        return urls

    def dump(self, volume=1):
        God._dump_it(volume=volume)

    def start_interactive_dump(self):
        self.log.info("Starting the dump....")
        while True:
            user_input = input("Enter an integer representing the # of transactions to dump, or 'x' to quit. "
                               "Press enter to dump 1 blocks\n")

            if user_input.lower() == 'x':
                self.log.important("Termination input detected. Breaking")
                break

            vol = int(user_input) if user_input.isdigit() else self.TX_PER_BLOCK
            self.log.important3("Dumping {} transactions!".format(vol))
            God._dump_it(volume=vol)

    def _get_from_masternode(self, query_str: str, enforce_consistency=True, req_type='json'):
        if not enforce_consistency:
            mn_idx = random.randint(0, len(self.mn_url_list) - 1)
            mn_url = self.mn_url_list[mn_idx]
            return self._parse_reply(requests.get("{}/{}".format(mn_url, query_str)))

        replies = []
        for mn_url in self.mn_url_list:
            replies.append(self._parse_reply(requests.get("{}/{}".format(mn_url, query_str))))

        if all(x == replies[0] for x in replies):
            self.log.notice("replies matchup!")
            return replies[0]
        else:
            self.log.warning("Masternodes had inconsistent replies for GET request {}\nReplies: {}".format(query_str, replies))
            return None

    def _parse_reply(self, req, req_type='json'):
        if req.status_code != 200:
            self.log.spam("Got status code {} from request {}".format(req.status_code, req))
            return None

        if req_type == 'json':
            return req.json()
        else:
            raise Exception("Unknown request type {}".format(req_type))

    def _fetch_balance(self, vk, contract_name=CURRENCY_CONTRACT_NAME) -> int or None:
        req_url = "contracts/{}/balances/{}".format(contract_name, vk)
        ret_json = self._get_from_masternode(req_url)

        if ret_json:
            assert 'value' in ret_json, "Expected key 'value' to be in reply json {}".format(ret_json)
            return int(ret_json['value'])
        else:
            return None




