from django.conf import settings

PUBLISHER_TOKEN_SECRET = getattr(settings, 'PUBLISHER_TOKEN_SECRET', None)
LIVE_SERVER = getattr(settings, 'LIVE_SERVER', None)
LIVE_SERVER_USER = getattr(settings, 'LIVE_SERVER_USER', None)
LIVE_SERVER_KEYFILE = getattr(settings, 'LIVE_SERVER_KEYFILE', None)
LIVE_SERVER_BASEDIR = getattr(settings, 'LIVE_SERVER_BASEDIR', None)
