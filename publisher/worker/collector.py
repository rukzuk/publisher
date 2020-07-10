'''
Created on 23.01.2013

@author: mtrunner
'''
# Used to unzip the zip file
import zipfile
# Used to download the zip file from the instance
import urllib.request, urllib.error, urllib.parse
import contextlib
# Used as a in memory buffer of the downloaded zip file
import tempfile

# Logging support
import logging
logger = logging.getLogger(__name__)

from publisher.worker.exceptions import NoRetryException


class ZIPCollector:
    """
    Collects the webside data from the instance and extracts it in a directory.
    """

    def collect(self, url, working_dir):
        """
        Download, validates a zip file and extracts it content to the given
        directory
        """
        downloaded_zip_file = self._downloadData(url)
        self._validateData(downloaded_zip_file)
        self._extractData(downloaded_zip_file, working_dir)

    def _downloadData(self, url):
        """
        Downloads the related content/data from the publisher instance and
        stores it in memory.

        Returns the file object of the download file
        """
        logger.debug("Downloading file from: %s" % url)
        with self._open_url(url) as url_file:
            mem_puffer = tempfile.SpooledTemporaryFile()
            mem_puffer.write(url_file.read())
            mem_puffer.seek(0)
            return mem_puffer

    def _validateData(self, zdata):
        """
        Validates the content of the zip file (zdata) and throws an exception
        when something is wrong with the given zip file
        """
        logger.debug("Checking magic number")
        if not self._is_zipfile(zdata):
            logger.warn("Magic number not found for ZIP file")
            raise NoRetryException("File is not a zip file")
        logger.debug("Magic number for ZIP found")

        with self._open_zip(zdata) as zfile:
            logger.debug("Validating content of the zip file")
            badfile = zfile.testzip()
            if badfile:
                logger.error("Internal zip file CRC of %s failed" % badfile)
                raise NoRetryException("Internal zip file CRC of %s failed"
                                       % badfile)
            logger.debug("All crc's are okay")

            logger.debug("Validating the filenames in the zip file")
            for name in zfile.namelist():
                # TODO os.path.join + os.path.abs
                if (name.find("..") >= 0) or name.startswith("/"):
                    logger.warning("Invalid filename in the zip file: %s"
                                   % name)
                    raise NoRetryException("Invalid filename in the zip"
                                           " file: %s" % name)
            logger.debug("All filenames are okay")

    def _extractData(self, zdata, working_dir):
        """
        Extracts the given zip file in the given directory.
        """
        with self._open_zip(zdata) as zfile:
            logger.debug("Extracting zip file")
            zfile.extractall(working_dir)
            logger.debug("All files extracted to %s" % working_dir)

    def _open_zip(self, zdata):
        """ Factory method for unit tests """
        return zipfile.ZipFile(zdata, 'r')

    def _open_url(self, url):
        """ Factory method for unit tests """
        return contextlib.closing(urllib.request.urlopen(url))

    def _is_zipfile(self, zdata):
        return zipfile.is_zipfile(zdata)
