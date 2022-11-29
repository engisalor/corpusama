import logging

logger = logging.getLogger(__name__)

__version__ = "0.1.0"  # x-release-please-version


def current():
    """Logs the library's current version."""

    logger.debug(__version__)
