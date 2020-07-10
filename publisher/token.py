from . import settings

import jwt
import abc
import re

import logging
logger = logging.getLogger(__name__)


class InvalidToken(Exception):
    """ Raised when an invalid token is detected """


class InvalidTokenType(InvalidToken):
    """ Raised when an unknown or invalid token type is detected """


class InvalidBackendData(Exception):
    """ Raised when the request contains invalid backend configurations """


class PublisherToken(object, metaclass=abc.ABCMeta):
    """
    Abstract base class for all jwt based publisher tokens
    """

    TYPE = None
    TYPE_INTERNAL = 'internal'
    TYPE_EXTERNAL = 'external'

    FIELD_TYPE = 'type'
    FIELD_INSTANCE = 'instance'

    PAYLOAD_SIZE = 2

    PROTOCOL_PARAMETERS = []

    def __init__(self, token_payload):
        self.instance = None
        self._process_payload(token_payload)

    def _process_payload(self, token_payload):
        """
        Extracts and validates the token payload depending on the token type

        :param token_payload: the jwt token payload/data
        :type token_payload: dict
        """
        logger.debug("Validating internal token payload: %s" % token_payload)

        if self.PAYLOAD_SIZE != len(token_payload):
            raise InvalidToken('Invalid token payload size, expected %i, got %i' %
                               (self.PAYLOAD_SIZE, len(token_payload)))

        if token_payload.get(self.FIELD_TYPE, None) != self.TYPE:
            raise InvalidTokenType('Invalid token payload for this token class')

        self.instance = token_payload.get(self.FIELD_INSTANCE)
        if not self.instance:
            raise InvalidTokenType('Token payload does not define the related instance')

    def get_instance(self):
        """
        Returns the instance name

        :return: the instance name
        :rtype: str
        """
        return self.instance

    def validate_download_url(self, download_url):
        """
        Validates the given download url against this token

        :param download_url: the download url that should be validated
        :type download_url: str

        :return: True when the given URL is valid for this token
        :rtype: bool
        """
        pattern = self.get_instance()
        match = re.match(pattern, download_url)
        logger.debug("Token validation result for %s: %s", download_url, match is not None)
        return match is not None

    @abc.abstractmethod
    def get_protocol(self, request_data):
        return None

    def get_protocol_parameters(self, request_data):
        """
        Extracts the protocol parameters from the given request_data

        :param request_data: the request data
        :type request_data: dict

        :return: the extracted protocol parameters
        :rtype: dict
        """
        try:
            parameters = {}
            for p in self.PROTOCOL_PARAMETERS:
                parameters[p] = request_data[p]
            return parameters
        except KeyError:
            raise InvalidBackendData('Protocol parameter missing: %s' % p)


class InternalPublisherToken(PublisherToken):
    """
    PublisherToken for publishing on our own live hosting platform
    """

    TYPE = PublisherToken.TYPE_INTERNAL
    FIELD_DOMAIN = 'domain'
    PAYLOAD_SIZE = 3
    PROTOCOL_PARAMETERS = {'cname', 'domain'}

    def __init__(self, token_payload):
        self.domain = None
        super(InternalPublisherToken, self).__init__(token_payload)

    def get_protocol_parameters(self, request_data):
        res = super(InternalPublisherToken, self).get_protocol_parameters(request_data)
        if re.match(self.domain, res[self.FIELD_DOMAIN]) is None:
            raise InvalidBackendData('backend param domain invalid: %s' % res[self.FIELD_DOMAIN])
        return res

    def _process_payload(self, token_payload):
        super(InternalPublisherToken, self)._process_payload(token_payload)
        self.domain = token_payload.get(self.FIELD_DOMAIN)
        if not self.domain:
            raise InvalidToken('Token payload does not define the live domain')

    def get_protocol(self, request_data):
        return "internal"


class ExternalPublisherToken(PublisherToken):
    """
    PublisherToken for publishing to external (S)FTP servers
    """

    TYPE = PublisherToken.TYPE_EXTERNAL
    PROTOCOL_PARAMETERS = {'host', 'username', 'password', 'basedir', 'port', 'chmod'}
    FIELD_PROTOCOL = 'protocol'

    def get_protocol(self, request_data):
        try:
            return request_data[self.FIELD_PROTOCOL]
        except KeyError:
            raise InvalidBackendData('Protocol is not defined')


class PublisherTokenFactory(object):
    """
    Factory class for the PublisherToken classes
    """

    def __init__(self, jwt_secret):
        self._secret = jwt_secret

    def _decode_token_payload(self, jwt_token_encoded=settings.PUBLISHER_TOKEN_SECRET):
        """
        Decodes the jwt payload and validates the jwt signature

        :param jwt_token_encoded: the encoded json web token
        :type jwt_token_encoded: str

        :return: the token payload
        :rtype: dict
        """
        try:
            token_payload = jwt.decode(jwt_token_encoded, self._secret)
        except jwt.ExpiredSignature:
            raise InvalidToken('ExpiredSignature')
        except jwt.DecodeError:
            raise InvalidToken('DecodeError')
        return token_payload

    def create_token(self, jwt_token_encoded):
        """
        Creates a new PublisherToken from the given json web token

        :param jwt_token_encoded: the encoded json web token
        :type jwt_token_encoded: str

        :return: a new created PublisherTokenObject
        :rtype: PublisherToken
        """
        token_payload = self._decode_token_payload(jwt_token_encoded)
        if PublisherToken.FIELD_TYPE not in token_payload:
            raise InvalidTokenType('Token type is not defined')

        if token_payload[PublisherToken.FIELD_TYPE] == PublisherToken.TYPE_INTERNAL:
            return InternalPublisherToken(token_payload)
        elif token_payload[PublisherToken.FIELD_TYPE] == PublisherToken.TYPE_EXTERNAL:
            return ExternalPublisherToken(token_payload)
        else:
            raise InvalidTokenType('Unknown token type')
