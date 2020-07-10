from django.http import response

import functools

import logging
logger = logging.getLogger(__name__)


def checkapikey(expected_key):
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            apikey = request.POST.get('apikey', None)
            if _wrapped_view.expected_key and _wrapped_view.expected_key != apikey:
                return response.HttpResponseForbidden()
            return view_func(request, *args, **kwargs)
        # Added indirection for better unit testing
        _wrapped_view.expected_key = expected_key
        return _wrapped_view
    return decorator
