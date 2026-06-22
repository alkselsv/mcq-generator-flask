import os

from redis import Redis

_client = None


def get_redis():
    global _client
    if _client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _client = Redis.from_url(redis_url, decode_responses=True)
    return _client
