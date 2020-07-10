# ConfigParser for ini file handling
import configparser

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)

SITE_ID = os.environ.get('SITE_ID', 1)

config = configparser.ConfigParser(strict=True, interpolation=None)
config_files = [
    # Sane defaults
    os.path.join(PROJECT_DIR, 'settings', 'defaults.ini'),
    # regular settings
    os.path.join(BASE_DIR, 'settings.ini'),
    # dev stuff
    os.path.join(BASE_DIR, 'settings-dev.ini'),
    ]
config.read(config_files)

#
# DEBUG settings
#
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config.getboolean('services', 'debug')
TEMPLATE_DEBUG = DEBUG

#
# E-Mail settings
#
EMAIL_SUBJECT_PREFIX = '[rukzuk services]'

if config.get('email', 'host'):
    EMAIL_HOST = config.get('email', 'host')
    EMAIL_PORT = config.get('email', 'port')

if config.get('email', 'server-email'):
    SERVER_EMAIL = config.get('email', 'server-email')

ADMINS = []
if config.items('admin-emails'):
    for _key, value in config.items('admin-emails'):
        name, sep, email = value.partition(',')
        ADMINS.append((name.strip(), email.strip()))

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
ROOT_DIR = os.path.dirname(PROJECT_ROOT)

MANAGERS = ADMINS

#
# Database
#
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
# DATABASES = {}
# if config.getboolean('database', 'internaldb'):
#     DATABASES['default'] = {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#         }
# else:
#     DATABASES['default'] = {
#         'ENGINE': 'django.db.backends.%s' % config.get('database', 'engine'),
#         'NAME': config.get('database', 'name'),
#         'HOST': config.get('database', 'host'),
#         'PORT': config.get('database', 'port'),
#         'USER': config.get('database', 'user'),
#         'PASSWORD': config.get('database', 'pass'),
#     }


# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
def parse_allowed_hosts(hosts_string):
    """
    Helper method to parse the host line

    :param hosts_string: a string with ; seperated hosts
    :type hosts_string: str

    :return: a list of host names
    :rtype: list
    """
    hosts = hosts_string.split(';')
    return [host.strip() for host in hosts if host]

ALLOWED_HOSTS = parse_allowed_hosts(config.get('services', 'allowed-hosts'))

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

ugettext = lambda s: s
LANGUAGES = (('en', ugettext('English')), ('de', ugettext('German')),)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True
# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

#
# Static files (CSS, JavaScript, Images)
#
# https://docs.djangoproject.com/en/1.6/howto/static-files/
#STATIC_ROOT = os.path.join(BASE_DIR, 'static')
#STATIC_URL = config.get('services', 'static-url')
#STATICFILES_DIRS = (os.path.join(PROJECT_DIR, 'static'),)

#MEDIA_URL = config.get('services', 'media-url')
#MEDIA_ROOT = config.get('services', 'media-root') or os.path.join(BASE_DIR, 'media')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config.get('services', 'secret-key')


MIDDLEWARE_CLASSES = ()

ROOT_URLCONF = 'webproject.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'webproject.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates"
    # or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

FIXTURE_DIRS = (os.path.join(PROJECT_ROOT, 'fixtures'), )

LOCALE_PATHS = (os.path.join(PROJECT_ROOT, 'locale'), )

INSTALLED_APPS = (
    'publisher',
#    'django.contrib.admin',
#    'django.contrib.auth',
#    'django.contrib.contenttypes',
#    'django.contrib.sessions',
#    'django.contrib.messages',
#    'django.contrib.staticfiles',
)

#
# Logging
#

# Used for syslog settings below
LOG_BASE_DIR = config.get('services', 'logdir')
SYSLOG_NAME = 'rukzukservices'

if not LOG_BASE_DIR:
    LOG_BASE_DIR = os.path.join(BASE_DIR, 'log')

from logging.handlers import SysLogHandler
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s '
                      '%(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
        },
        # Syslog/logstash needs an program prefix
        'syslog': {
            'format': SYSLOG_NAME + '[%(process)d]: [%(name)s] %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda _record: DEBUG,
        },
        'log_files': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda _record: config.getboolean('services', 'logfiles'),
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['require_debug_true']
        },
        'syslog': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'formatter': 'syslog',
            'address': '/dev/log',
            'facility': SysLogHandler.LOG_LOCAL2,
            'filters': ['require_debug_false']
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
            'filters': ['require_debug_false']
        },
        'debuglogfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.WatchedFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(LOG_BASE_DIR, 'django-debug.log'),
            'filters': ['require_debug_true', 'log_files'],
        },
        'logfile': {
            'level': 'INFO',
            'class': 'logging.handlers.WatchedFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(LOG_BASE_DIR, 'django-info.log'),
            'filters': ['log_files']
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['syslog', 'mail_admins', 'logfile', ],
            'level': 'ERROR',
            'propagate': True,
        },
        'django': {
            'handlers': ['syslog', 'null', 'console', 'logfile', ],
            'level': 'ERROR',
        },
        'publisher': {
            'handlers': ['syslog', 'console', 'logfile', 'debuglogfile'],
            'level': 'DEBUG',
        },
        'pageshooter': {
            'handlers': ['syslog', 'console', 'logfile', 'debuglogfile'],
            'level': 'DEBUG',
        },
        'rukzuk': {
            'handlers': ['syslog', 'console', 'logfile', 'debuglogfile'],
            'level': 'DEBUG',
        },
        'keepalivestatus': {
            'handlers': ['syslog', 'console', 'logfile', 'debuglogfile'],
            'level': 'DEBUG',
        }
    }
}

#
# Celery settings
#
CELERY_BROKER_URL = config.get('celery', 'broker-url')
CELERY_SEND_TASK_ERROR_EMAILS = True
CELERY_TIMEZONE = TIME_ZONE

CELERY_TASK_RESULT_EXPIRES = 12 * 60 * 60  # 12 h
CELERY_RESULT_BACKEND = config.get('celery', 'result-backend')
# use https://pypi.python.org/pypi/django-celery-results/
#CELERY_RESULT_BACKEND = 'django-db'
#CELERY_CACHE_BACKEND = 'django-cache'
# BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 60 * 60}

# TODO: CELERYBEAT_SCHEDULE!!!


#######################################################################
#
# Own stuff
#
#######################################################################

#
# Publisher settings
#
PUBLISHER_TOKEN_SECRET = config.get('publisher', 'jwt-secret')


# Setting global temp dir for this application
if config.get('services', 'tempdir'):
    import tempfile
    tempfile.tempdir = config.get('services', 'tempdir')


#
# live server settings
#
LIVE_SERVER = config.get('publisher', 'live-server')
LIVE_SERVER_USER = config.get('publisher', 'live-server-user')
LIVE_SERVER_KEYFILE = config.get('publisher', 'live-server-keyfile')
LIVE_SERVER_BASEDIR = config.get('publisher', 'live-server-basedir')
