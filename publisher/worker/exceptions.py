'''
Created on 30.01.2013

@author: mtrunner
'''


class RetryException(Exception):

    def __init__(self, msg, recovery_parameters):
        super(RetryException, self).__init__()
        self.message = msg
        self.recovery_parameters = recovery_parameters


class NoRetryException(Exception):
    pass
