import json
import time
import uuid

from services.redis_client import get_redis

JOB_TTL = 3600
JOB_STALE_TIMEOUT = 900
JOB_KEY_PREFIX = "mcq:job:"


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


def update_job(job_id, **fields):
    job = _load_job(job_id)
    if not job:
        return

    if fields.get("status") == "running" and job.get("status") != "running":
        fields["started_at"] = time.time()

    job.update(fields)
    _save_job(job_id, job)


def cleanup_old_jobs():
    pass
