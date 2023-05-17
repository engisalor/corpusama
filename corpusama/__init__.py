"A corpus management tool."
import logging
from logging.handlers import TimedRotatingFileHandler

log_file = ".logs/corpusama.log"
file_handler = TimedRotatingFileHandler(log_file, "midnight", backupCount=1)
stream_handler = logging.StreamHandler()

logging.basicConfig(
    encoding="utf-8",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    handlers=[stream_handler, file_handler],
)
