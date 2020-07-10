import abc

import logging
logger = logging.getLogger(__name__)


class PublishManager(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def start(self, working_dir, recovery=None, writeable_list=[], cache_list=[]):
        """
        Starts the synchronisation. This method uploads the local working directory on the
        configured server
        """
