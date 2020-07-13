from . import backends
from . import manifestbased
from . import livehosting
from django.conf import settings

import logging
logger = logging.getLogger(__name__)


def init_manager(test_url, back_end_type, back_end_params, state=None):
    if back_end_type == "internal":
        logger.info("Initalising internal back end")
        logger.debug("Back end parameters are: %s" % back_end_params)
        live_cname = back_end_params['cname']
        live_domain = back_end_params['domain']
        sftp_connection = backends.LiveHostingSFTPBackEnd(
            settings.LIVE_SERVER, settings.LIVE_SERVER_USER, settings.LIVE_SERVER_KEYFILE,
            settings.LIVE_SERVER_BASEDIR)
        rsync_helper = livehosting.LiveHostingRsyncHelper(
            settings.LIVE_SERVER, settings.LIVE_SERVER_USER, settings.LIVE_SERVER_KEYFILE,
            settings.LIVE_SERVER_BASEDIR)
        return livehosting.LiveHostingManager(
            live_domain, live_cname, sftp_connection, rsync_helper, state)
    elif back_end_type == "sftp":
        logger.info("Initalising SFTP back end")
        logger.debug("Back end parameters are: %s" % back_end_params)
        permission_map = {
            'r': back_end_params['chmod']['default'],
            'w': back_end_params['chmod']['writeable'],
            'c': back_end_params['chmod']['writeable']
        }
        manager_back_end = backends.SFTPUploadBackEnd(
            back_end_params['host'], back_end_params['username'], back_end_params['password'],
            back_end_params['basedir'], back_end_params['port'], permission_map)
        return manifestbased.ManifestUploadManager(manager_back_end, test_url, state)
    elif back_end_type == "ftp":
        logger.info("Initalising FTP back end")
        logger.debug("Back end parameters are: %s" % back_end_params)
        permission_map = {'r': back_end_params['chmod']['default'],
                          'w': back_end_params['chmod']['writeable'],
                          'c': back_end_params['chmod']['writeable']}
        manager_back_end = backends.BoostedFTPUploadBackEnd(
            back_end_params['host'], back_end_params['username'], back_end_params['password'],
            back_end_params['basedir'], back_end_params['port'], permission_map)
        return manifestbased.ManifestUploadManager(manager_back_end, test_url, state)
    elif back_end_type == "ftps":
        logger.info("Initalising FTPS back end")
        logger.debug("Back end parameters are: %s" % back_end_params)
        permission_map = {'r': back_end_params['chmod']['default'],
                          'w': back_end_params['chmod']['writeable'],
                          'c': back_end_params['chmod']['writeable']}
        manager_back_end = backends.BoostedFTPUploadBackEnd(
            back_end_params['host'], back_end_params['username'], back_end_params['password'],
            back_end_params['basedir'], back_end_params['port'], permission_map, ssl=True)
        return manifestbased.ManifestUploadManager(manager_back_end, test_url, state)
    else:
        logger.info("Unknown back_end_type: %s" % back_end_type)
