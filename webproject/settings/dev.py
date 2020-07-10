"""
Django local settings for customerarea project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
from .defaults import *  # noqa

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

import os
import sys

CELERY_ALWAYS_EAGER = True

if ('test' in sys.argv) or ('JENKINS_URL' in os.environ and 'jenkins' in sys.argv):
    DEBUG = False
    TEMPLATE_DEBUG = False
    import logging
    logging.disable(logging.CRITICAL)

    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    BROKER_BACKEND = 'memory'
