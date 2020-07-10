# Used to write down all files in the upload folder
import os
# Used to delete the temp folder and its content
import tempfile
import shutil

# Used for folder name calculation
import hashlib

from .collector import ZIPCollector

from .exceptions import RetryException
from .managers import init_manager

# Logging support
import logging
logger = logging.getLogger(__name__)


def get_tmp_dir(publish_id):
    """
    This method calculates a unique temp folder for the publish_id
    """
    md5 = hashlib.md5()
    md5.update(publish_id.encode("utf-8"))
    dirname = md5.hexdigest()
    os.path.join(tempfile.gettempdir(), dirname)
    temp_dir = os.path.join(tempfile.gettempdir(), dirname)
    return temp_dir


def clean_tmp_dir(tmp_dir):
    """
    Removes the working dir and all files in it
    """
    logger.debug("Check if temp folder %s exists" % tmp_dir)
    if os.path.exists(tmp_dir):
        logger.debug("Deleting temp folder: %s" % tmp_dir)
        shutil.rmtree(tmp_dir)


def _read_list_file(path):
    with open(path) as read_file:
        return [line.strip() for line in read_file]


def publish(download_url, test_url, backend, backend_parameters,
            recovery=None, state_callback=None):
    """
    Publishs a publishing file from download_url to the given back end server
    """
    try:
        # Prepare working dir
        working_dir = get_tmp_dir(download_url)
        if recovery is None or not os.path.exists(working_dir):
            # Prepares the job for upload
            if not os.path.exists(working_dir):
                os.mkdir(working_dir)
            collector = ZIPCollector()
            collector.collect(download_url, working_dir)

        # Init back end
        _manager = init_manager(test_url, backend, backend_parameters, state_callback)
        writeable_txt = os.path.join(working_dir, "writeable.txt")
        writeable_list = _read_list_file(writeable_txt)
        cache_txt = os.path.join(working_dir, "cache.txt")
        cache_list = _read_list_file(cache_txt)
        logger.debug("Writeable list: %s" % writeable_list)
        logger.debug("Cache list: %s" % cache_list)

        # Start job
        _manager.start(os.path.join(working_dir, "website"), recovery, writeable_list, cache_list)
        # Clean up
        clean_tmp_dir(working_dir)
    except RetryException as e:
        raise e

    except Exception as e:
        clean_tmp_dir(working_dir)
        raise e


def delete(backend, backend_parameters):
    manager = init_manager(None, backend, backend_parameters)
    manager.delete_all()
