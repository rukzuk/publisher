from django.test import SimpleTestCase
from django.test.client import Client
import mock
import json


class TestViews(SimpleTestCase):

    token = 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpbnN0YW5jZSI6Imh0dHBzOi8vdGVzdHNwYWNlXFwuZXhhbXBsZVxcLmNvbS8uKyIsImRvbWFpbiI6IlswLTlhLXpdK1xcLjE0eXllN2NuZGZ3cWRjM2UzeHc1ajllZzdcXC5leGFtcGxlXFwuY29tIiwidHlwZSI6ImludGVybmFsIn0._1vWdTbi_mQrT-U9rTWT1W6AFkipDJKhO88_I0-QRqGMD_Y9xcqopjACH_Lo2O8dGkL6wceHsxpX5lhVjHLdYQ'  # noqa

    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_get_job_state(self, as_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/status/'
        c = Client()

        # execute
        response = c.post(url, data={
            'client_version': 2,
            'token': self.token,
            'download_url': "https://testspace.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 200)

    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_get_job_state_no_token(self, as_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/status/'
        c = Client()

        # execute
        response = c.post(url, data={
            'client_version': 2,
            'download_url': "https://testspace.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 400)

    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_get_job_state_no_client_version(self, as_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/status/'
        c = Client()

        # execute
        response = c.post(url, data={
            'token': self.token,
            'download_url': "https://testspace.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 400)

    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_get_job_state_bad_dl_url(self, as_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/status/'
        c = Client()

        # execute
        response = c.post(url, data={
            'token': self.token,
            'download_url': "https://testspace2.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 400)

    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_get_job_state_bad_domain(self, as_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/status/'
        c = Client()

        # execute
        response = c.post(url, data={
            'token': self.token,
            'download_url': "https://testspace.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf2.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 400)

    @mock.patch('publisher.tasks.delete.delay')
    def test_delete(self, delay_mock):
        url = '/publisher/delete/'
        c = Client()

        # execute
        response = c.post(url, data={
            'client_version': 2,
            'token': self.token,
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": "xxx.de"
            })
        }, follow=True)

        # verify
        delay_mock.assert_called_once_with(
            'internal', {'domain': 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com', 'cname': 'xxx.de'})
        self.assertEqual(response.status_code, 200)

    @mock.patch('publisher.tasks.publish.apply_async')
    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_add_job(self, as_mock, apply_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/add/'
        c = Client()

        # execute
        response = c.post(url, data={
            'client_version': 2,
            'token': self.token,
            'download_url': "https://testspace.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 200)

    @mock.patch('publisher.tasks.publish.apply_async')
    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_add_job_no_client_version(self, as_mock, apply_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/add/'
        c = Client()

        # execute
        response = c.post(url, data={
            'token': self.token,
            'download_url': "https://testspace.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 400)

    @mock.patch('publisher.tasks.publish.apply_async')
    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_add_job_no_token(self, as_mock, apply_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/add/'
        c = Client()

        # execute
        response = c.post(url, data={
            'client_version': 2,
            'download_url': "https://testspace.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 400)

    @mock.patch('publisher.tasks.publish.apply_async')
    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_add_job_bad_dl_url(self, as_mock, apply_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/add/'
        c = Client()

        # execute
        response = c.post(url, data={
            'client_version': 2,
            'download_url': "https://testspace2.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 400)

    @mock.patch('publisher.tasks.publish.apply_async')
    @mock.patch('publisher.tasks.publish.AsyncResult')
    def test_add_job_bad_domain(self, as_mock, apply_mock):
        as_mock.return_value.state = "PENDING"
        url = '/publisher/add/'
        c = Client()

        # execute
        response = c.post(url, data={
            'client_version': 2,
            'download_url': "https://testspace.example.com/dl",
            'data': json.dumps({
                "test_url": 'dsfg',
                "domain": 'asdf.14yye7cndfwqdc3e3xw5j9eg7.example2.com',
                "cname": ""
            })
        }, follow=True)

        # verify
        self.assertEqual(response.status_code, 400)
