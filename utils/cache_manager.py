"""
Intelligent caching system for ReAct agents.

Thread-safe in-process cache with TTL expiry, statistics tracking,
and hash-based key normalisation.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from utils.logger import setup_logger

logger = setup_logger(__name__)


class CacheManager:
    """Multi-level, TTL-based in-process cache for agent optimisation."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        """Initialise the cache.

        Args:
            ttl_seconds: Time-to-live for each entry in seconds (default 1 hour).
        """
        self.ttl = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}
        self._stats: dict[str, int] = {"hits": 0, "misses": 0, "evictions": 0}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _make_key(self, data: str | dict) -> str:
        """Derive a stable MD5 hash from *data*.

        Args:
            data: A string or JSON-serialisable dict to hash.

        Returns:
            Hex digest string.
        """
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str | dict) -> Any | None:
        """Return a cached value, or ``None`` on miss / expiry.

        Args:
            key: Cache key (string or dict – will be hashed).

        Returns:
            The cached value, or ``None``.
        """
        cache_key = self._make_key(key)  # type: ignore[arg-type]

        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() - entry["ts"] < self.ttl:
                self._stats["hits"] += 1
                logger.debug("✅ Cache HIT:  %s…", cache_key[:10])
                return entry["value"]

            # Expired
            del self._cache[cache_key]
            self._stats["evictions"] += 1
            logger.debug("⏰ Cache EXPIRED: %s…", cache_key[:10])

        self._stats["misses"] += 1
        logger.debug("❌ Cache MISS: %s…", cache_key[:10])
        return None

    def set(self, key: str | dict, value: Any) -> None:
        """Store *value* in the cache under *key*.

        Args:
            key:   Cache key (string or dict – will be hashed).
            value: Any picklable value to cache.
        """
        cache_key = self._make_key(key)  # type: ignore[arg-type]
        self._cache[cache_key] = {"value": value, "ts": time.time()}
        logger.debug("💾 Cache SET:  %s…", cache_key[:10])

    def clear(self) -> None:
        """Evict **all** cached entries."""
        self._cache.clear()
        logger.info("🗑️  Cache cleared.")

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries evicted.
        """
        now = time.time()
        expired = [k for k, v in self._cache.items() if now - v["ts"] >= self.ttl]
        for k in expired:
            del self._cache[k]
            self._stats["evictions"] += 1

        if expired:
            logger.info("🗑️  Evicted %d expired cache entries.", len(expired))
        return len(expired)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, int | float]:
        """Return a summary of cache performance.

        Returns:
            Dict with ``hits``, ``misses``, ``evictions``, ``hit_rate``, and
            ``cache_size`` keys.
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate: float = (self._stats["hits"] / total * 100) if total else 0.0
        return {
            **self._stats,
            "hit_rate": round(hit_rate, 2),
            "cache_size": len(self._cache),
        }

    def log_stats(self) -> None:
        """Log cache statistics via the module logger (replaces raw print)."""
        stats = self.get_stats()
        logger.info(
            "💾 Cache stats — size: %d | hits: %d | misses: %d | hit-rate: %.1f%% | evictions: %d",
            stats["cache_size"],
            stats["hits"],
            stats["misses"],
            stats["hit_rate"],
            stats["evictions"],
        )

    # Keep backward-compatible alias
    def print_stats(self) -> None:  # pragma: no cover
        """Alias for :meth:`log_stats` (kept for backward compatibility)."""
        self.log_stats()