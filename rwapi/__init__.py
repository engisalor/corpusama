import logging
from logging.handlers import TimedRotatingFileHandler

from . import convert, db
from .call import Call
from .manager import Manager

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
)

log_file = ".rwapi.log"
file_handler = TimedRotatingFileHandler(log_file, "midnight", backupCount=1)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)
