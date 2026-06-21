import threading
import time
import uuid

JOB_TTL = 3600  # 1 hour after completion

_jobs = {}
_lock = threading.Lock()


def create_job(job_type="generate"):
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "job_type": job_type,
            "status": "pending",
            "created_at": time.time(),
            "error": None,
            "questions": None,
            "question_id": None,
            "simplified_text": None,
        }
    return job_id


def get_job(job_id):
    with _lock:
        return _jobs.get(job_id)


def update_job(job_id, **fields):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)


def cleanup_old_jobs():
    cutoff = time.time() - JOB_TTL
    with _lock:
        expired = [
            job_id
            for job_id, job in _jobs.items()
            if job["status"] in ("done", "error") and job["created_at"] < cutoff
        ]
        for job_id in expired:
            del _jobs[job_id]
