'''
Created on 07.02.2013

@author: mtrunner
'''
import unittest

import base64

from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from rukzuk import openssl


class OpenSSLTest(unittest.TestCase):

    PRIV_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEArJW5+FlnZMB42kjA1ZVwNGHNoC8nv94X2Vlu4XFiYv7jxzuA
0KgWzsJCihGv00tzOd+9VrX7rpzxfOiZzXppQhL7qi0035FiJ934NUlaXfJxrxV6
dgwQeMOm+TW1Kmil7AVMB5j6CsyqFu6O2FoFHAGKFa7lX68L+XvVWwMGl+CgKaa6
BLVQ/VvK+7WtMzphvcs1OQr+4A/1uKdlYQsUYAf4uzZyUc6fBOyFZP2iDSfVhK99
T3dL4hYtPREt3DDi8+fiV5R1w0SztUYOptq+ZdqwDKNG2yMvxKjJhZuJzzGQrwN6
2NTaoBCplFCCA/XBzk2xiudBx7pHyDVU6P0GLQIDAQABAoIBAQCEVK3q8kpoI3jH
Dt/lJReK4q8zMtUMtjOdMYjmjfT9qSloG4Ty+N+8G5G/oj4qCoFIj/jy4skfozE7
MHK17jWFN18GpnETN7uGjBmEakFDJeHreNGUcD21C3gdQAQwh1sp9QnODYsz+qg0
uyiGVcfzKG8Dnz47NtI8sqnuhgxpKM3fvPX5ALPzFd9jjjXDK2yFaN6DeVZaxotF
yPHdatbRGjcyiOK7YjwMw4f/y0B/w8SimJNZC6fXcTmY+9oWYbxOUMECLTPzNKKw
tRfia4NgA68MtcH7VXT450AK0kJ1+nV8raWBGrsYhqdpd4CqQHeF3131tC85tZ47
23aDX0IBAoGBANY47oWV0E/+kdrY7PXiH6YajZKD84oeFNkvuQ+F0E6j9ye929pi
fq7oDFpZhrGE/Vv/L9ItYfhHit9OaI2JxsE/Nt/xTI1n5BOCE4vWvW9rJze2pdN7
rLzLRnJ0urlbJsE+7uTdVuoXMnSF2515HoofshjnSz11Jy9puUODOUSBAoGBAM4+
CdrKtomx8LgvzBjfhfOqwMgiZ0qtXUFdrFGI0Y0KAANvmd64cgmuhbfC6JRWhkOX
DEUUFCZ8qPBBQJkD7PfiqxfVBwzDxPnvwiaBIjHy1cAIaHNSTTKvjflhCuNAIWQ6
4jyaGcG14OcLf0eUSPt21vUVCovA2W3bMVDIgDutAoGAEeIYz2ANTtBCntFjHres
yrIGxYdsakhOlz7rpQcXt6jqdg/cbaOxTaqjdVtp6iHfALIR7OrK9e4LAs9J3R72
T6WWUCWVrWxR1usR9KeNkuKQGI+P0lLNvcj+bYmfGOAqIRG+4a40lkAvfxi5l7DH
wuIYfQm59zxzc/rQc3ld64ECgYEApKIbRb8JxZL4gF8PQk+z4xXMPDZSU+deCN7Y
vmFEPZzc8+EzZ/m+doINFeqNtFP5a5z422+ywiJCzT6ZbUwX7qzPPP/9V7Ay3f0I
86mjfVHGVTug/WWWYD6JS6euhEdeIF9s10mABATG2khwOthhBfMQlqVMPNEd/7a4
gC79RiUCgYBeFnWfhcqSV4ZEuL9tL8YvtqikFiBQ064/UUQV666AkWUP5/fu6zwG
KjHL/oRX8H6KlfkG+ufeQQJDsHwhsqqLoidBUSMNBFjV5jqAqqwQH/MIxn+NbJTg
Fcgxdkt1/0mchmRXqeJeUCuEjF8QsGSxE0H8pbj9RqAu0T0ftg6C1w==
-----END RSA PRIVATE KEY-----
"""

    PUB_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArJW5+FlnZMB42kjA1ZVw
NGHNoC8nv94X2Vlu4XFiYv7jxzuA0KgWzsJCihGv00tzOd+9VrX7rpzxfOiZzXpp
QhL7qi0035FiJ934NUlaXfJxrxV6dgwQeMOm+TW1Kmil7AVMB5j6CsyqFu6O2FoF
HAGKFa7lX68L+XvVWwMGl+CgKaa6BLVQ/VvK+7WtMzphvcs1OQr+4A/1uKdlYQsU
YAf4uzZyUc6fBOyFZP2iDSfVhK99T3dL4hYtPREt3DDi8+fiV5R1w0SztUYOptq+
ZdqwDKNG2yMvxKjJhZuJzzGQrwN62NTaoBCplFCCA/XBzk2xiudBx7pHyDVU6P0G
LQIDAQAB
-----END PUBLIC KEY-----
"""

    PRIV_KEY2 = """-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAotHvSg1KKUO4Wm8dk3zn/0knfMcndBUEh87qIVE0BnNi0qPk
7xCeVqMQ9r1z7a3LlRyJzCN/gXTfon4/bZjb4JsFLWuJo6k8x5F6Kv06XwoI+rZd
KbA91itvgTy9VtSsjnX1fSmJ9JNWpY5gzLg+ISxS3YSLXTckIVxRmeR1YKkTPWji
qLCUzduq6NxcV8leJ2ymPZXA1xgz/lwMtPVbkHSYr9gLZ8N1zRg78UrA2hhY1hfM
5XsKVLommBwKAL145iBCxpTjFKAP/KfhNMBAfzLSIprQdGvKEASahDcLns4jRsjx
jSw0y6mi/OuF2wzmwYUr2fDyWj5zmbOk27c4+QIDAQABAoIBAH+6++L3HAfVNYnU
g7pRkdrms9Cil+PsHRrBi1FJ1+t7l7oxkwas3dqPoF5A7/I0lnJK6hs4ee3AFzTt
n6rF8TB5zIz+QQMgYCsbiGCzOZiXUcYFTH7I4Snj91zGnq7AtwInrcdbz/sLnzzP
vka7/xmdIQDg20fsWy7Esstsu1xw5un38wiwTTSsQsI02lD9bVfTKy3HN2+im0wX
LDy+6BmY+BNcjN+jTzOKt5Z3lqwITGfVG4axzm3zYF8Lhrvcl3dGJOFM2W+XhTIg
j5Tx57h8O05dOlNT8iksX8tcrNpk7EDKwv0KI5BSg3x7KOg1ROq9OIziSrA49akn
MyN3kHUCgYEAzpiDcGKCJlb6+jbLF2E4iGloMjc8c7v/JxQVskZQtYe7H6pgywmp
kBuvoDM6bbd3Dv+E4a3Iq90qafD/ne9BtvTK56SXWyzw++Yfhxu7T5m7i4JUqCAA
0WqA3kfijMs89z/C2Jr/SJo1cWqRGljHFlM45x6HNQotWGW7+rP7CIMCgYEAycGJ
rZqog58ZGTBDr+EPvsvkYbJBtpe+fM+nOT7kHstPRWyiLTszT/OiLuY5znWJCDr/
oTitD3taB1wg48Dh0kP2LRof2rpur/nsQLc+XmdhdSth9qI7l0fvq+KPqICxZlD9
tBYqRUkFPHdlqUeyDaLdEdQNJFERxOLzPyCL59MCgYAtEoUKjdNLPgq/cBja3vEQ
gb6jxf1AWrGN+wnIvSJ6mEQw4mD/qvn9YKzuTH7g1Pf6o7B/9AQlyrioKFX8ROiX
W8ywwO3sjF9+9XPHbDtvYGDUTPjfPSwwhAXdeN1qTiTc5GJEE3zCgDJMri0+DERT
EJEHi1eAMNo3wOpEBeQstQKBgC1iIawxe/KPmT+3QaKQh9AtYSQwyuNd4vWEaGNS
KFJc/Wnqc9ik1ngHn9XY5+vvOHHng5UqgJNY9flt2eAhhSqdKwUeOUgkY72mBGTS
U2885glLRvAJsknnXpxVjGck+8K+OTOHQN7w/AKMAQxBGmZC2mOmRYaDzfFx87Gh
ipcNAoGACwioFlqz5+mfyVDiPBNnHMVG1yZyaHPsPAoVqffYszRxp6wsIzhTtTsA
+go/wXRn48Rin8Xv+oxvxIlWwPB8QE8A7wTBzjsRQTnnNldLHquovlitbpN8jUh6
dBzpVkNN/+mbIRozpMtXGtgOGjgOctBuqHaOdFAEmS2wZ6Lcr7s=
-----END RSA PRIVATE KEY-----
"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_verify_signature_with_random_key(self):
        plaintext = "akdsjflakjsdflkajsf"
        key = RSA.generate(1024)

        h = SHA.new(plaintext)
        pkcs1 = PKCS1_v1_5.new(key)
        signature = pkcs1.sign(h).encode('base64')

        self.assertTrue(openssl.verify_signature(plaintext, signature, key),
                        "Self created signature verification failed")
        self.assertFalse(openssl.verify_signature(plaintext + "wrong message",
                                                signature,
                                                key),
                        "Signature matched on a manipulated string")

    def test_verify_signature(self):
        sig = """
Q1xDFj+7reOp4iUCtLFQQgo+ldh+k+VFq4VPBTZ8NdEHc1oHl93ZU7TUPQZXveetQ4d8c0luvfh1
CLCifXx9zaNtz0w/a3uFoqfBjLOm+jT/TO2iQGH6eLZAoBbDhVpEDna1CmNwMwDmcPYtYNuF0FvG
TGHxuKi/8L9dyV4a9P9LNyQU1qJPL/EhQO4sIPlMi9pgQskmZqAUKroX3JbyLc2G9vFeSJsEgrPF
Z8qXlpACUw4P9K3MRiD/S/4rHWXIXB9RXqVuIgVd64Jmjlh1UXNJEDzpul5rr+HYotWJIsIRmItk
qNzhBEQfiClphVHt4LViMp4S84XXEAITZSVU4g==
"""
        key = RSA.importKey(self.PUB_KEY)
        self.assertTrue(openssl.verify_signature("Bla bla", sig, key),
                        "Verification of the test signature failed")

        self.assertFalse(openssl.verify_signature("Bla bla2", sig, key),
                        "Test signature verified wrong message")

    def test_decrypt(self):
        data = "gp+uv3zFKwBXlTtpNXGjGivuL7z0EVwx7SWJEhnx6FQpX3mM8ASWZhQamWstyNWXckfe/p8IjG3QoWB3ebzKQvg17FptEYUU1ogYyhwJGCxx5MePESEH7c4NBv72dCfJQ995ijAUp2t7xmNwUsQsq2a0tOYVaW//VjvE0D0hbTogMgLjg5celhv3dHuMgS6aCmh3Ur4QBOXkOKtdCobu6K2B200q4xWIJU9Yr5hHYzTk4cKKSJAoR3+PoA8rLmHHJPuQyD95MdTa/x95ZbMRk/29LnzG15woyMIdLL1bxUBI3iDwpvjrg+y6uNupNNYKwffUDCWnrD4ryumSEBcQ/w=="""
        key = RSA.importKey(self.PRIV_KEY)
        result = openssl.decrypt_data(data, key)
        self.assertEqual(result, "Bla bla", "Decryption failed")

    def test_encrypt(self):
        key = RSA.importKey(self.PUB_KEY)
        key2 = RSA.importKey(self.PRIV_KEY)
        result = openssl.encrypt_data("Bla bla", key)
        self.assertEqual(openssl.decrypt_data(result, key2), "Bla bla",
                         "Can not decrypt the encryption result")

    def test_create_signature(self):
        data = "Bla bla"
        key = RSA.importKey(self.PRIV_KEY)
        sig = openssl.create_signature(data, key)
        pubkey = RSA.importKey(self.PUB_KEY)
        self.assertTrue(openssl.verify_signature(data, sig, pubkey),
                        "Couldn't verify created signature")
        test_sig = """Q1xDFj+7reOp4iUCtLFQQgo+ldh+k+VFq4VPBTZ8NdEHc1oHl93ZU7TUPQZXveetQ4d8c0luvfh1
CLCifXx9zaNtz0w/a3uFoqfBjLOm+jT/TO2iQGH6eLZAoBbDhVpEDna1CmNwMwDmcPYtYNuF0FvG
TGHxuKi/8L9dyV4a9P9LNyQU1qJPL/EhQO4sIPlMi9pgQskmZqAUKroX3JbyLc2G9vFeSJsEgrPF
Z8qXlpACUw4P9K3MRiD/S/4rHWXIXB9RXqVuIgVd64Jmjlh1UXNJEDzpul5rr+HYotWJIsIRmItk
qNzhBEQfiClphVHt4LViMp4S84XXEAITZSVU4g==
"""
        self.assertEqual(base64.b64decode(test_sig), base64.b64decode(sig),
                         "Signature differs from the test signature")
