import logging
import sys


levels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def setup(config):
    level = config.get("wibbr", "log-level")
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                        stream=sys.stdout,
                        level=levels[level.lower()])
