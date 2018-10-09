import os, datetime, zmq, shutil
from cilantro.protocol import wallet
from os.path import basename, splitext, join, exists
from zmq.auth.thread import ThreadAuthenticator
from zmq.auth.asyncio import AsyncioAuthenticator
from zmq.utils.z85 import decode, encode
from nacl.public import PrivateKey, PublicKey
from nacl.signing import SigningKey, VerifyKey
from nacl.bindings import crypto_sign_ed25519_sk_to_curve25519
from cilantro.storage.db import VKBook
from cilantro.logger import get_logger
from cilantro.utils import lazy_property

class Auth:
    log = get_logger('Auth')
    @classmethod
    def setup_certs_dirs(cls, sk_hex, reset_auth_folder=False):
        cls.sk = sk_hex
        cls._sk = SigningKey(seed=bytes.fromhex(sk_hex))
        cls.vk = cls._sk.verify_key.encode().hex()
        cls.public_key = cls.vk2pk(cls.vk)
        cls.private_key = crypto_sign_ed25519_sk_to_curve25519(cls._sk._signing_key)
        cls.keyname = cls.public_key.hex()
        cls.base_dir = 'certs/{}'.format(os.getenv('HOST_NAME', cls.keyname))
        cls.default_domain_dir = 'authorized_keys'
        cls.authorized_keys_dir = join(cls.base_dir, cls.default_domain_dir)
        if reset_auth_folder and exists(cls.base_dir):
            shutil.rmtree(cls.base_dir)
        os.makedirs(cls.authorized_keys_dir, exist_ok=True)
        cls.add_public_key(public_key=cls.public_key)

    @classmethod
    def auth_validate(cls, vk, roles='any'):
        if roles == 'any':
            return vk in VKBook.get_all()
        else:
            if 'masternodes' in roles and vk in VKBook.get_masternodes():
                return True
            if 'witnesses' in roles and vk in VKBook.get_witnesses():
                return True
            if 'delegates' in roles and vk in VKBook.get_delegates():
                return True
        return False

    @classmethod
    def vk2pk(cls, vk):
        return encode(VerifyKey(bytes.fromhex(vk)).to_curve25519_public_key()._public_key)

    @classmethod
    def add_public_key(cls, public_key=None, vk=None, domain=None):
        assert public_key or vk, 'No public key or vk provided'
        if vk: public_key = cls.vk2pk(vk)
        public_key_filename = "{0}.key".format(public_key.hex())
        public_key_file = join(cls.base_dir, domain or cls.default_domain_dir, public_key_filename)
        now = datetime.datetime.now()
        zmq.auth.certs._write_key_file(public_key_file,
                        zmq.auth.certs._cert_public_banner.format(now),
                        public_key)

    @classmethod
    def remove_public_key(cls, public_key=None, vk=None, domain=None):
        assert public_key or vk, 'No public key or vk provided'
        if vk: public_key = cls.vk2pk(vk)
        public_key_filename = "{0}.key".format(public_key)
        public_key_file = join(cls.base_dir, domain or cls.default_domain_dir, public_key_filename)
        if exists(public_key_file):
            os.remove(public_key_file)

    @classmethod
    def configure_auth(cls, auth, domain='*'):
        location = location = self.authorized_keys_dir if domain == '*' else join(self.base_dir, domain)
        auth.configure_curve(domain=domain, location=location)