import os

from rq import Queue

from services.redis_client import get_redis
from services.tasks import run_generation, run_simplification

QUEUE_NAME = "mcq"
JOB_TIMEOUT = int(os.environ.get("RQ_JOB_TIMEOUT", "900"))

_queue = None


def get_queue():
    global _queue
    if _queue is None:
        _queue = Queue(QUEUE_NAME, connection=get_redis())
    return _queue


def enqueue_generation(job_id, text, num_questions):
    get_queue().enqueue(
        run_generation,
        job_id,
        text,
        num_questions,
        job_timeout=JOB_TIMEOUT,
        result_ttl=60,
        failure_ttl=3600,
    )


def enqueue_simplification(job_id, text):
    get_queue().enqueue(
        run_simplification,
        job_id,
        text,
        job_timeout=JOB_TIMEOUT,
        result_ttl=60,
        failure_ttl=3600,
    )
