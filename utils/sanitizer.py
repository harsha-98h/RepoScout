"""
Input sanitization utilities for RepoScout.

Guards against prompt-injection attempts before user text reaches the
LLM.  Any input that matches a suspicious pattern is either stripped or
rejected outright.
"""

from __future__ import annotations

import re

from utils.exceptions import PromptInjectionDetected
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Patterns that are characteristic of prompt-injection payloads
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard.{0,30}instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"<\|.*?\|>"),          # control token patterns
    re.compile(r"###\s*instruction", re.IGNORECASE),
]

# Maximum allowed length for a single user query
_MAX_QUERY_LENGTH: int = 500


def sanitize_query(query: str) -> str:
    """Validate and sanitize a user search query.

    Args:
        query: Raw text entered by the user.

    Returns:
        Sanitized, stripped query string.

    Raises:
        PromptInjectionDetected: If the input contains injection patterns.
        ValueError: If the input is empty or exceeds ``_MAX_QUERY_LENGTH``.
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    query = query.strip()

    if len(query) > _MAX_QUERY_LENGTH:
        raise ValueError(
            f"Query too long ({len(query)} chars). Maximum is {_MAX_QUERY_LENGTH}."
        )

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(query):
            logger.warning("⚠️  Potential prompt injection detected in query.")
            raise PromptInjectionDetected(
                "Query contains disallowed content. Please rephrase your search."
            )

    return query
