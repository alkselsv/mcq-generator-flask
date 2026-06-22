"""RQ worker entry point with logging configured."""

import sys

from logging_config import setup_logging

setup_logging()

from rq.cli import main

if __name__ == "__main__":
    sys.argv = ["rq"] + sys.argv[1:]
    main()
