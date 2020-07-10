'''
Created on 20.02.2013

@author: mtrunner
'''
from django.http import HttpResponse
import json


class HttpResponseConflict(HttpResponse):
    """
    Http response for 409 Conflict.

    .. seealso::
       * http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
    """
    status_code = 409


class HttpJSONResponse(HttpResponse):
    """
    HttpResponse that converts the given content into a json string and sets
    the right content type.
    """
    def __init__(self, content='', _content_type=None, status=None):
        super(HttpJSONResponse, self).__init__(json.dumps(content),
                                               content_type="application/json",
                                               status=status)
