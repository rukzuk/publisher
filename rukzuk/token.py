import json
import base64
import time

from . import openssl

import logging
logger = logging.getLogger(__name__)


class InvalidTokenException(Exception):
    pass


class Token(object):
    '''
    Generic authentication token
    '''
    REQUIRED_META_FIELDS = ['data', 'sign']
    REQUIRED_DATA_FIELDS = []

    def __init__(self, token_as_base64_string, sign_key, decryption_key=None):
        '''
        Constructor
        '''
        try:
            token_as_string = base64.b64decode(token_as_base64_string)
            token = json.loads(token_as_string)
        except:
            logger.exception('Malformed token detected')
            raise InvalidTokenException('Malformed token detected')

        self._verify_meta(token)
        self._verify_signature(sign_key, token)
        self._extract_data(token)
        if decryption_key is not None:
            self._decrypt(decryption_key)

        self.meta = token

    def _verify_meta(self, token):
        for field in self.REQUIRED_META_FIELDS:
            if field not in token:
                raise InvalidTokenException('Token meta field (%s) missing')

    def _verify_signature(self, sign_key, token):
        valid = openssl.verify_signature(token["data"],
                                         token["sign"],
                                         sign_key)
        if not valid:
            raise InvalidTokenException("Token signature is wrong")

    def _extract_data(self, token):
        data = json.loads(base64.b64decode(token["data"]))
        del token['data']
        del token['sign']
        for field in self.REQUIRED_DATA_FIELDS:
            if field not in data:
                raise InvalidTokenException('Token data field (%s) missing')
        self.data = data

    def _decrypt(self, key):
        """
        Decrypts the encrypted data field that should be part of a token.
        """
        if "encrypted" in self.data:
            try:
                crypted = self.data["encrypted"]
                del self.data["encrypted"]
                decrypted_data = json.loads(openssl.decrypt_data(crypted, key))
                # Add the encrypted data on top of the plain text data
                self.data = dict(list(self.data.items()) + list(decrypted_data.items()))
            except:
                raise InvalidTokenException('Could not decrypt token data')

    @staticmethod
    def generate_token(notsign, sign_dict, sign_key,
                       crypt_dict=None, enc_key=None):
        data = dict(sign_dict)
        data['created'] = int(time.time())
        if crypt_dict:
            data['encrypted'] = openssl.encrypt_data(json.dumps(crypt_dict),
                                                     enc_key)
        token_data = json.dumps(data).encode('base64')
        meta_data = dict(notsign) if notsign else dict()
        meta_data['data'] = token_data
        meta_data['sign'] = openssl.create_signature(token_data, sign_key)
        return json.dumps(meta_data).encode('base64')
