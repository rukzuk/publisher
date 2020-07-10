'''
Created on 15.02.2013

@author: mtrunner
'''
from rukzuk import token
from functools import wraps
from django.http import HttpResponseBadRequest
from django.conf.urls import url

import logging
logger = logging.getLogger(__name__)


def require_token(token_type):

    def decorator(func):
        """
        Decorator that validates the token from the request and extracts it.
        """
        @wraps(func)
        def wrapper(request, *args, **kwds):
            try:
                token_as_base64 = request.POST['token']
            except:
                return HttpResponseBadRequest('No token found')

            # Validate token
            try:
                tok = token_type(token_as_base64)
            except token.InvalidTokenException as e:
                return HttpResponseBadRequest(e.message)
            except:
                logger.exception('Malformed token detected')
                return HttpResponseBadRequest('Malformed token detected')

            return func(request, *args, token=tok, **kwds)
        return wrapper
    return decorator


def require_client_version(min_version=None, max_version=None):
    """
    Decorator to check the client version
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwds):
            if 'client_version' not in request.POST:
                return HttpResponseBadRequest("No client version found")
            if min_version is not None \
                    and int(request.POST['client_version']) < min_version:
                return HttpResponseBadRequest(
                        "Unsupported client version (must be newer than %s)" \
                                              % min_version)
            if max_version is not None \
                    and int(request.POST['client_version']) > max_version:
                return HttpResponseBadRequest(
                        "Unsupported client version (must be older than %s)" \
                        % max_version)
            return func(request, *args, **kwds)
        return wrapper
    return decorator


class UrlPatternDecorator(list):

    def url(self, url_regex, kwargs=None, name=None):
        def decorator(func):
            self.append(url(url_regex, func, kwargs=kwargs, name=name))
            return func
        return decorator


def required_fields(*request_fields):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwds):
            for field in request_fields:
                if field not in request.POST:
                    return HttpResponseBadRequest('%s missing' % field)
            return func(request, *args, **kwds)
        return wrapper
    return decorator
