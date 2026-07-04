"""
Pytest suite for ErrorDetector.

Replaces the old test_error_detection.py print-based script.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from utils.error_handler import ErrorDetector
from utils.exceptions import GitHubAPIError, RateLimitExceeded


def _mock_response(status_code: int, headers: dict | None = None) -> MagicMock:
    """Build a minimal mock mimicking a requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    return resp


class TestClassifyAPIError:
    def test_success_200(self) -> None:
        info = ErrorDetector.classify_api_error(_mock_response(200))
        assert info["is_error"] is False

    def test_rate_limit_403(self) -> None:
        resp = _mock_response(403, {"X-RateLimit-Remaining": "0"})
        info = ErrorDetector.classify_api_error(resp)
        assert info["is_error"] is True
        assert info["type"] == "RATE_LIMIT"
        assert info["retry"] is True
        assert info["wait_time"] == 3600

    def test_forbidden_403_not_rate_limit(self) -> None:
        resp = _mock_response(403, {"X-RateLimit-Remaining": "59"})
        info = ErrorDetector.classify_api_error(resp)
        assert info["type"] == "FORBIDDEN"
        assert info["retry"] is False

    def test_not_found_404(self) -> None:
        info = ErrorDetector.classify_api_error(_mock_response(404))
        assert info["type"] == "NOT_FOUND"

    def test_invalid_query_422(self) -> None:
        info = ErrorDetector.classify_api_error(_mock_response(422))
        assert info["type"] == "INVALID_QUERY"

    def test_server_error_500(self) -> None:
        info = ErrorDetector.classify_api_error(_mock_response(500))
        assert info["is_error"] is True
        assert info["category"] == "SERVER_ERROR"
        assert info["retry"] is True

    def test_unknown_status(self) -> None:
        info = ErrorDetector.classify_api_error(_mock_response(999))
        assert info["category"] == "UNKNOWN"
        assert info["retry"] is False


class TestClassifyNetworkError:
    def test_timeout(self) -> None:
        exc = requests.exceptions.Timeout("timed out")
        info = ErrorDetector.classify_network_error(exc)
        assert info["type"] == "TIMEOUT"
        assert info["retry"] is True

    def test_connection_error(self) -> None:
        exc = requests.exceptions.ConnectionError("conn refused")
        info = ErrorDetector.classify_network_error(exc)
        assert info["type"] == "CONNECTION_ERROR"

    def test_unknown_exception(self) -> None:
        info = ErrorDetector.classify_network_error(ValueError("oops"))
        assert info["retry"] is False


class TestHelpers:
    def test_should_retry_true(self) -> None:
        assert ErrorDetector.should_retry({"retry": True}) is True

    def test_should_retry_false(self) -> None:
        assert ErrorDetector.should_retry({"retry": False}) is False

    def test_get_wait_time_default(self) -> None:
        assert ErrorDetector.get_wait_time({}) == 1

    def test_get_user_message_fallback(self) -> None:
        msg = ErrorDetector.get_user_message({})
        assert "error" in msg.lower()


class TestRaiseForAPIError:
    def test_raises_rate_limit_error(self) -> None:
        resp = _mock_response(403, {"X-RateLimit-Remaining": "0"})
        with pytest.raises(RateLimitExceeded):
            ErrorDetector.raise_for_api_error(resp)

    def test_no_raise_on_200(self) -> None:
        ErrorDetector.raise_for_api_error(_mock_response(200))  # should not raise

    def test_raises_github_api_error_on_500(self) -> None:
        with pytest.raises(GitHubAPIError):
            ErrorDetector.raise_for_api_error(_mock_response(500))
