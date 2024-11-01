"""Current release version."""
import logging

logger = logging.getLogger(__name__)

__version__ = "0.4.0"  # x-release-please-version


def current() -> None:
    """Logs the current version."""

    logger.debug(__version__)
