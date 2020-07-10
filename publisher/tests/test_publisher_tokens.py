# coding=utf-8
from django.test import SimpleTestCase
from .. import token

import logging
logger = logging.getLogger(__name__)


class PublisherTokenTest(SimpleTestCase):

    external_token = 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpbnN0YW5jZSI6Imh0dHBzOi8vdGVzdHNwYWNlXFwuZXhhbXBsZVxcLmNvbS8uKyIsInR5cGUiOiJleHRlcm5hbCJ9.WDjjMzu4KH_rqisvnjhiTI_3bIgzHjO_XJDnLClxLsWauyEyiHqai65Op15IVmHLJrwYOeZGsrW_or0Nb0ZWKg'  # noqa
    internal_token = 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpbnN0YW5jZSI6Imh0dHBzOi8vdGVzdHNwYWNlXFwuZXhhbXBsZVxcLmNvbS8uKyIsImRvbWFpbiI6IlswLTlhLXpdK1xcLjE0eXllN2NuZGZ3cWRjM2UzeHc1ajllZzdcXC5leGFtcGxlXFwuY29tIiwidHlwZSI6ImludGVybmFsIn0.plPPakCp6-xVD062282Lr_-uTB6DSk9WjbI5gXm0zumReaLMWAATAnKTLVzFRMEZoezvTJqX5lMBH-9Twp73vg'  # noqa

    sut = token.PublisherTokenFactory("")

    def test_external_token(self):
        res = self.sut.create_token(self.external_token)

        request_data = {
            'protocol': "sftp",
            'username': "www-data",
            'basedir': "/srv/kunden",
            'chmod': "asdf",
            'host': "live.rukzuk.com",
            'password': "asdf",
            'port': 22
        }

        self.assertIsInstance(res, token.ExternalPublisherToken)
        self.assertEqual(res.get_protocol(request_data), "sftp")
        self.assertEqual(res.get_instance(), 'https://testspace\\.example\\.com/.+')
        self.assertTrue(res.validate_download_url("https://testspace.example.com/dl"))
        self.assertFalse(res.validate_download_url("https://testspace2.example.com/dl"))
        self.assertFalse(res.validate_download_url("https://testspace2.example.com/"))

        pps = res.get_protocol_parameters(request_data)
        self.assertEqual(pps['host'], request_data['host'])
        self.assertEqual(pps['port'], request_data['port'])
        self.assertEqual(pps['username'], request_data['username'])
        self.assertEqual(pps['basedir'], request_data['basedir'])
        self.assertEqual(pps['password'], request_data['password'])
        self.assertEqual(pps['chmod'], request_data['chmod'])

    def test_internal_token(self):
        res = self.sut.create_token(self.internal_token)

        request_data = {
            "cname": "aa.asdf.cc",
            "domain": "123.14yye7cndfwqdc3e3xw5j9eg7.example.com"
        }

        self.assertIsInstance(res, token.InternalPublisherToken)
        self.assertEqual(res.get_protocol(request_data), "internal")
        self.assertEqual(res.get_instance(), 'https://testspace\\.example\\.com/.+')
        self.assertTrue(res.validate_download_url("https://testspace.example.com/dl"))
        self.assertFalse(res.validate_download_url("https://testspace2.example.com/dl"))
        self.assertFalse(res.validate_download_url("https://testspace2.example.com/"))
        self.assertEqual(res.domain, '[0-9a-z]+\\.14yye7cndfwqdc3e3xw5j9eg7\\.example\\.com')

        pps = res.get_protocol_parameters(request_data)
        self.assertEqual(pps['cname'], request_data['cname'])
        self.assertEqual(pps['domain'], request_data['domain'])
