import base64

from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
import Crypto.Signature.PKCS1_v1_5
import Crypto.Cipher.PKCS1_OAEP


def create_signature(data, key, hash_algo=SHA):
    """
    Returns a base64 encoded signature for the given data created with the
    given key. The signature can be verified with the related public key.

    This method works like the PHP openssl_sign function.
    """
    pkcs1 = Crypto.Signature.PKCS1_v1_5.new(key)
    return base64.b64encode(pkcs1.sign(hash_algo.new(data)))


def verify_signature(data, signature_base64, key, hash_algo=SHA):
    """
    This method works like the PHP openssl_verify function.

    The signature must be encoded with base64.
    As hash function SHA1 is used.
    """
    pkcs1 = Crypto.Signature.PKCS1_v1_5.new(key)
    return pkcs1.verify(hash_algo.new(data), base64.b64decode(signature_base64))


def decrypt_data(data, key):
    """
    This method is designed to work like the PHP openssl_decrypt function.
    The data must be encoded with base64.

    Because PKCS#1 v1.5 (the PHP default padding (OPENSSL_PKCS1_PADDING) has
    some security problems, we require PKCS#1 OAEP (in PHP you have to use
    padding=OPENSSL_PKCS1_OAEP_PADDING).

    For more informations see Bleichenbacher's attack:
      http://www.bell-labs.com/user/bleichen/papers/pkcs.ps
    """
    pkcs1 = Crypto.Cipher.PKCS1_OAEP.new(key)
    return pkcs1.decrypt(base64.b64decode(data))


def encrypt_data(data, key):
    """
    Encrypts the given data with the given public key, so that it can only be
    decrypted with the relating private key.

    This method is designed to be compatible to the openssl_encrypt function
    from PHP.

    Because PKCS#1 v1.5 (the PHP default padding (OPENSSL_PKCS1_PADDING) has
    some security problems, we require PKCS#1 OAEP (in PHP you have to use
    padding=OPENSSL_PKCS1_OAEP_PADDING).

    For more informations see Bleichenbacher's attack:
      http://www.bell-labs.com/user/bleichen/papers/pkcs.ps
    """
    pkcs1 = Crypto.Cipher.PKCS1_OAEP.new(key)
    return base64.b64encode(pkcs1.encrypt(data))


def load_key(key_file):
    with open(key_file) as kf:
        return RSA.importKey(kf.read())

