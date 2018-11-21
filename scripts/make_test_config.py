#!/usr/bin/env python3.6
import random
import argparse
import string
import configparser
from free_port import free_port
from random_password import random_password
from cilantro.constants.masternode import *

if __name__ == '__main__':
    random_pw = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(12))

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--username', default='lamden')
    parser.add_argument('--database', default='mn')
    parser.add_argument('--hostname', default='127.0.0.1')
    parser.add_argument('--output-file', default='./mn_db_conf.ini')
    parser.add_argument('--port', default=27017)
    args = parser.parse_args()

    conf = configparser.RawConfigParser()
    s = 'MN_DB'

    conf.add_section(s)
    conf.set(s, 'username', args.username)
    conf.set(s, 'password', random_password())
    conf.set(s, 'mn_blk_database', '{}_store'.format(args.database))
    conf.set(s, 'mn_cache_database', '{}_cache'.format(args.database))
    conf.set(s, 'hostname', args.hostname)
    conf.set(s, 'port', args.port)
    conf.set(s, 'replication', REP_FACTOR)
    conf.set(s, 'quorum', QUORUM)
    conf.set(s, 'total_mn', TEST_HOOK)

    with open(args.output_file, 'w') as f:
        conf.write(f)
