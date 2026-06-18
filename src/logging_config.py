import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

APP_LOGGERS = ("llm", "llm.questions", "llm.simplify")
NOISY_LOGGERS = (
    "httpcore",
    "httpcore.http11",
    "httpcore.connection",
    "httpx",
    "openai",
    "openai._base_client",
    "urllib3",
)


def is_debug_mode():
    return os.environ.get("LOG_LEVEL", "INFO").upper() == "DEBUG"


def setup_logging():
    env_path = Path(os.environ.get("APP_ENV_FILE", ".env"))
    if env_path.exists():
        load_dotenv(env_path, override=False)

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    app_handler = logging.StreamHandler(
        open(os.environ.get("LOG_STREAM", "/dev/stderr"), "w", encoding="utf-8")
    )
    app_handler.setLevel(level)
    app_handler.setFormatter(formatter)

    for logger_name in APP_LOGGERS:
        app_logger = logging.getLogger(logger_name)
        app_logger.handlers = [app_handler]
        app_logger.setLevel(level)
        app_logger.propagate = False

    if is_debug_mode() and os.environ.get("LOG_HTTP_DEBUG", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        for logger_name in NOISY_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.getLogger("werkzeug").setLevel(
        logging.WARNING if level > logging.DEBUG else logging.INFO
    )
