"""
Error Detection and Classification.

Uses the custom exception hierarchy from :mod:`utils.exceptions` instead of
generic :class:`Exception` raises so that callers can be specific about what
they catch.
"""

from __future__ import annotations

import requests

from utils.exceptions import (
    ConnectionFailedError,
    GitHubAPIError,
    InvalidSearchQuery,
    RateLimitExceeded,
    RepositoryNotFound,
    RequestTimeoutError,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ErrorDetector:
    """Detect and classify errors in the ReAct agent pipeline."""

    @staticmethod
    def classify_api_error(response: requests.Response) -> dict:
        """Classify an HTTP error from a GitHub API response.

        Args:
            response: A :class:`requests.Response` object.

        Returns:
            A dict describing the error with keys ``is_error``, ``category``,
            ``status_code``, ``retry``, ``type``, ``wait_time``, and ``message``.
        """
        status_code = response.status_code

        # 2xx – success
        if 200 <= status_code < 300:
            return {"is_error": False, "status_code": status_code}

        # 4xx – client errors
        if 400 <= status_code < 500:
            error_info: dict = {
                "is_error": True,
                "category": "CLIENT_ERROR",
                "status_code": status_code,
                "retry": False,
            }

            if status_code == 403:
                remaining = response.headers.get("X-RateLimit-Remaining", "1")
                if remaining == "0":
                    error_info.update(
                        {
                            "type": "RATE_LIMIT",
                            "retry": True,
                            "wait_time": 3600,
                            "message": (
                                "GitHub API rate limit exceeded. "
                                "Add a GitHub token or wait 1 hour."
                            ),
                        }
                    )
                else:
                    error_info.update(
                        {
                            "type": "FORBIDDEN",
                            "message": "Access forbidden. Check authentication.",
                        }
                    )

            elif status_code == 400:
                error_info.update(
                    {
                        "type": "BAD_REQUEST",
                        "message": "Invalid request. Please rephrase your search.",
                    }
                )

            elif status_code == 404:
                error_info.update(
                    {
                        "type": "NOT_FOUND",
                        "message": "Resource not found.",
                    }
                )

            elif status_code == 422:
                error_info.update(
                    {
                        "type": "INVALID_QUERY",
                        "message": "Search query is invalid. Try different keywords.",
                    }
                )

            return error_info

        # 5xx – server errors
        if 500 <= status_code < 600:
            return {
                "is_error": True,
                "category": "SERVER_ERROR",
                "status_code": status_code,
                "retry": True,
                "type": "SERVER_ERROR",
                "wait_time": 60,
                "message": f"GitHub server error ({status_code}). Will retry…",
            }

        # Unknown
        return {
            "is_error": True,
            "category": "UNKNOWN",
            "status_code": status_code,
            "retry": False,
            "message": "Unexpected error occurred.",
        }

    @staticmethod
    def raise_for_api_error(response: requests.Response) -> None:
        """Raise a specific exception for a failed API response.

        This is a convenience method that converts the classification dict
        into a typed :class:`utils.exceptions.GitHubAPIError` subclass.

        Args:
            response: A :class:`requests.Response` object.

        Raises:
            RateLimitExceeded: HTTP 403 with rate-limit exhausted.
            RepositoryNotFound: HTTP 404.
            InvalidSearchQuery: HTTP 422.
            GitHubAPIError: Any other non-2xx response.
        """
        info = ErrorDetector.classify_api_error(response)
        if not info["is_error"]:
            return

        error_type = info.get("type", "")
        if error_type == "RATE_LIMIT":
            raise RateLimitExceeded(wait_seconds=info.get("wait_time", 3600))
        if error_type == "NOT_FOUND":
            raise RepositoryNotFound(repo_name="unknown")
        if error_type == "INVALID_QUERY":
            raise InvalidSearchQuery(query="")
        raise GitHubAPIError(
            info.get("message", "API error occurred"),
            status_code=info.get("status_code"),
        )

    @staticmethod
    def classify_network_error(exception: Exception) -> dict:
        """Classify a network-related exception.

        Args:
            exception: The caught exception.

        Returns:
            A dict with ``is_error``, ``category``, ``type``, ``retry``, and
            ``message`` keys.
        """
        if isinstance(exception, requests.exceptions.Timeout):
            return {
                "is_error": True,
                "category": "NETWORK_ERROR",
                "type": "TIMEOUT",
                "retry": True,
                "max_retries": 3,
                "message": "Request timed out. Retrying…",
            }

        if isinstance(exception, requests.exceptions.ConnectionError):
            return {
                "is_error": True,
                "category": "NETWORK_ERROR",
                "type": "CONNECTION_ERROR",
                "retry": True,
                "max_retries": 3,
                "message": "Cannot connect to GitHub. Check your internet connection.",
            }

        if isinstance(exception, requests.exceptions.RequestException):
            return {
                "is_error": True,
                "category": "NETWORK_ERROR",
                "type": "REQUEST_ERROR",
                "retry": True,
                "max_retries": 2,
                "message": f"Network error: {exception}",
            }

        return {
            "is_error": True,
            "category": "UNKNOWN_ERROR",
            "type": "UNKNOWN",
            "retry": False,
            "message": f"Unexpected error: {exception}",
        }

    @staticmethod
    def raise_for_network_error(exception: Exception) -> None:
        """Re-raise ``exception`` as a typed network exception.

        Args:
            exception: The original caught exception.

        Raises:
            RequestTimeoutError: For :class:`requests.exceptions.Timeout`.
            ConnectionFailedError: For :class:`requests.exceptions.ConnectionError`.
        """
        if isinstance(exception, requests.exceptions.Timeout):
            raise RequestTimeoutError("Request timed out.") from exception
        if isinstance(exception, requests.exceptions.ConnectionError):
            raise ConnectionFailedError(
                "Cannot connect to GitHub."
            ) from exception

    @staticmethod
    def should_retry(error_info: dict) -> bool:
        """Check whether the error warrants a retry attempt.

        Args:
            error_info: Error classification dict from :meth:`classify_api_error`
                or :meth:`classify_network_error`.

        Returns:
            ``True`` if the error is retryable.
        """
        return bool(error_info.get("retry", False))

    @staticmethod
    def get_wait_time(error_info: dict) -> int:
        """Return the recommended wait time (seconds) before retrying.

        Args:
            error_info: Error classification dict.

        Returns:
            Number of seconds to wait.
        """
        return int(error_info.get("wait_time", 1))

    @staticmethod
    def get_user_message(error_info: dict) -> str:
        """Return a user-friendly error message.

        Args:
            error_info: Error classification dict.

        Returns:
            A human-readable error string.
        """
        return error_info.get("message", "An error occurred. Please try again.")