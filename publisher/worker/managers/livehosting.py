from . import base
from ..exceptions import RetryException, NoRetryException

import os
import subprocess

import logging
logger = logging.getLogger(__name__)


class LiveHostingException(Exception):
    pass


class LiveHostingRetryException(RetryException):
    pass


class LiveHostingCNameAlreadyInUse(NoRetryException):
    pass


class LiveHostingRsyncHelper(object):

    def __init__(self, hostname, username, pkey_file, basedir):
        self.hostname = hostname
        self.username = username
        self.pkey_file = pkey_file
        self.basedir = basedir

    def _prepare_working_dir_for_sync(self, working_dir, writeable_list, cache_list):
        logger.info("preparing working dir %s" % working_dir)
        # TODO use os.chmod()
        self._call_chmod('u+rwX,go+rX,go-w', working_dir, recursive=True)
        for d in writeable_list:
            self._call_chmod('go+w', os.path.join(working_dir, d))
        for d in cache_list:
            self._call_chmod('go+w', os.path.join(working_dir, d))

    def _call_chmod(self, permission, folder, recursive=False):
        chmod_cmd = ["chmod", permission]
        if recursive:
            chmod_cmd.append('-R')
        chmod_cmd.append(folder)
        subprocess.check_call(' '.join(chmod_cmd), shell=True)

    def _call_rsync(self, working_dir, live_domain, writeable_list):
        subprocess.check_call(' '.join(self.get_rsync_cmd(working_dir,
                                                          live_domain,
                                                          writeable_list)), shell=True)

    def get_rsync_cmd(self, source_dir, destination_dir, writeable_list):
        dest = os.path.abspath(os.path.join(self.basedir, destination_dir))
        return [
            "rsync", '-rptogc', "-e 'ssh -i %s'" % self.pkey_file,
            " ".join(['--exclude %s' % f for f in writeable_list]),
            source_dir, "%s@%s:%s" % (self.username, self.hostname, dest)
        ]

    def sync(self, working_dir, live_domain, writeable_list, cache_list):
        self._prepare_working_dir_for_sync(working_dir, writeable_list, cache_list)
        self._call_rsync(working_dir, live_domain, writeable_list)


class NotALink(Exception):
    pass


class LiveHostingManager(base.PublishManager):
    """
    Publish manager for our own live hosting platform
    """

    STATE_PREPARING = "PREPARING"
    STATE_SYNCING = "SYNCING"
    STATE_CNAME = "UPDATING CNAME"

    def __init__(self, live_domain, live_cname, sftp_connection, rsync_helper,
                 state_callback=None):
        if live_cname == '':
            live_cname = None
        self.live_cname = live_cname

        self.live_domain = live_domain

        self._sftp_connection = sftp_connection
        self._rsync_helper = rsync_helper

        self._state_callback = state_callback

    def _get_sftp_connection(self):
        """
        :rtype: publisher.worker.managers.backends.LiveHostingSFTPBackEnd
        """
        return self._sftp_connection

    def _get_rsync_helper(self):
        return self._rsync_helper

    def start(self, working_dir, recovery=None, writeable_list=[], cache_list=[]):
        """
        Starts the synchronization
        """
        try:
            self._prepare_livehosting()
            self._sync(working_dir, writeable_list, cache_list)
        except LiveHostingCNameAlreadyInUse as cname_exp:
            raise cname_exp
        except Exception as exp:
            logger.exception('Unknown exception occurred')
            raise LiveHostingRetryException(str(exp), None)

    def delete_all(self):
        logger.debug('Preparing deletion: %s' % self.live_domain)
        try:
            cname = self.live_cname
            self.live_cname = None

            sftp = self._get_sftp_connection()
            sftp.connect()
            logger.debug("Deleting all related cnames for %s" % self.live_domain)

            self._delete_links(sftp)
            if sftp.exists(self.live_domain):
                logger.info("Deleting live website %s" % self.live_domain)
                sftp.erase_directory(self.live_domain)
                sftp.delete_directory(self.live_domain)
            self.live_cname = cname
        finally:
            try:
                sftp.quit()
            except Exception:
                logger.warning('Could not close SFTP connection')

    def _prepare_livehosting(self):
        self._update_state(self.STATE_PREPARING, 0.25)
        logger.debug('Preparing live hosting sync for: %s', self.live_domain)
        try:
            sftp = self._get_sftp_connection()
            sftp.connect()

            self._create_base_folder(sftp)
            self._update_cname(sftp)
        finally:
            try:
                sftp.quit()
            except Exception:
                logger.warning('Could not close SFTP connection')

    def _create_base_folder(self, sftp):
        live_domain = self.live_domain
        if not sftp.exists(live_domain):
            sftp.mkdir(live_domain)

    def _update_cname(self, sftp):
        self._update_state(self.STATE_CNAME, 0.50)
        self._delete_links(sftp)

        if self.live_cname is None:
            return

        if not sftp.exists(self.live_cname):
            # create symlink
            sftp.symlink(self.live_domain, self.live_cname)
        elif sftp.readlink(self.live_cname) != self.live_domain:
            # cname already in use (by other instance)
            logger.warning('The cname %s is already in use' % self.live_cname)
            raise LiveHostingCNameAlreadyInUse('The cname %s is already in use' % self.live_cname)

    def _delete_links(self, sftp):
        files = sftp.dir('.')
        for f in files:
            try:
                self._delete_link(sftp, f)
            except NotALink:
                pass

    def _delete_link(self, sftp, link):
            link_target = sftp.readlink(link)
            if not link_target:
                raise NotALink("path not a link: %s" % link)

            path_base_name = os.path.basename(os.path.normpath(link))
            try:
                if link_target == self.live_domain and path_base_name != self.live_cname:
                    logger.info('Deleting CNAME symlink: %s' % link)
                    sftp.delete_file(link)
            except Exception:
                logger.exception('error deleting link %s' % link)

    def _sync(self, working_dir, writeable_list=[], cache_list=[]):
        self._update_state(self.STATE_SYNCING, 0.75)
        logger.debug('Starting internal sync for: %s' % self.live_domain)
        rsync_helper = self._get_rsync_helper()
        rsync_helper.sync(working_dir, self.live_domain, writeable_list, cache_list)

    def _update_state(self, state, percent):
        self._state_callback(state, percent)
