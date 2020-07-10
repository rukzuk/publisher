'''
Created on 30.01.2013

@author: mtrunner
'''
import unittest
from mock import Mock
from publisher.worker.managers.backends import FTPUploadBackEnd, FTPLineParser


class FTPBackEndTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_no_init_connect(self):
        m = Mock(return_value=None)
        FTPUploadBackEnd.connect = m
        ftp = FTPUploadBackEnd('server', 'user', 'pass', 'basedir', 21)
        self.assertEqual(m.call_count, 0,
                         "Connection should not started on __init__")
        ftp.connect()
        m.assert_called_once_with()

    def test_reconnect_not_triggered(self):
        ftp = FTPUploadBackEnd('server', 'user', 'pass', 'basedir', 21)
        ftp._ftp.cwd = Mock()
        ftp._ftp.dir = Mock(return_value=[])
        ftp.exists('test')
        self.assertEqual(ftp._ftp.dir.call_count, 1, "Test")

    def test_reconnect_only_once(self):
        ftp = FTPUploadBackEnd('server', 'user', 'pass', 'basedir', 21)
        ftp._ftp.cwd = Mock()
        ftp._ftp.dir = Mock(side_effect=Exception('Boom!'))
        with self.assertRaises(Exception):
            ftp.dir('test')
        self.assertEqual(ftp._ftp.dir.call_count, 2, "Test")

    def test_reconnect_triggered(self):
        ftp = FTPUploadBackEnd('server', 'user', 'pass', 'basedir', 21)
        ftp._list = Mock(side_effect=[Exception('Boom!'), [('test', '-')]])
        self.assertTrue('test' in ftp.dir(''))
        self.assertEqual(ftp._list.call_count, 2)


class FTPLineParserTest(unittest.TestCase):

    def test_parse_unix_result(self):
        parser = FTPLineParser()
        self.assertRaises(parser.LineFormatError, parser.parse, "xxxx")

    def test_linux_result(self):
        linux_line1 = ("drwxr-xr-x 2 mtrunner domnen-benutzer 4096 "
                       "30. Aug 10:29 test.txt")
        parser = FTPLineParser()
        n, t = parser.parse(linux_line1)
        self.assertEqual("test.txt", n)
        self.assertEqual("d", t)

    def test_msdos_result(self):
        msdos_line1 = '11-19-13  02:03AM       <DIR>          wwwlogs'
        parser = FTPLineParser()
        n, t = parser.parse(msdos_line1)
        self.assertEqual("wwwlogs", n)
        self.assertEqual("d", t)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
