import logging
import os
import sys


def setup_logging():
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    logging.getLogger("werkzeug").setLevel(
        logging.WARNING if level > logging.DEBUG else logging.INFO
    )
