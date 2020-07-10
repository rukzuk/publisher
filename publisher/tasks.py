from publisher.worker.exceptions import RetryException
import publisher.worker

import time
import math
import urllib.request, urllib.error, urllib.parse
import json

from celery import current_app
from celery import shared_task

from celery.signals import after_task_publish

import logging
logger = logging.getLogger(__name__)


@shared_task(track_started=True, max_retries=4, ignore_result=True)
def delete(backend, backend_parameters):
    publisher.worker.delete(backend, backend_parameters)


@after_task_publish.connect
def update_sent_state(sender=None, headers=None, body=None, **kwargs):
    """
    Adds a SENT state for each task
    """
    # the task may not exist if sent using `send_task` which
    # sends tasks by name, so fall back to the default result backend
    # if that is the case.
    task = current_app.tasks.get(sender)
    backend = task.backend if task else current_app.backend
    if backend.get_status(headers['id']) == 'PENDING':
        backend.store_result(headers['id'], None, "SENT")


@shared_task(track_started=True, max_retries=4)
def publish(download_url, test_url, status_url, backend, backend_parameters,
            recovery=None):
    start_time = time.time()

    def update_state(state, percent=0, msg=None, remaining_time=None):
        meta = {'msg': msg, 'percent': percent, 'remaining': remaining_time,
                'timestamp': start_time, 'heartbeat': time.time()}
        custom_state = state.upper()
        publish.update_state(state=custom_state,  # @UndefinedVariable
                             meta=meta)

    try:
        publisher.worker.publish(download_url,
                                 test_url,
                                 backend,
                                 backend_parameters,
                                 recovery,
                                 state_callback=update_state)
        tell_finish.delay(status_url)
    except RetryException as e:
        logger.info("Added task ('%s') for later retry" % download_url)
        publish.retry(args=(download_url, test_url, status_url,
                            backend, backend_parameters),
                      kwargs={'recovery': e.recovery_parameters},
                      countdown=30 * math.pow(2, publish.request.retries))
    return {'timestamp': start_time}


@shared_task(track_started=True, max_retries=12,
             default_retry_delay=60 * 60, ignore_result=True)
def tell_finish(status_url):
    logger.debug('Calling %s' % status_url)
    data = urllib.request.urlopen(status_url, timeout=60)
    try:
        result = json.load(data)
        if not result['success']:
            logger.warn("Calling status url (%s) failed" % status_url)
            publish.retry(args=(status_url,))
    finally:
        data.close()
