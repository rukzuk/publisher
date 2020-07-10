import unittest
import mock

from publisher.worker.managers import manifestbased


class FileListTest(unittest.TestCase):

    def test_remove_invalids(self):
        fl = manifestbased.FileList()
        files = [('FILE', 'subfolder1/test.txt', oct(777), 512, 1234567890),
                 ('FILE', 'test2.txt', oct(555), 1024, 963852741),
                 ('FILE', 'test3.txt', oct(555), 1024, 963852741),
                 ('FILE', 'test5.txt', oct(555), 1, 963852741)]
        folders = [('DIR', 'subfolder1', oct(777)),
                   ('DIR', 'subfolder2', oct(777))]
        manifest = {'files': files, 'folders': folders}
        fl.read_manifest(manifest)
        fl.remove_invalids(lambda x: (x.find('2') > -1))
        # TODO: Check arrays


class ManagerTest(unittest.TestCase):

    def test_create_tasklist(self):
        backend = mock.Mock()
        backend.size = mock.Mock(return_value=1024)

        local_list = manifestbased.FileList()
        files = [('FILE', 'subfolder1/test.txt', oct(777), 512, 1234567890),
                 ('FILE', 'test2.txt', oct(555), 1024, 963852741),
                 ('FILE', 'test3.txt', oct(555), 1024, 963852741),
                 ('FILE', 'test5.txt', oct(555), 1, 963852741)]
        folders = [('DIR', 'subfolder1', oct(777)),
                   ('DIR', 'subfolder2', oct(777))]
        manifest = {'files': files, 'folders': folders}
        local_list.read_manifest(manifest)

        remote_list = manifestbased.FileList()
        files = [('FILE', 'subfolder3/test4.txt', oct(777), 512, 1234567890),
                 ('FILE', 'test2.txt', oct(555), 1024, 963852741),
                 ('FILE', 'test3.txt', oct(555), 1024, 963852111),
                 ('FILE', 'test5.txt', oct(555), 2, 963852741)]
        folders = [('DIR', 'subfolder3', oct(777)),
                   ('DIR', 'subfolder2', oct(777))]
        manifest = {'files': files, 'folders': folders}
        remote_list.read_manifest(manifest)
        manager = manifestbased.ManifestUploadManager(backend, "http://test/test.zip")
        manager._get_remote_list = mock.Mock(return_value=remote_list)
        tasklist = manager._create_new_task_list(local_list)
        self.assertIn('subfolder3', [task.task.path for task in
                                     tasklist.delete_folders])
        self.assertIn('subfolder3/test4.txt', [task.task.path for task in
                                               tasklist.delete_files])
        self.assertIn('subfolder1', [task.task.path for task in
                                     tasklist.create_folders])
        self.assertIn('subfolder1/test.txt', [task.task.path for task in
                                              tasklist.new_files])
        self.assertIn('test3.txt', [task.task.path for task in
                                    tasklist.update_files])
        self.assertIn('test5.txt', [task.task.path for task in
                                    tasklist.update_files])
        # This file hasn't changed but we are forcing a chmod update
        self.assertIn('test2.txt', [task.task.path for task in
                                    tasklist.change_permissions])

    def test_new_file_exists_tasklist_validation(self):
        backend = mock.Mock()
        backend.exists = mock.Mock(return_value=True)
        manager = manifestbased.ManifestUploadManager(backend,
                                                      "http://test/test.zip")
        local_list = manifestbased.FileList()
        files = [('FILE', 'test2.txt', oct(555), 1024, 963852741)]
        folders = []
        manifest = {'files': files, 'folders': folders}
        local_list.read_manifest(manifest)

        remote_list = manifestbased.FileList()
        manager._get_remote_list = mock.Mock(return_value=remote_list)
        tasklist = manager._create_new_task_list(local_list)
        self.assertRaises(manifestbased.AlreadyExistsException,
                          manager._validate_task_list, tasklist)

    def test_not_empty_folder_tasklist_validation(self):
        backend = mock.Mock()
        backend.dir = mock.MagicMock(return_value=('notempty.txt',))

        local_list = manifestbased.FileList()
        remote_list = manifestbased.FileList()
        files = []
        folders = [('DIR', 'subfolder', oct(555))]
        manifest = {'files': files, 'folders': folders}
        remote_list.read_manifest(manifest)
        manager = manifestbased.ManifestUploadManager(backend,
                                                      "http://test/test.zip")
        manager._get_remote_list = mock.Mock(return_value=remote_list)
        tasklist = manager._create_new_task_list(local_list)
        self.assertGreater(len(manager._validate_task_list(tasklist)), 0)

    def test_lazy_connect(self):
        backend = mock.Mock()
        backend.connect = mock.MagicMock()

        manifestbased.ManifestUploadManager(backend, "http://test/test.zip")
        self.assertFalse(backend.connect.called, "Backend connection while init")

    def test_delete_all(self):
        backend = mock.Mock()
        backend.dir = mock.MagicMock(return_value=[])
        backend.exists = mock.Mock(return_value=True)
        backend.delete_file = mock.Mock()
        backend.delete_directory = mock.Mock()
        manager = manifestbased.ManifestUploadManager(backend,
                                                      "http://test/test.zip")

        remote_list = manifestbased.FileList()
        files = [('FILES', 'file.txt', oct(777), 512, 1234567890)]
        folders = [('DIR', 'subfolder', oct(555))]
        manifest = {'files': files, 'folders': folders}
        remote_list.read_manifest(manifest)

        manager._get_remote_list = mock.Mock(return_value=remote_list)
        manager.delete_all()

        manager._get_remote_list.assert_called_once_with()
        backend.delete_file.assert_called_with('file.txt')
        backend.delete_directory.assert_called_with('subfolder')

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
