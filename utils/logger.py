"""
Logging utility for RepoScout.

Provides rich, timestamped log output with level indicators.
Set the ``DEBUG`` environment variable to ``true`` to see verbose output.
"""

from __future__ import annotations

import logging
import os
import sys

# ------------------------------------------------------------------
# Resolve the root log level from the environment once at import time
# ------------------------------------------------------------------
_ENV_DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
_ROOT_LEVEL: int = logging.DEBUG if _ENV_DEBUG else logging.INFO

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def setup_logger(name: str = "reposcout", level: int | None = None) -> logging.Logger:
    """Return a named :class:`logging.Logger` with a stdout handler.

    Args:
        name:  Logger name (use ``__name__`` in each module).
        level: Override log level. Defaults to ``INFO`` (or ``DEBUG`` when the
               ``DEBUG`` env-var is ``true``).

    Returns:
        Configured :class:`logging.Logger` instance.
    """
    if level is None:
        level = _ROOT_LEVEL

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers when the function is called multiple times for
    # the same logger name (e.g. during test collection).
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(_FORMATTER)
    logger.addHandler(handler)

    # Prevent log records from bubbling up to the root logger.
    logger.propagate = False

    return logger