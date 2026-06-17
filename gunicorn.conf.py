import os

bind = "0.0.0.0:5000"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
timeout = 900
graceful_timeout = 30
pythonpath = "src"
max_requests = 50
max_requests_jitter = 10
