import unittest
import mock
from publisher.worker import collector


class TestableZipCollector(collector.ZIPCollector):

    def __init__(self, url_file_mock, url_content, zip_mock, is_zip=True):
        self.zip_mock = zip_mock
        self.url_file_mock = url_file_mock
        self.url_content = url_content
        self.is_zip = is_zip

    def _open_url(self, url):
        return mock.mock_open(self.url_file_mock, self.url_content)(url)

    def _open_zip(self, zdata):
        self.zip_mock(zdata)
        mock_context_manager = mock.Mock()
        mock_context_manager.__enter__ = lambda unused: self.zip_mock
        mock_context_manager.__exit__ = mock.Mock(return_value=False)
        return mock_context_manager

    def _is_zipfile(self, _zdata):
        return self.is_zip


class Test(unittest.TestCase):

    def test_normal_case(self):
        url_mock = mock.Mock()
        attrs = {'testzip.return_value': [],
                 'namelist.return_value': ['test.txt'], }
        zip_mock = mock.Mock(name="Zipfile mock", **attrs)
        col = TestableZipCollector(url_mock, "Testdata", zip_mock)
        col.collect(mock.sentinel.url, mock.sentinel.workdir)
        url_mock.assert_called_once_with(mock.sentinel.url)
        zip_mock.testzip.assert_any_call()
        zip_mock.namelist.assert_any_call()
        zip_mock.extractall.assert_called_with(mock.sentinel.workdir)
        calls = zip_mock.method_calls
        self.assertLess(calls.index(mock.call.testzip()),
                        calls.index(mock.call.extractall(mock.sentinel.workdir)),
                        "Zip file not tested before extraction")
        self.assertLess(calls.index(mock.call.namelist()),
                        calls.index(mock.call.extractall(mock.sentinel.workdir)),
                        "Zip file not tested before extraction")

    def test_bad_download(self):
        url_mock = mock.Mock(side_effect=Exception)
        attrs = {'testzip.return_value': [],
                 'namelist.return_value': ['test.txt'], }
        zip_mock = mock.Mock(name="Zipfile mock", **attrs)
        col = TestableZipCollector(url_mock, "Testdata", zip_mock)
        self.assertRaises(Exception, col.collect, mock.sentinel.url,
                          mock.sentinel.workdir)

    def test_bad_file(self):
        url_mock = mock.Mock()
        attrs = {'testzip.return_value': ['test.txt'],
                 'namelist.return_value': ['test.txt'], }
        zip_mock = mock.Mock(name="Zipfile mock", **attrs)
        col = TestableZipCollector(url_mock, "Testdata", zip_mock)
        self.assertRaises(Exception, col.collect, mock.sentinel.url,
                          mock.sentinel.workdir)

    def test_bad_filename(self):
        url_mock = mock.Mock()
        attrs = {'testzip.return_value': [],
                 'namelist.return_value': ['../test.txt'], }
        zip_mock = mock.Mock(name="Zipfile mock", **attrs)
        col = TestableZipCollector(url_mock, "Testdata", zip_mock)
        self.assertRaises(Exception, col.collect, mock.sentinel.url,
                          mock.sentinel.workdir)

    def test_no_zip(self):
        url_mock = mock.Mock()
        attrs = {'testzip.return_value': [],
                 'namelist.return_value': [], }
        zip_mock = mock.Mock(name="Zipfile mock", **attrs)
        col = TestableZipCollector(url_mock, "Testdata", zip_mock, False)
        self.assertRaises(Exception, col.collect, mock.sentinel.url,
                          mock.sentinel.workdir)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
