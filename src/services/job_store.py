import json
import os
import time
import uuid

from services.redis_client import get_redis

JOB_TTL = int(os.environ.get("JOB_TTL", "3600"))
JOB_STALE_TIMEOUT = int(os.environ.get("JOB_STALE_TIMEOUT", "900"))
JOB_KEY_PREFIX = "mcq:job:"
TERMINAL_STATUSES = frozenset({"done", "error", "cancelled"})


class JobCancelled(Exception):
    """Raised when a running job is cancelled by the user."""

    def __init__(self, partial_questions=None):
        super().__init__("Job cancelled")
        self.partial_questions = partial_questions or []


def _job_key(job_id):
    return f"{JOB_KEY_PREFIX}{job_id}"


def _save_job(job_id, job):
    get_redis().setex(_job_key(job_id), JOB_TTL, json.dumps(job, ensure_ascii=False))


def _load_job(job_id):
    raw = get_redis().get(_job_key(job_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def create_job(job_type="generate"):
    job_id = str(uuid.uuid4())
    job = {
        "job_type": job_type,
        "status": "pending",
        "created_at": time.time(),
        "error": None,
        "question_id": None,
        "simplified_text": None,
        "rq_job_id": None,
        "progress_current": 0,
        "progress_total": None,
    }
    _save_job(job_id, job)
    return job_id


def get_job(job_id):
    job = _load_job(job_id)
    if not job:
        return None

    if job["status"] == "running":
        started_at = job.get("started_at", job["created_at"])
        if time.time() - started_at > JOB_STALE_TIMEOUT:
            job["status"] = "error"
            job["error"] = "Генерация прервана. Попробуйте снова."
            _save_job(job_id, job)

    return job


def is_cancelled(job_id):
    job = _load_job(job_id)
    return bool(job and job.get("status") == "cancelled")


def update_job(job_id, **fields):
    job = _load_job(job_id)
    if not job:
        return None

    # Do not overwrite a terminal status (e.g. cancelled → done).
    if job["status"] in TERMINAL_STATUSES:
        new_status = fields.get("status")
        if new_status is not None and new_status != job["status"]:
            return job
        # After cancel allow attaching partial generation results / RQ id.
        if job["status"] == "cancelled":
            allowed = {
                "rq_job_id",
                "question_id",
                "progress_current",
                "progress_total",
            }
            if set(fields.keys()).issubset(allowed):
                job.update(fields)
                _save_job(job_id, job)
                return job
            return job
        # After done/error only allow linking RQ id (race with enqueue).
        if set(fields.keys()) != {"rq_job_id"}:
            return job

    if fields.get("status") == "running" and job.get("status") != "running":
        fields["started_at"] = time.time()

    job.update(fields)
    _save_job(job_id, job)
    return job


def cancel_job(job_id):
    job = _load_job(job_id)
    if not job:
        return None

    if job["status"] in TERMINAL_STATUSES:
        return job

    job["status"] = "cancelled"
    job["error"] = None
    _save_job(job_id, job)
    return job


def cleanup_old_jobs():
    pass
