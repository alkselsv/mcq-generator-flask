import logging
import os
import sys

APP_LOGGERS = ("llm", "llm.questions", "llm.simplify")


def setup_logging():
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)
        handler.setFormatter(formatter)

    for logger_name in APP_LOGGERS:
        logging.getLogger(logger_name).setLevel(level)

    logging.getLogger("werkzeug").setLevel(
        logging.WARNING if level > logging.DEBUG else logging.INFO
    )
