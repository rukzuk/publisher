# Create your views here.
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from django.conf import settings

from rukzuk.viewdecorators import require_client_version
from rukzuk.viewdecorators import UrlPatternDecorator
from rukzuk.httpresponses import HttpJSONResponse, HttpResponseConflict

from . import tasks
from . import token

from hashlib import sha1

import json
import time

import functools

from django.http import HttpResponseServerError
from django.http import HttpResponseBadRequest

from celery import states
from celery.exceptions import MaxRetriesExceededError

import logging
logger = logging.getLogger(__name__)


urlpatterns = UrlPatternDecorator()


def calc_publish_task_id(download_url):
    return sha1(str.encode(download_url)).hexdigest()


def result_to_json(async_result):
    remaining_time = None
    percent = None
    msg = None
    timestamp = None
    state = async_result.state
    result = async_result.result
    if state == states.PENDING:
        status = 'UNKNOWN'
    elif state == states.SUCCESS:
        status = 'FINISHED'
        timestamp = result.get('timestamp', None)
    elif state in states.PROPAGATE_STATES:
        status = 'FAILED'
        if isinstance(async_result.result, MaxRetriesExceededError):
            logger.error(str(async_result.result))
            msg = "Can't retry publishing. To many error occurred."
        else:
            msg = str(async_result.result)
    else:
        status = 'INPROGRESS'
        if isinstance(result, dict):
            msg = result.get("msg", None)
            perc = result.get('percent', None)
            percent = int(perc * 100) if perc else None
            remaining_time = result.get('remaining', None)
            timestamp = result.get('timestamp', None)
            if 'heartbeat' in result:
                if time.time() - result['heartbeat'] > 60 * 60 * 3:
                    status = 'FAILED'
                    msg = 'No heart beat received from worker task'
        else:
            msg = str(result)
    return_value = {
        'status': status,
        'msg': msg,
        'percent': percent,
        'remaining': remaining_time,
        'timestamp': timestamp
    }
    logger.debug("Result is: %s" % return_value)
    return return_value


def require_jwt(view_func):
    """
    Decorator that extracts the jwt pubisher token from the request of
    the decorated view and adds it as an parameter
    """
    @functools.wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        try:
            token_factory = token.PublisherTokenFactory(settings.PUBLISHER_TOKEN_SECRET)
            publisher_token = token_factory.create_token(request.POST['token'])
            return view_func(request, publisher_token, *args, **kwargs)
        except KeyError:
            msg = 'No token found'
            logger.exception(msg)
            return HttpResponseBadRequest(msg)
        except token.InvalidToken:
            msg = 'Malformed token detected'
            logger.exception(msg)
            return HttpResponseBadRequest(msg)
    return _wrapped


#
# Views starting here
#

@urlpatterns.url(r'^delete/')
@require_POST
@csrf_exempt
@require_client_version(min_version=2)
@require_jwt
def delete_job(request, publisher_token):
    try:
        job_data_as_json = request.POST['data']
    except KeyError:
        return HttpResponseBadRequest('data is missing')
    job_data = json.loads(job_data_as_json)

    # Create new job
    try:
        # Check that the task doesn't exists
        protocol = publisher_token.get_protocol(job_data)
        backend_params = publisher_token.get_protocol_parameters(job_data)
        if protocol == 'internal':
            tasks.delete.delay(protocol, backend_params)
            msg = "delete Task added"
            logger.info(msg)
            return HttpJSONResponse((0, msg))
        else:
            msg = "not internally hosted, skipping"
            logger.info(msg)
            return HttpJSONResponse((0, msg))
    except Exception:
        msg = "Unknown Error while adding delete task for"
        logger.exception(msg)
        return HttpResponseServerError(json.dumps((255, msg)),
                                       content_type="application/json")


@urlpatterns.url(r'^add/')
@require_POST
@csrf_exempt
@require_client_version(min_version=2)
@require_jwt
def add_job(request, publisher_token):
    """
    This view adds publisher job to the worker queue

    :param request: The current http request
    :param request: django.http.HttpRequest
    :param publisher_token: the jwt publisher token
    :type publisher_token: token.PublisherToken

    :return: The HTTP response
    :rtype: django.http.HttpResponse
    """
    try:
        download_url = request.POST['download_url']
    except KeyError:
        return HttpResponseBadRequest('download_url missing')

    status_url = request.POST.get('status_url', None)

    if not publisher_token.validate_download_url(download_url):
        logger.warn("Invalid token '%s' for %s"
                    % (publisher_token.get_instance(), download_url))
        return HttpResponseBadRequest('Invalid token for this download URL')

    try:
        job_data_as_json = request.POST['data']
    except KeyError:
        return HttpResponseBadRequest('data is missing')
    job_data = json.loads(job_data_as_json)
    test_url = job_data.get('test_url', None)

    # Create new job
    task_id = calc_publish_task_id(download_url)
    try:
        # Check that the task doesn't exists
        state = tasks.publish.AsyncResult(task_id).state  # @UndefinedVariable
        if state != 'PENDING':
            raise IntegrityError(
                "Task for '%s' with id '%s' already exists (%s)"
                % (download_url, task_id, state))

        publish_args = (download_url, test_url, status_url,
                        publisher_token.get_protocol(job_data),
                        publisher_token.get_protocol_parameters(job_data))

        tasks.publish.apply_async(args=publish_args, task_id=task_id)
        msg = "Task for '%s' with id '%s' added" % (download_url, task_id)
        logger.info(msg)
        return HttpJSONResponse((0, msg))
    except IntegrityError as e:
        logger.warning(e.message)
        return HttpResponseConflict(json.dumps((1, e.message)),
                                    content_type="application/json")
    except Exception:
        msg = "Unknown Error while adding task for %s" % download_url
        logger.exception(msg)
        return HttpResponseServerError(json.dumps((255, msg)),
                                       content_type="application/json")


@urlpatterns.url(r'^status/')
@csrf_exempt
@require_client_version(min_version=2)
@require_jwt
def get_job_state(request, publisher_token):
    """
    This view the publisher job status

    :param request: The current http request
    :param request: django.http.HttpRequest
    :param publisher_token: the jwt publisher token
    :type publisher_token: token.PublisherToken

    :return: The HTTP response
    :rtype: django.http.HttpResponse
    """
    try:
        download_url = request.POST['download_url']
    except:
        return HttpResponseBadRequest('download_url missing')
    if not publisher_token.validate_download_url(download_url):
        logger.warn('Invalid token for URL: %s' % download_url)
        return HttpResponseBadRequest('Invalid token for this download URL')

    task_id = calc_publish_task_id(download_url)
    try:
        asyc_result = tasks.publish.AsyncResult(task_id)  # @UndefinedVariable
        return HttpJSONResponse(result_to_json(asyc_result))
    except Exception as e:
        logger.exception("Some thing went wrong here!")
        raise e
