import logging
import os

from rq import Queue
from rq.job import Job

from services.job_store import update_job
from services.redis_client import get_redis
from services.tasks import run_generation, run_simplification

logger = logging.getLogger(__name__)

QUEUE_NAME = "mcq"
JOB_TIMEOUT = int(os.environ.get("RQ_JOB_TIMEOUT", "900"))

_queue = None


def get_queue():
    global _queue
    if _queue is None:
        _queue = Queue(QUEUE_NAME, connection=get_redis())
    return _queue


def enqueue_generation(job_id, text, num_questions):
    rq_job = get_queue().enqueue(
        run_generation,
        job_id,
        text,
        num_questions,
        job_timeout=JOB_TIMEOUT,
        result_ttl=60,
        failure_ttl=3600,
    )
    job = update_job(job_id, rq_job_id=rq_job.id)
    if job and job.get("status") == "cancelled":
        cancel_rq_job(rq_job.id)
    return rq_job.id


def enqueue_simplification(job_id, text):
    rq_job = get_queue().enqueue(
        run_simplification,
        job_id,
        text,
        job_timeout=JOB_TIMEOUT,
        result_ttl=60,
        failure_ttl=3600,
    )
    job = update_job(job_id, rq_job_id=rq_job.id)
    if job and job.get("status") == "cancelled":
        cancel_rq_job(rq_job.id)
    return rq_job.id


def cancel_rq_job(rq_job_id):
    """Cancel a queued RQ job so the worker never starts it."""
    if not rq_job_id:
        return False
    try:
        rq_job = Job.fetch(rq_job_id, connection=get_redis())
        rq_job.cancel()
        return True
    except Exception as error:
        logger.info("Не удалось отменить RQ-задачу %s: %s", rq_job_id, error)
        return False
