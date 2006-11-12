import logging
import sys
import time


levels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class TimeOffsetFormatter(logging.Formatter):

    """Format timestamps as offsets since the beginning of logging"""

    def __init__(self, fmt=None, datefmt=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        self.startup_time = time.time()

    def formatTime(self, record, datefmt=None):
        offset = record.created - self.startup_time
        minutes = int(offset / 60)
        seconds = offset % 60
        return "%dm%.1fs" % (minutes, seconds)

def setup(config):
    level = config.get("backup", "log-level")

    formatter = TimeOffsetFormatter("%(asctime)s %(levelname)s: %(message)s")
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(levels[level.lower()])
    logger.addHandler(handler)
