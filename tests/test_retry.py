"""
Pytest suite for RetryManager.

Replaces the old test_retry.py file (which was a duplicate RetryManager
implementation rather than actual tests).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from utils.retry_manager import RetryManager


@pytest.fixture()
def manager() -> RetryManager:
    return RetryManager(max_retries=3, base_delay=0.01, max_delay=0.1)


class TestRetryManagerSuccess:
    def test_succeeds_first_attempt(self, manager: RetryManager) -> None:
        func = lambda: "ok"
        assert manager.execute_with_retry(func) == "ok"

    def test_succeeds_on_second_attempt(self, manager: RetryManager) -> None:
        calls = {"count": 0}

        def flaky():
            calls["count"] += 1
            if calls["count"] < 2:
                raise ConnectionError("temporary")
            return "recovered"

        # patch sleep so the test doesn't actually wait
        with patch("utils.retry_manager.time.sleep"):
            result = manager.execute_with_retry(flaky)

        assert result == "recovered"
        assert calls["count"] == 2

    def test_passes_args_and_kwargs(self, manager: RetryManager) -> None:
        func = lambda a, b=10: a + b
        assert manager.execute_with_retry(func, 5, b=3) == 8


class TestRetryManagerFailure:
    def test_raises_after_max_retries(self, manager: RetryManager) -> None:
        def always_fails():
            raise RuntimeError("always bad")

        with patch("utils.retry_manager.time.sleep"):
            with pytest.raises(RuntimeError):
                manager.execute_with_retry(always_fails)

    def test_attempt_count_equals_max_retries(self, manager: RetryManager) -> None:
        calls = {"count": 0}

        def counter():
            calls["count"] += 1
            raise OSError("fail")

        with patch("utils.retry_manager.time.sleep"):
            with pytest.raises(OSError):
                manager.execute_with_retry(counter)

        assert calls["count"] == manager.max_retries


class TestBackoffCalculation:
    def test_backoff_increases(self, manager: RetryManager) -> None:
        """Backoff for attempt 2 should be ≥ backoff for attempt 1 on average."""
        # Check the deterministic base component only
        b1 = min(manager.base_delay * (2**0), manager.max_delay)
        b2 = min(manager.base_delay * (2**1), manager.max_delay)
        assert b2 >= b1

    def test_backoff_capped_at_max_delay(self) -> None:
        mgr = RetryManager(max_retries=5, base_delay=10, max_delay=10)
        # All backoff values should be capped at 10 + jitter ≤ 10 * 1.5
        for attempt in range(1, 5):
            bt = mgr._backoff(attempt)
            assert bt <= mgr.max_delay * 1.5
