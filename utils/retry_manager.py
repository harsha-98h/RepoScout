"""
Retry Manager for ReAct Agent.

Uses typed custom exceptions from :mod:`utils.exceptions` and exponential
backoff with jitter.  Generic :class:`Exception` is no longer raised
directly; callers receive specific types they can inspect.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from utils.exceptions import RepoScoutError
from utils.logger import setup_logger

logger = setup_logger(__name__)

_T = TypeVar("_T")


class RetryManager:
    """Manage retry logic with exponential backoff and jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> None:
        """Initialise the manager.

        Args:
            max_retries: Maximum number of attempts (including the first call).
            base_delay:  Starting delay in seconds.
            max_delay:   Upper cap on the delay in seconds.
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_with_retry(
        self, func: Callable[..., _T], *args: Any, **kwargs: Any
    ) -> _T:
        """Execute *func* with automatic retries on retryable errors.

        Args:
            func:   Callable to execute.  Should raise a subclass of
                    :class:`utils.exceptions.RepoScoutError` (or
                    :class:`requests.exceptions.RequestException`) to signal
                    a retryable failure.
            *args:  Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func* on success.

        Raises:
            The last exception raised by *func* when all attempts fail.
        """
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("🔄 Attempt %d/%d", attempt, self.max_retries)
                result: _T = func(*args, **kwargs)
                if attempt > 1:
                    logger.info("✅ Succeeded on attempt %d", attempt)
                return result

            except RepoScoutError as exc:
                last_exc = exc
                # Use the ``retry`` flag carried by the exception if present
                if not getattr(exc, "retry", True):
                    logger.error("❌ Non-retryable error — aborting: %s", exc)
                    raise

                logger.warning("⚠️  %s", exc)

            except Exception as exc:  # network / OS level errors
                last_exc = exc
                logger.warning("⚠️  Unexpected error: %s", exc)

            if attempt < self.max_retries:
                wait = self._backoff(attempt)
                logger.info("⏳ Waiting %.2fs before next attempt…", wait)
                time.sleep(wait)
            else:
                logger.error("❌ Max retries (%d) exhausted.", self.max_retries)

        assert last_exc is not None  # always set when loop ends without return
        raise last_exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with ±50 % jitter.

        Args:
            attempt: 1-indexed current attempt number.

        Returns:
            Seconds to sleep before the next attempt.
        """
        exponential = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        jitter = random.uniform(0, exponential * 0.5)
        return exponential + jitter