import json
import pickle
import time

import hashlib
import os

import string
import random

import abc

from . import base
from ..exceptions import NoRetryException, RetryException

from io import BytesIO

from functools import total_ordering

# Logging support
import logging
logger = logging.getLogger(__name__)


class AlreadyExistsException(NoRetryException):

    def __init__(self, invalid_filepaths):
        msg = "The following files already exists: %s" % invalid_filepaths
        super(AlreadyExistsException, self).__init__(msg)
        self.message = msg
        self.invalid_filepaths = invalid_filepaths


class NonEmptyFoldersException(NoRetryException):
    def __init__(self, non_empty_folders):
        self.message = "The following folders are not empty: %s" % non_empty_folders
        self.non_empty_folders = non_empty_folders


class NonEmptyFolderException(NoRetryException):
    def __init__(self, folder):
        self.message = "The folder %s is not empty" % folder
        self.folder = folder


class DoesNotExistException(NoRetryException):
    def __init__(self, folder):
        self.message = "The folder %s does not exists any more"
        self.folder = folder


class SecurityException(NoRetryException):
    pass


def random_string():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for unused in range(10))


def md5sum(filepointer):
    """
    Calculates the md5 hash for the given file (pointer)
    """
    md5 = hashlib.md5()
    with open(filepointer, 'rb') as f:
        data = f.read(md5.block_size)  # IGNORE:E1101
        while data:
            md5.update(data)  # IGNORE:E1101
            data = f.read(128)
    return md5.hexdigest()


def filter_unfinished_tasks(tasklist):
    return [task for task in tasklist if not task.done]


def filter_finished_tasks(tasklist):
    return [task for task in tasklist if task.done]


def object_handler(Obj):
    if hasattr(Obj, 'tojson'):
        return Obj.tojson()
    else:
        raise TypeError('Object of type %s with value of %s'
                        ' is not JSON serializable' % (type(Obj), repr(Obj)))


@total_ordering
class TaskListEntry(object):

    def __init__(self, task):
        self.task = task
        self.done = False

    def __repr__(self):
        return "%s : %s" % (self.done, self.task)

    def __lt__(self, other):
        return self.task < other.task

    def __eq__(self, other):
        return self.task == other.task

    def __hash__(self):
        return hash(self.path)


class TaskList(object):
    """
    Calculates what steps have to be done to synchronize the two lists
    """

    def __init__(self, local_list, remote_list, changed_callback):
        logger.info("Creating task list")
        changed_files = self._get_changed_files(local_list, remote_list,
                                                changed_callback)
        chmod_files = self._get_chmod_only_files(local_list, remote_list,
                                                 changed_files)
        chmod_folders = self._get_chmod_only_folders(local_list, remote_list)

        self.delete_folders = self._get_delete_folders(local_list, remote_list)
        self.delete_files = self._get_delete_files(local_list, remote_list)
        self.create_folders = self._get_new_folders(local_list, remote_list)
        self.new_files = self._get_new_files(local_list, remote_list)
        self.update_files = changed_files
        self.change_permissions = chmod_folders + chmod_files
        self.erase_folders = self._get_erase_folders(local_list, remote_list)
        logger.debug("Erase folders in tasklist: %s" % self.erase_folders)
        logger.debug("Delete folders in tasklist: %s" % self.delete_folders)
        logger.debug("Delete files in tasklist: %s" % self.delete_files)
        logger.debug("Create folders in tasklist: %s" % self.create_folders)
        logger.debug("Updated files in tasklist: %s" % self.update_files)
        logger.debug("New files in tasklist: %s" % self.new_files)
        logger.debug("Change permissions in tasklist: %s" % self.change_permissions)
        logger.info("Task list created")

    def _get_delete_folders(self, local_list, remote_list):
        local_folders = set(local_list.get_folders())
        remote_folders = set(remote_list.get_folders())
        return list(TaskListEntry(remote_list.get_folder(path))
                    for path in remote_folders - local_folders)

    def _get_new_folders(self, local_list, remote_list):
        local_folders = set(local_list.get_folders())
        remote_folders = set(remote_list.get_folders())
        return list(TaskListEntry(local_list.get_folder(x))
                    for x in local_folders - remote_folders)

    def _get_delete_files(self, local_list, remote_list):
        local_files = set(local_list.get_files())
        remote_files = set(remote_list.get_files())
        return list(TaskListEntry(remote_list.get_file(x))
                    for x in remote_files - local_files)

    def _get_new_files(self, local_list, remote_list):
        local_files = set(local_list.get_files())
        remote_files = set(remote_list.get_files())
        return list(TaskListEntry(local_list.get_file(x))
                    for x in local_files - remote_files)

    def _get_changed_files(self, local_list, remote_list, changed_callback):
        local_files = set(local_list.get_files())
        remote_files = set(remote_list.get_files())

        def test_changed(filepath):
            return changed_callback(local_list.get_file(filepath),
                                    remote_list.get_file(filepath))
        changed_files = set(filepath
                            for filepath in set(local_files & remote_files)
                            if test_changed(filepath))
        return list(TaskListEntry(local_list.get_file(x))
                    for x in changed_files)

    def _get_chmod_only_folders(self, local_list, remote_list):
        local_folders = set(local_list.get_folders())
        remote_folders = set(remote_list.get_folders())
        return list(TaskListEntry(local_list.get_folder(x))
                    for x in local_folders & remote_folders)

    def _get_erase_folders(self, local_list, remote_list):
        chmod_folders = self._get_chmod_only_folders(local_list, remote_list)
        delete_folders = self._get_delete_folders(local_list, remote_list)

        def _get_old_permissions(folder):
            return remote_list.get_folder(folder.task.path).permission
        erase_folders = [folder for folder in chmod_folders
                         if _get_old_permissions(folder) == 'c']
        erase_folders += [folder for folder in delete_folders
                          if folder.task.permission in ('w', 'c')]
        return erase_folders

    def _get_chmod_only_files(self, local_list, remote_list, changed_files):
        local_files = set(local_list.get_files())
        remote_files = set(remote_list.get_files())
        chmod_only_files = local_files & remote_files
        changed = set(filetask.task.path for filetask in changed_files)
        return list(TaskListEntry(local_list.get_file(x))
                    for x in chmod_only_files - changed)


@total_ordering
class FileListEntry(object, metaclass=abc.ABCMeta):
    def __init__(self, path, permission):
        self.path = path
        self.permission = permission
        self.old = False

    def __lt__(self, other):
        return self.path < other.path

    def __eq__(self, other):
        return self.path == other.path

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        return self.path

    @abc.abstractmethod
    def tojson(self):
        return


class FileListFileEntry(FileListEntry):

    def __init__(self, path, permission, size, checksum):
        super(FileListFileEntry, self).__init__(path, permission)
        self.size = size
        self.checksum = checksum

    def tojson(self):
        return ('FILE', self.path, self.permission, self.size, self.checksum,
                self.old)


class FileListFolderEntry(FileListEntry):

    def tojson(self):
        return ('DIR', self.path, self.permission, self.old)


class FileList(object):

    def __init__(self, files=[], folders=[]):
        self._files = dict((f.path, f) for f in files)
        self._folders = dict((f.path, f) for f in folders)

    def scan_local_folder(self, working_dir, type_mapper=None):
        logger.debug("Detecting local files from: %s" % working_dir)

        file_list = []
        folder_list = []
        if not type_mapper:
            type_mapper = lambda _path: 'r'
        for base_dir, _unused_dirs, files in os.walk(working_dir):
            folder = os.path.relpath(base_dir, working_dir)
            if folder != '.':
                permission = type_mapper(folder)
                folder_list.append(FileListFolderEntry(folder, permission))
            for filename in files:
                path = os.path.join(base_dir, filename)
                permission = type_mapper(os.path.join(folder, filename))
                file_list.append(FileListFileEntry(os.path.join(folder,
                                                                filename),
                                                   permission,
                                                   os.path.getsize(path),
                                                   md5sum(path)))
        self._files = dict((f.path, f) for f in file_list)
        self._folders = dict((f.path, f) for f in folder_list)

    def read_json_manifest(self, manifest, recovery_manifest=None):
        list_dict = json.load(manifest)
        if recovery_manifest:
            tmp_manifest = json.load(recovery_manifest)
            self.read_manifest(list_dict, tmp_manifest)
        else:
            self.read_manifest(list_dict)

    def read_manifest(self, manifest, recovery_manifest=None):
        file_list = dict((e[1], FileListFileEntry(e[1], e[2], e[3], e[4]))
                         for e in manifest['files'])
        folder_list = dict((e[1], FileListFolderEntry(e[1], e[2]))
                           for e in manifest['folders'])
        if recovery_manifest:
            tmp_files = dict((e[1], FileListFileEntry(e[1], e[2], e[3], e[4]))
                             for e in recovery_manifest['files'])
            tmp_folders = dict((e[1], FileListFolderEntry(e[1], e[2]))
                               for e in recovery_manifest['folders'])
            file_list = dict(list(tmp_files.items()) + list(file_list.items()))
            folder_list = dict(list(tmp_folders.items()) + list(folder_list.items()))
        self._files = file_list
        self._folders = folder_list

    def generate_manifest(self, old_folders=[], old_files=[]):
        files = list(self._files.values()) + old_files
        folders = list(self._folders.values()) + old_folders
        return json.dumps({'files': files, 'folders': folders}, default=object_handler)

    def get_folders(self):
        return list(self._folders.keys())

    def get_files(self):
        return list(self._files.keys())

    def get_file(self, path):
        return self._files[path]

    def get_folder(self, path):
        return self._folders[path]

    def remove_invalids(self, validation_callback):
        logger.info("Checking remote files")
        self._files = dict((p, f) for p, f in list(self._files.items())
                           if validation_callback(p))
        self._folders = dict((p, f) for p, f in list(self._folders.items())
                             if validation_callback(p))


class ManifestUploadManager(base.PublishManager):

    MANIFEST_FOLDER_PREFIX = ".publisher"

    def __init__(self, back_end, test_url=None, state_callback=None):
        # TODO: implement test url
        self._test_url = test_url
        self._back_end = back_end
        self._state_callback = state_callback

        # Lazy attributes
        self._manifest_folder = None
        self._manifest = None
        self._manifest_tmp = None

        self._start_time = None

        logger.debug("Initialized ManifestUploadManager")

    @property
    def manifest(self):
        if not self._manifest:
            self._manifest = self.get_manifest_folder() + "/.manifest"
        return self._manifest

    @property
    def manifest_tmp(self):
        if not self._manifest_tmp:
            self._manifest_tmp = self.get_manifest_folder() + "/.manifest.new"
        return self._manifest_tmp

    def get_manifest_folder(self):
        if not self._manifest_folder:
            folders = [x for x in map(os.path.basename, self._back_end.dir('.')) if x.startswith(self.MANIFEST_FOLDER_PREFIX)]
            if folders:
                self._manifest_folder = folders[0]
            else:
                self._manifest_folder = "%s.%s" % (self.MANIFEST_FOLDER_PREFIX, random_string())
        return self._manifest_folder

    def _update_state(self, state, tasklist=None, msg=None):
        if self._state_callback is None:
            return

        if not tasklist:
            self._state_callback(state, None, msg)
            return

        if not self._start_time:
            self._start_time = time.time()

        delete_files = tasklist.delete_files
        delete_folders = tasklist.delete_folders
        create_folders = tasklist.create_folders
        change_permissions = tasklist.change_permissions
        upload_files = tasklist.new_files + tasklist.update_files

        dividend = len(filter_finished_tasks(delete_files))
        dividend += len(filter_finished_tasks(delete_folders))
        dividend += len(filter_finished_tasks(create_folders))
        dividend += len(filter_finished_tasks(change_permissions))

        divisor = len(delete_files)
        divisor += len(delete_folders)
        divisor += len(create_folders)
        divisor += len(change_permissions)

        weight = 4096
        dividend *= weight
        divisor *= weight

        mb_done = sum(upfile.task.size for upfile in
                      filter_finished_tasks(upload_files))
        mb_overall = sum(upfile.task.size for upfile in upload_files)

        dividend += mb_done
        divisor += mb_overall

        percent = float(dividend) / float(divisor) if divisor else 0.0
        speed = percent / (time.time() - self._start_time)
        remaining = (1.0 - percent)
        if speed and percent > 0.05:
            self._state_callback(state, percent, msg, remaining / speed)
        else:
            self._state_callback(state, percent, msg, None)

    def _create_manifest_folder(self):
        folder = self.get_manifest_folder()
        if not self._back_end.exists(folder):
            self._back_end.mkdir(folder)

    def test_connection(self):
        # TODO: Check and unify exceptions here
        self._back_end.connect()
        # TODO: Upload test file
        self._back_end.quit()

    def start(self, working_dir, recovery=None, writeable_list=[], cache_list=[]):
        """
        Starts the synchronization
        """
        def type_mapper(path):
            if path in cache_list:
                logger.debug("%s is cache" % path)
                return 'c'
            elif path in writeable_list:
                logger.debug("%s is writeable" % path)
                return 'w'
            else:
                return 'r'
        self._update_state("PREPARING TASKLIST")
        local_list = self._get_local_list(working_dir, type_mapper)

        # Connect to server and create task list
        tasklist = None
        self._back_end.connect()
        try:
            if recovery:
                tasklist = pickle.loads(recovery)
                # TODO: Compare local_list with manifest
            if not tasklist:
                tasklist = self._create_new_task_list(local_list)
            self._validate_task_list(tasklist)
            # Starting the real synchronization
            logger.info("Starting synchronization")
            self._create_manifest_folder()
            self._upload_temp_manifest(local_list.generate_manifest())

            not_cleaned_folders = self._erase_folders(tasklist)
            if not_cleaned_folders:
                self._validate_task_list(tasklist, not_cleaned_folders)

            old_files = self._delete_files(tasklist)
            old_folders = self._delete_folders(tasklist)
            self._create_folders(tasklist)
            self._upload_files(tasklist, working_dir)
            self._chmod_only(tasklist)

            new_manifest = local_list.generate_manifest(old_folders, old_files)
            self._upload_new_manifest(new_manifest)
            logger.info("Server synchronized")
        except NoRetryException:
            # NoRetryExceptions are thrown as is
            raise
        except Exception as e:
            # All other Exception are wrapped as a RetryException.
            # This way the job will later restarted.
            logger.exception("An Exception occurred")
            raise RetryException(str(e), pickle.dumps(tasklist))
        finally:
            try:
                self._back_end.quit()
            except:
                # Ignore that problem here
                pass

    def delete_all(self):
        """ Removes all files from the given back end/server """
        self._back_end.connect()
        tasklist = self._create_new_task_list(FileList())
        self._validate_task_list(tasklist)
        logger.info("Removing files from %s" % self._back_end)
        self._delete_files(tasklist)
        logger.info("Removing folders from %s" % self._back_end)
        self._delete_folders(tasklist)

    def _create_new_task_list(self, local_list):
        # Collecting meta informations
        remote_list = self._get_remote_list()
        logger.debug(remote_list.generate_manifest())
        remote_list.remove_invalids(self._back_end.exists)
        logger.debug(remote_list.generate_manifest())
        tasklist = TaskList(local_list, remote_list, self._changed)
        return tasklist

    def _validate_task_list(self, tasklist, not_erased_folders=[]):
        """
        Verifying that there are no file conflicts
        """
        logger.debug("Checking for any file conflicts")
        new_files = set(task.task.path for task in tasklist.new_files)
        delete_files = set(task.task.path for task in tasklist.delete_files)
        new_folders = set(task.task.path for task in tasklist.create_folders)
        delete_folders = set(task.task.path for task in tasklist.delete_folders)
        erase_folders = set(task.task.path for task in tasklist.erase_folders)
        erase_folders -= set(not_erased_folders)
        logger.debug("Full erase folders are: %s" % erase_folders)
        invalid_new_folders = self._validate_new(new_folders - delete_files,
                                                 erase_folders)

        logger.debug("Checking that the folder for deletion can be deleted")
        #
        # Warning!!! The following method manipulates the delete_folders list!
        #
        invalid_delete_folders = self._validate_delete_folders(delete_folders,
                                                               delete_files,
                                                               erase_folders)
        if invalid_delete_folders:
            logger.warn("Some folders are not empty: %s"
                        % invalid_delete_folders)
        invalid_new_files = self._validate_new(new_files - delete_folders,
                                               erase_folders)
        invalid_files = invalid_new_files + invalid_new_folders
        if invalid_files:
            logger.warn("Some file conflicts detected: %s" % invalid_files)
            raise AlreadyExistsException(invalid_files)
        return invalid_delete_folders

    def _upload_temp_manifest(self, manifest):
        logger.debug("Uploading recovery manifest file")
        new_manifest = BytesIO()
        new_manifest.write(manifest.encode("utf-8"))
        new_manifest.seek(0)
        self._back_end.upload(self.manifest_tmp, new_manifest)

    def _upload_new_manifest(self, manifest):
        """
        Uploads the given file list as the new manifest file.
        It also removes the temporary manifest file.
        """
        logger.debug("Uploading new manifest file")
        new_manifest = BytesIO()
        new_manifest.write(manifest.encode("utf-8"))
        new_manifest.seek(0)
        self._back_end.upload(self.manifest, new_manifest)
        logger.debug("Deleting recovery manifest file")
        self._back_end.delete_file(self.manifest_tmp)

    def _upload_files(self, tasklist, working_dir):
        self._update_state("UPLOAD_FILES", tasklist)
        files = filter_unfinished_tasks(tasklist.new_files +
                                        tasklist.update_files)
        logger.info("Uploading %d files" % len(files))
        for task in files:
            upload_file, permission = task.task.path, task.task.permission
            local_path = os.path.abspath(os.path.join(working_dir,
                                                      upload_file))
            local_path = os.path.realpath(local_path)
            # TODO (sw): figure out how this should work?!
            #if os.path.relpath(local_path, working_dir).startswith('..'):
            #    msg = "File (%s) is not in the current working directory" % local_path
            #    logger.warning(msg)
            #    raise SecurityException(msg)
            logger.debug("Uploading file: %s" % local_path)
            with open(local_path, 'rb') as fp:
                self._back_end.upload(upload_file, fp)
                self._back_end.chmod(upload_file, permission)

            task.done = True
            self._update_state("UPLOAD_FILES", tasklist)

    def _chmod_only(self, tasklist):
        self._update_state("CHANGE_PERMISSIONS", tasklist)
        chmod_only = filter_unfinished_tasks(tasklist.change_permissions)
        logger.info("Updating permissions of %d existing folders" % len(chmod_only))
        for task in chmod_only:
            path, permission = task.task.path, task.task.permission
            logger.debug("Updating permissions of %s" % path)
            if not self._back_end.exists(path):
                # This only happens when someone deletes stuff in our rukzuk
                # folder after we finished our preparing
                raise DoesNotExistException(path)
            self._back_end.chmod(path, permission)

            task.done = True
            self._update_state("CHANGE_PERMISSIONS", tasklist)

    def _create_folders(self, tasklist):
        self._update_state("CREATE_FOLDERS", tasklist)
        new_folders = filter_unfinished_tasks(tasklist.create_folders)
        logger.info("Creating %d new folders" % len(new_folders))
        for task in sorted(new_folders, key=lambda x: x.task):
            folder = task.task
            logger.debug("Creating folder %s/" % folder)
            if self._back_end.exists(folder.path):
                # This only happens when someone uploads stuff into the rukzuk
                # folder after we started our upload and finished
                # our preparing.
                raise AlreadyExistsException([folder])
            self._back_end.mkdir(folder.path)
            self._back_end.chmod(folder.path, folder.permission)

            task.done = True
            self._update_state("CREATE_FOLDERS", tasklist)

    def _erase_folders(self, tasklist):
        self._update_state("ERASE_FOLDERS", tasklist)
        erase_folders = filter_unfinished_tasks(tasklist.erase_folders)
        logger.info("Erasing folder content of %d folders"
                    % len(erase_folders))
        not_clean_folders = []
        for task in sorted(erase_folders, reverse=True):
            folder = task.task
            if not self._back_end.erase_directory(folder.path):
                logger.warn("Couldn't clean up %s" % folder.path)
                not_clean_folders.append(folder.path)
            task.done = True
            self._update_state("ERASE_FOLDERS", tasklist)
        return set(not_clean_folders)

    def _delete_folders(self, tasklist):
        """
        Tries to start the unfinished folder deletion tasks and returns all
        not deleted folders.
        """
        self._update_state("DELETE_FOLDERS", tasklist)
        delete_folders = filter_unfinished_tasks(tasklist.delete_folders)
        logger.info("Deleting %d old folder" % len(delete_folders))
        logger.debug("Folders for deletion are: %s" % delete_folders)
        # Bring the list into the right order for deletion
        # (Child folder before parent folder)
        for task in sorted(delete_folders, reverse=True):
            folder = task.task
            logger.debug("Deleting %s" % folder)
            # Check that the folder is empty
            if self._back_end.dir(folder.path):
                # This only happens when someone uploads stuff into the rukzuk
                # folder after we started our upload and finished
                # our preparing or the erasing failed.
                folder.old = True
            # Delete the folder
            if not self._back_end.delete_directory(folder.path):
                folder.old = True
            # Mark task as done
            task.done = True
            self._update_state("DELETE_FOLDERS", tasklist)
        return [task.task for task in tasklist.delete_folders if task.task.old]

    def _delete_files(self, tasklist):
        self._update_state("DELETE_FILES", tasklist)
        delete_files = filter_unfinished_tasks(tasklist.delete_files)
        logger.info("Deleting %d old files" % len(delete_files))
        for task in delete_files:
            old_file = task.task
            logger.debug("Deleting %s" % old_file)
            if not self._back_end.delete_file(old_file.path):
                old_file.old = True

            task.done = True
            self._update_state("DELETE_FILES", tasklist)
        return [task.task for task in tasklist.delete_files if task.task.old]

    def _validate_delete_folders(self, delete_folders, delete_files,
                                 erase_folders):
        non_empty_folders = []
        sorted_delete_folders = sorted(delete_folders, reverse=True)
        for delete_folder in sorted_delete_folders:
            if delete_folder not in erase_folders:
                folder_content = self._back_end.dir(delete_folder)
                # Add the folder to the non_empty_folders list,
                # when its content will not removed in this transaction.
                folder_content = set(folder_content) - delete_files - delete_folders
                if folder_content:
                    logger.warning("Folder %s is not empty: %s"
                                   % (delete_folder, folder_content))
                    non_empty_folders.append(delete_folder)
                    delete_folders.remove(delete_folder)
        return non_empty_folders

    def _validate_new(self, new_filepaths, erase_folders):
        result = []
        for filepath in new_filepaths:
            logger.debug("Checking new file: %s" % filepath)
            addit = True
            for folder in erase_folders:
                if filepath.startswith(folder):
                    addit = False
            if addit and self._back_end.exists(filepath):
                logger.debug("Found new file on the server : %s" % filepath)
                result.append(filepath)
        return result

    def _changed(self, local_file, remote_file):
        """
        Checks if the checksum has changed or the server file size is wrong.
        """
        if local_file.checksum != remote_file.checksum:
            return True

        if local_file.size != remote_file.size:
            return True
        else:
            size = self._back_end.size(remote_file.path)
            if size != remote_file.size:
                return True

        return False

    def _get_local_list(self, working_dir, type_mapper=None):
        local_list = FileList()
        local_list.scan_local_folder(working_dir, type_mapper)
        return local_list

    def _get_remote_list(self):
        if self._back_end.exists(self.manifest):
            return self._get_remote_list_from_manifest()
        else:
            logger.warn("No manifest file found on server")
            if self._old_publish():
                return self._get_remote_list_from_folder_structure()
            else:
                return FileList()

    def _old_publish(self):
        return self._back_end.exists('server/version.json') and \
            self._back_end.exists('mdb/mdb.php')

    def _get_remote_list_from_folder_structure(self):
        logger.info("Removing old published data")
        files = []
        folders = []
        content = self._back_end.dir('')
        logger.debug("Content of base dir is: %s" % content)
        for entry in content:
            # Don't remove hidden stuff on first level
            if not entry.startswith('.'):
                if self._back_end.type(entry) == 'd':
                    # Mark this folder as writeable for complete erasing
                    folders.append(FileListFolderEntry(entry, 'c'))
                else:
                    files.append(FileListFileEntry('./' + entry, 'r', 0, ''))
        filelist = FileList(files, folders)
        logger.debug(filelist.generate_manifest())
        return filelist

    def _get_remote_list_from_manifest(self):
        logger.debug("Downloading Manifest")
        manifest_file = self._back_end.download(self.manifest)
        remote_list = FileList()
        if self._back_end.exists(self.manifest_tmp):
            # Ups there is a hopefully broken old session
            # We will calculate a new manifest file out of both files
            # and upload it to clean up the publisher state
            # TODO: Check for parallel execution
            logger.warning("Temporary manifest file found. Trying to recover.")
            recovery_manifest_file = self._back_end.download(self.manifest_tmp)
            remote_list.read_json_manifest(manifest_file,
                                           recovery_manifest_file)
            logger.debug("New manifest file calculated")
            logger.debug("Uploading new manifest file")
            # That function also removes the temporary manifest file
            self._upload_new_manifest(remote_list.generate_manifest())
        else:
            logger.debug("Reading remote manifest file")
            remote_list.read_json_manifest(manifest_file)
        return remote_list
