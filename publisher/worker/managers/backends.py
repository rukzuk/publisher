'''
Created on 14.02.2013

@author: mtrunner
'''
from functools import wraps
import abc

import re
import ftplib
import os.path
from io import BytesIO

import paramiko
import stat
import contextlib

import logging
logger = logging.getLogger(__name__)


class ConnectionBackEnd(object, metaclass=abc.ABCMeta):
    @staticmethod
    def on_exception_reconnect_and_retry(func):
        """
        Decorator that starts a new back end connection and retries the
        decorated function when an exception occurs.
        """
        @wraps(func)
        def _wrapper(self, *args, **kwrds):
            try:
                return func(self, *args, **kwrds)
            except Exception as exp:
                logger.warning("An exception (%s) occurred while executing %s,"
                               " reconnecting and retrying the command"
                               % (exp, func))
                try:
                    self.quit()
                except Exception:
                    pass
                self.connect()
                return func(self, *args, **kwrds)
        return _wrapper

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def quit(self):
        pass


class FTPLineParser(object):
    """ Helper to parses the human readable out put of the FTP DIR command """

    # FTP is quite a rudimentary protocol and there's no built-in protocol
    # query allowing you to get the type (file, dir) of each node.
    # Furthermore the output of the LIST command is only specified
    # as "human readable", but most servers return a list that has the
    # same format as "ls -l" on most unix systems.
    # The following flag is True when the server returns a format that
    # we can parse and use.
    _list_regex_unix = re.compile(r"^(?P<type>[A-Za-z-])"
                                  r"([r-][w-][xXsStT-]){3}\s+"
                                  r"\d+\s+"
                                  r"\S+\s+\S+\s+"
                                  r"\d+\s+"
                                  r"\S+\s+\S+\s+"
                                  r"(\d{2}:\d{2}|\d{4})\s"
                                  r"(?P<name>.+)$")
    _list_regex_msdos = re.compile(r"^\S+\s+\S+\s+"
                                   r"(?P<type>\S+)\s+(?P<name>.+)$")

    class LineFormatError(Exception):
        pass

    def parse(self, line):
        """
        Helper function thats parses the human readable out put of
        the unix 'ls -l' command and the msdos 'dir' command.

        It returns the file or directory name and its type.

        Hint: The MS-DOS <DIR> will be mapped to the unix 'd' type.
        """
        unix_result = self._list_regex_unix.match(line)
        if unix_result:
            return (unix_result.group('name'),
                    unix_result.group('type'))
        msdos_result = self._list_regex_msdos.match(line)
        if msdos_result:
            if msdos_result.group('type') == '<DIR>':
                return (msdos_result.group('name'), 'd')
            else:
                return (msdos_result.group('name'), '-')
        msg = "Unknown FTP DIR line format detected: '%s'" % line
        logger.error(msg)
        raise self.LineFormatError(msg)


class FTPUploadBackEnd(ConnectionBackEnd):
    """
    FTP Upload Back end for the rukzuk publisher.
    """

    def __init__(self,
                 host, username, password, basedir, port=21,
                 permission_map={}):
        self.host = host
        self.username = username
        self.password = password
        self.basedir = basedir
        self.port = port if port else 21
        self.permission_map = permission_map
        # TODO: make FTP / FTPS switchable?
        #self._ftp = ftplib.FTP()
        self._ftp = ftplib.FTP_TLS()
        self._ftp_folder = basedir
        self._type_i = True

    def connect(self):
        logger.info("Connecting %s:%s" % (self.host, self.port))
        self._ftp.connect(self.host, self.port, 15)
        self._ftp.login(self.username, self.password)
        self._ftp.prot_p()
        logger.debug("FTP-Server welcome message was: %s" % self._ftp.getwelcome())
        pwd = self._ftp.pwd()
        logger.debug("PWD of server '%s' is: %s" % (self.host, pwd))
        self._ftp_folder = os.path.join(pwd, self.basedir)
        logger.debug("Switching to binary mode")
        self._set_binary_mode()
        self._cwd(self._ftp_folder)

    def exists(self, filepath):
        """
        Checks that a file or directory exist on the server
        """
        return self.type(filepath) is not None

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def dir(self, folder):
        """
        Returns all elements in the directory
        """
        dir_list = [os.path.basename(entry[0]) for entry in self._list(folder)]
        return [os.path.join(folder, f)
                for f in dir_list
                if f not in ('.', '..')]

    def _list(self, folder):
        dir_list = []
        try:
            self._cwd("%s/%s" % (self._ftp_folder, folder))
        except ftplib.Error:
            # Assuming that a ftp error means folder does not exist.
            return []
        self._ftp.dir("-a", dir_list.append)
        return list(map(self._parse_list_line, dir_list))

    def erase_directory(self, folder):
        """
        Erases the hole content of an directory.
        Returns True when the directory is now empty else False.
        """
        logger.debug("Erasing %s" % folder)
        result = True
        for entry in self.dir(folder):
            if self.type(entry) == 'd':
                result = result and self.erase_directory(entry)
                try:
                    self._delete_directory(entry)
                except:
                    result = False
            else:
                try:
                    self._delete_file(entry)
                except:
                    result = False
        return result

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def type(self, path):
        """
        Returns the unix inode type of the given path. If path doesn't exists
        it returns 'None'.

        Warning: This function only works on unix and msdos ftp servers.
        """
        try:
            folder, name = os.path.split(path)
            for entryname, entrytype in self._list(folder):
                if entryname == name:
                    return entrytype
            return None
        except ftplib.Error:
            return None

    def _parse_list_line(self, line):
        parser = FTPLineParser()
        return parser.parse(line)

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def size(self, filepath):
        """
        Returns the size of the given file
        """
        dirpath, filename = os.path.split(filepath)
        self._cwd(dirpath)
        self._set_binary_mode()
        return self._ftp.size(filename)

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def download(self, filepath):
        """
        Downloads a file to ftp server
        """
        dirpath, filename = os.path.split(filepath)
        self._cwd(dirpath)
        buf = BytesIO()
        logger.debug("Downloading %s" % filename)
        self._ftp.retrbinary("RETR %s" % filename, buf.write)
        buf.seek(0)
        logger.debug("Downloaded %s" % filename)
        return buf

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def upload(self, filepath, fp):
        """
        Uploads a file to the ftp server
        """
        dirpath, filename = os.path.split(filepath)
        self._cwd(dirpath)
        self._ftp.storbinary("STOR %s" % filename, fp)

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def mkdir(self, newdir):
        """
        Creates a new directory on the ftp server
        """
        dirpath, dirname = os.path.split(newdir)
        self._cwd(dirpath)
        logger.debug("Creating folder: %s" % dirname)
        self._ftp.mkd(dirname)

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def delete_file(self, filepath):
        """
        Function to delete a file.
        """
        try:
            self._delete_file(filepath)
            return True
        except ftplib.Error:
            return False

    def _delete_file(self, filepath):
        """
        Internal function to delete a file.
        """
        dirpath, filename = os.path.split(filepath)
        self._cwd(dirpath)
        self._ftp.delete(filename)

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def delete_directory(self, directorypath):
        """
        Function to delete a directory
        """
        try:
            self._delete_directory(directorypath)
            return True
        except ftplib.Error:
            return False

    def _delete_directory(self, directorypath):
        """
        Internal function to delete a directory
        """
        dirpath, dirname = os.path.split(directorypath)
        self._cwd(dirpath)
        self._ftp.rmd(dirname)

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def chmod(self, filepath, permission):
        """
        Function to change the chmod of a given file or directory.
        Returns False when an exception occurs while executing the
        SITE CHMOD command.

        Warning: Not all servers support the chmod cmd
        """
        dirpath, filename = os.path.split(filepath)
        self._cwd(dirpath)
        chmod = self.permission_map.get(permission, None)
        if chmod:
            try:
                self._ftp.voidcmd("SITE CHMOD %s %s" % (chmod, filename))
            except IOError:
                raise
            except:
                return False
        return True

    def quit(self):
        """
        Exits the FTP session
        """
        self._ftp.quit()

    def _cwd(self, directory):
        if directory:
            logger.debug("Switching into ftp directory %s"
                         % os.path.join(self._ftp_folder, directory))
            self._ftp.cwd(os.path.join(self._ftp_folder, directory))
        else:
            logger.debug("Switching into ftp directory %s"
                         % (self._ftp_folder))
            self._ftp.cwd("%s" % self._ftp_folder)

    def _set_binary_mode(self):
        if self._type_i:
            try:
                self._ftp.sendcmd("TYPE I")
            except ftplib.Error:
                self._type_i = False


class CachedFTPUploadBackEnd(FTPUploadBackEnd):
    """
    FTP back end that caches the FTP list call result for a faster task list
    creation on an initial publishing FTP job.
    """

    def __init__(self, host, username, password, basedir, port=21, permission_map={}):
        logger.debug("Init FTP back end with directory list cache")
        self._list_cache = {}
        FTPUploadBackEnd.__init__(self, host, username, password, basedir,
                                  port=port, permission_map=permission_map)

    def connect(self):
        self._invalidate_cache()
        FTPUploadBackEnd.connect(self)

    def _list(self, folder):
        if folder not in self._list_cache:
            logger.debug("No ftp directory cache entry found for %s" % folder)
            self._list_cache[folder] = FTPUploadBackEnd._list(self, folder)
        else:
            logger.debug("Ftp directory cache entry found for %s" % folder)
        return self._list_cache[folder]

    def _invalidate_cache(self):
        """ Invalidates the internal FTP directory list cache """
        self._list_cache.clear()

    def delete_directory(self, directorypath):
        self._invalidate_cache()
        return FTPUploadBackEnd.delete_directory(self, directorypath)

    def delete_file(self, filepath):
        self._invalidate_cache()
        return FTPUploadBackEnd.delete_file(self, filepath)

    def upload(self, filepath, fp):
        self._invalidate_cache()
        FTPUploadBackEnd.upload(self, filepath, fp)

    def mkdir(self, newdir):
        self._invalidate_cache()
        FTPUploadBackEnd.mkdir(self, newdir)

    def erase_directory(self, folder):
        self._invalidate_cache()
        return FTPUploadBackEnd.erase_directory(self, folder)


class BoostedFTPUploadBackEnd(CachedFTPUploadBackEnd):
    """
    FTP back end that lists parent folders first to quickly fill the cache.
    This way it the FTP list command is less called for non
    existing sub folders. (Which is time expensive on some FTP servers.)
    """

    def _list(self, folder):
        current_folder = ''
        folder_entries = []
        # This iteration fills the quickly the cache
        # and also increases the hit rate for missing/empty folders
        # for a normal publishing task.
        for f in str(folder).split('/'):
            # Append the sub folder
            current_folder = "/".join([current_folder, f])
            # Check folder entries
            folder_entries = CachedFTPUploadBackEnd._list(self, current_folder)
            # No parent folder means no sub folder. So we can stop here.
            if not folder_entries:
                return []
        return folder_entries


class SFTPUploadBackEnd(ConnectionBackEnd):

    def __init__(self, host, username, password, basedir, port=22,
                 permission_map={}):
        self.host = host
        self.username = username
        self.password = password
        self.basedir = basedir
        self.port = port if port else 22
        self.permission_map = permission_map
        self._sftp_folder = basedir
        self._sftp = None
        self._transport = None

    def connect(self):
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username, password=self.password)
        self._sftp = paramiko.SFTPClient.from_transport(transport)
        self._transport = transport

    def quit(self):
        self._sftp.close()
        self._transport.close()

    def _path(self, path):
        if path.startswith(self._sftp_folder):
            return path
        return os.path.join(self._sftp_folder, path)

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def exists(self, filepath):
        try:
            self._sftp.stat(self._path(filepath))
            return True
        except IOError:
            return False

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def dir(self, folder):
        return [os.path.join(folder, entry)
                for entry in self._sftp.listdir(self._path(folder))]

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def type(self, path):
        path = self._path(path)
        return 'd' if stat.S_ISDIR(self._sftp.stat(path).st_mode) else '-'

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def size(self, filepath):
        return self._sftp.stat(self._path(filepath)).st_size

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def download(self, filepath):
        buf = BytesIO()
        with contextlib.closing(self._sftp.open(self._path(filepath), 'rb')) as remote_file:
            buf.write(remote_file.read())
        buf.seek(0)
        return buf

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def upload(self, filepath, fp):
        path = self._path(filepath)
        logger.debug("Uploading %s" % path)
        with contextlib.closing(self._sftp.open(path, 'wb')) as remote_file:
            remote_file.write(fp.read())

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def mkdir(self, newdir):
        self._sftp.mkdir(self._path(newdir))

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def delete_file(self, filepath):
        self._sftp.remove(self._path(filepath))

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def delete_directory(self, directorypath):
        self._sftp.rmdir(self._path(directorypath))

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def chmod(self, filepath, permission):
        chmod = self.permission_map.get(permission, None)
        if chmod:
            self._sftp.chmod(self._path(filepath), int(chmod, 8))

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def erase_directory(self, folder):
        """
        Erases the hole content of a directory.
        Returns True when the directory is now empty else False.
        """
        logger.debug("Erasing %s" % folder)
        result = True
        for entry_path in self.dir(folder):
            if self.type(entry_path) == 'd':
                result = result and self.erase_directory(entry_path)
                try:
                    self.delete_directory(entry_path)
                except:
                    result = False
            else:
                try:
                    self.delete_file(entry_path)
                except:
                    result = False
        return result


class PKeySFTPUploadBackEnd(SFTPUploadBackEnd):
    """
    SFTP back end with private key auth support
    """

    def __init__(self, host, username, pkey_file, basedir, port=22, permission_map={}):
        self.host = host
        self.username = username
        self.pkey = paramiko.RSAKey.from_private_key_file(pkey_file)
        self.basedir = basedir
        self.port = port if port else 22
        self.permission_map = permission_map
        self._sftp_folder = basedir
        self._sftp = None
        self._transport = None

    def connect(self):
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username, pkey=self.pkey)
        self._sftp = paramiko.SFTPClient.from_transport(transport)
        self._transport = transport


class LiveHostingSFTPBackEnd(PKeySFTPUploadBackEnd):
    """
    Special back end with SFTP symlink support, for our mod_vhost hack/configuration
    """

    def symlink(self, source, dest):
        """
        Create a symbolic link (shortcut) of the source path at destination.

        :param source:
        :type source: str
        :param dest:
        :type dest: str
        """
        server_source = os.path.abspath(self._path(source))
        server_dest = os.path.abspath(self._path(dest))
        self._sftp.symlink(server_source, server_dest)

    def readlink(self, path):
        """
        Returns the symlink destination

        :param path: relative Path to the symlink
        :type path: str

        :return: The destination of the symlink
        :rtype: str
        """
        try:
            server_path = self._sftp.readlink(self._path(path))
            return os.path.basename(os.path.normpath(
                os.path.relpath(server_path, self._sftp_folder)))
        except:
            return None

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def lstat(self, path):
        return self._sftp.lstat(self._path(path))

    @ConnectionBackEnd.on_exception_reconnect_and_retry
    def dir_attr(self, folder):
        return self._sftp.listdir_attr(self._path(folder))
