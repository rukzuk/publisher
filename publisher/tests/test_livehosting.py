import unittest
import mock

from ..worker.exceptions import RetryException
from ..worker.managers import livehosting

import logging
logger = logging.getLogger(__name__)


class LiveHostingRsyncHelperTestCase(unittest.TestCase):

    def setUp(self):
        hostname = "liveserver1.test.case"
        username = "testuser"
        pkey_file = "/home/testuser/.ssh/id_rsa"
        basedir = "/srv/livehosting"
        # Act
        self.sut = livehosting.LiveHostingRsyncHelper(
            hostname, username, pkey_file, basedir)

    def test_init(self):
        # Arrange
        hostname = mock.sentinel.hostname
        username = mock.sentinel.username
        pkey_file = mock.sentinel.pkey_file
        basedir = mock.sentinel.basedir
        # Act
        rsync_helper = livehosting.LiveHostingRsyncHelper(hostname, username, pkey_file, basedir)
        # Assert
        self.assertEqual(rsync_helper.basedir, basedir)
        self.assertEqual(rsync_helper.username, username)
        self.assertEqual(rsync_helper.pkey_file, pkey_file)
        self.assertEqual(rsync_helper.hostname, hostname)

    def test_get_rsync_cmd(self):
        # Arrange
        source_dir = '/tmp/testcase/working_dir'
        destination_dir = 'asdf.yxcv.test.case'
        writeable_list = ['media', 'cache']
        # Act
        result = self.sut.get_rsync_cmd(source_dir, destination_dir, writeable_list)
        # Assert
        expected = ['rsync', '-rptogc', "-e 'ssh -i /home/testuser/.ssh/id_rsa'",
                    '--exclude media --exclude cache', '/tmp/testcase/working_dir',
                    'testuser@liveserver1.test.case:/srv/livehosting/asdf.yxcv.test.case']
        self.assertEqual(expected, result)

    def test_sync(self):
        # Arrange
        self.sut._call_chmod = mock.Mock()
        self.sut._call_rsync = mock.Mock()
        working_dir = '/tmp/testcase/working_dir'
        live_domain = 'asdf.yxcv.test.case'
        writeable_list = ['media']
        cache_list = ['cache']
        # Act
        self.sut.sync(working_dir, live_domain, writeable_list, cache_list)
        # Assert
        self.sut._call_rsync.assert_called_once_with(
            '/tmp/testcase/working_dir', 'asdf.yxcv.test.case', ['media'])
        self.sut._call_chmod.assert_has_calls(
            [mock.call('u+rwX,go+rX,go-w', '/tmp/testcase/working_dir', recursive=True),
             mock.call('go+w', '/tmp/testcase/working_dir/media'),
             mock.call('go+w', '/tmp/testcase/working_dir/cache')])

    @mock.patch('subprocess.check_call')
    def test_sync_integration(self, check_call_mock):
        # Arrange
        working_dir = '/tmp/testcase/working_dir'
        live_domain = 'asdf.yxcv.test.case'
        writeable_list = ['media']
        cache_list = ['cache']
        # Act
        self.sut.sync(working_dir, live_domain, writeable_list, cache_list)
        # Assert
        check_call_mock.assert_has_calls(
            [mock.call(' '.join(['chmod', 'u+rwX,go+rX,go-w', '-R', '/tmp/testcase/working_dir']),
                       shell=True),
             mock.call(' '.join(['chmod', 'go+w', '/tmp/testcase/working_dir/media']), shell=True),
             mock.call(' '.join(['chmod', 'go+w', '/tmp/testcase/working_dir/cache']), shell=True),
             mock.call(' '.join(
                 ['rsync', '-rptogc', "-e 'ssh -i /home/testuser/.ssh/id_rsa'",
                  '--exclude media', '/tmp/testcase/working_dir',
                  'testuser@liveserver1.test.case:/srv/livehosting/asdf.yxcv.test.case']),
                 shell=True)])


class LiveHostingManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.sftp_mock = mock.Mock()
        self.rsync_mock = mock.Mock()
        self.state_callback_mock = mock.Mock()
        self.live_domain = 'live2.zuk.io'
        self.live_cname = 'cname_live2.zuk.io'
        self.sut = livehosting.LiveHostingManager(
            self.live_domain, self.live_cname,
            self.sftp_mock, self.rsync_mock, self.state_callback_mock)

    def test_delete_livehosting(self):
        # Arrange
        self.sftp_mock.dir.return_value = ['cname_live2.zuk.io',
                                           'cname_live1.zuk.io',
                                           'live1.zuk.io',
                                           'live2.zuk.io',
                                           'live3.zuk.io']

        def readlink(link):
            if not link.startswith('cname'):
                return None
            return link.partition('_')[2]
        self.sftp_mock.readlink = readlink
        # Act
        self.sut.delete_all()
        # Assert
        self.sftp_mock.delete_file.assert_called_once_with('cname_live2.zuk.io')
        self.sftp_mock.exists.assert_called_once_with('live2.zuk.io')
        self.sftp_mock.erase_directory.assert_called_once_with('live2.zuk.io')
        self.sftp_mock.delete_directory.assert_called_once_with('live2.zuk.io')
        self.assertEqual(self.sut.live_domain, self.live_domain)
        self.assertEqual(self.sut.live_cname, self.live_cname)

    def test_delete_links(self):
        self.sftp_mock.dir.return_value = ['a']
        self.sut._delete_link = mock.Mock()

        # exec
        self.sut._delete_links(self.sftp_mock)

        # verify
        self.sut._delete_link.assert_called_with(self.sftp_mock, 'a')

    def test_delete_links_fail(self):
        self.sftp_mock.dir = mock.Mock(return_value=['a'])
        self.sut._delete_link = mock.Mock(side_effect=[livehosting.NotALink])

        # exec
        self.sut._delete_links(self.sftp_mock)

        # verify
        self.sut._delete_link.assert_called_with(self.sftp_mock, 'a')

    def test_delete_link(self):
        link = 'a'
        self.sftp_mock.readlink = mock.Mock(return_value='b')
        self.sftp_mock.delete_file = mock.Mock()
        self.sut.live_domain = 'b'

        # exec
        self.sut._delete_link(self.sftp_mock, link)

        # verify
        self.sftp_mock.delete_file.assert_called_with(link)

    def test_delete_link_no_link(self):
        link = 'a'
        self.sftp_mock.readlink = mock.Mock(return_value=None)

        # exec
        with self.assertRaises(Exception):
            self.sut._delete_link(self.sftp_mock, link)

    def test_start_success_mock(self):
        # Arrange
        working_dir = '/tmp/testcase/working_dir'
        writeable_list = ['media', 'uploads']
        cache_list = ['cache', 'media/cache']

        self.sftp_mock.dir.return_value = []
        self.sftp_mock.exists.return_value = False
        # Act
        self.sut.start(working_dir, None, writeable_list, cache_list)
        # Assert
        self.sftp_mock.exists.assert_has_calls(
            [mock.call(self.live_domain), mock.call(self.live_cname)])
        self.sftp_mock.symlink.assert_called_once_with(self.live_domain, self.live_cname)
        self.sftp_mock.quit.assert_called_once_with()
        self.rsync_mock.sync.assert_called_once_with(
            working_dir, self.live_domain, writeable_list, cache_list)
        self.state_callback_mock.assert_has_calls(
            [mock.call(self.sut.STATE_PREPARING, 0.25), mock.call(self.sut.STATE_CNAME, 0.5),
             mock.call(self.sut.STATE_SYNCING, 0.75)])

    def test_start_retry_exception(self):
        # Arrange
        working_dir = '/tmp/testcase/working_dir'
        writeable_list = ['media', 'uploads']
        cache_list = ['cache', 'media/cache']

        self.sftp_mock.dir_attr.side_effect = [Exception('TestCase')]
        self.sftp_mock.exists.return_value = False
        # Act
        self.assertRaises(livehosting.LiveHostingRetryException, self.sut.start,
                          working_dir, None, writeable_list, cache_list)
        # Assert
        self.assertFalse(self.rsync_mock.sync.called)
        self.sftp_mock.quit.assert_called_once_with()
        self.state_callback_mock.assert_has_calls(
            [mock.call(self.sut.STATE_PREPARING, 0.25), mock.call(self.sut.STATE_CNAME, 0.50)])

    def test_start_retry_exception_rsync(self):
        # Arrange
        working_dir = '/tmp/testcase/working_dir'
        writeable_list = ['media', 'uploads']
        cache_list = ['cache', 'media/cache']

        self.sftp_mock.dir.return_value = []
        self.sftp_mock.exists.return_value = False
        self.rsync_mock.sync.side_effect = [Exception('TestCase')]
        # Act
        self.assertRaises(livehosting.LiveHostingRetryException, self.sut.start,
                          working_dir, None, writeable_list, cache_list)
        # Assert
        self.assertTrue(self.rsync_mock.sync.called)
        self.sftp_mock.quit.assert_called_once_with()
        self.state_callback_mock.assert_has_calls(
            [mock.call(self.sut.STATE_PREPARING, 0.25), mock.call(self.sut.STATE_CNAME, 0.50),
             mock.call(self.sut.STATE_SYNCING, 0.75)])

    def test_start_cname_already_in_use(self):
        # Arrange
        working_dir = '/tmp/testcase/working_dir'
        writeable_list = ['media', 'uploads']
        cache_list = ['cache', 'media/cache']

        self.sftp_mock.dir.return_value = []
        self.sftp_mock.dir_attr.return_value = []
        self.sftp_mock.exists.side_effect = [False, True]
        self.sftp_mock.read_link.return_value = 'blabla'
        self.rsync_mock.sync.side_effect = [Exception('TestCase')]
        # Act
        with self.assertRaises(livehosting.LiveHostingCNameAlreadyInUse) as cm:
            self.sut.start(working_dir, None, writeable_list, cache_list)
        # Assert
        self.assertNotIsInstance(cm.exception, RetryException)
        self.assertFalse(self.rsync_mock.sync.called)
        self.sftp_mock.quit.assert_called_once_with()
        self.assertFalse(self.sftp_mock.symlink.called)
        self.state_callback_mock.assert_has_calls(
            [mock.call(self.sut.STATE_PREPARING, 0.25), mock.call(self.sut.STATE_CNAME, 0.50)])
