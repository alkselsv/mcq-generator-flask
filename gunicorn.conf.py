import os

bind = "0.0.0.0:5000"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", "32"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "300"))
graceful_timeout = 120
keepalive = 2
backlog = 2048
pythonpath = "src"
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "0"))
max_requests_jitter = 10
loglevel = os.environ.get("LOG_LEVEL", "info").lower()


def post_worker_init(worker):
    from logging_config import setup_logging

    setup_logging()
