"""
Pytest suite for CacheManager.

Replaces the old test_cache.py script (which used print-based assertions)
with proper pytest assertions and fixtures.
"""

from __future__ import annotations

import time

import pytest

from utils.cache_manager import CacheManager


@pytest.fixture()
def cache() -> CacheManager:
    """Return a short-TTL CacheManager for each test."""
    return CacheManager(ttl_seconds=2)


class TestCacheBasicOperations:
    def test_set_and_get(self, cache: CacheManager) -> None:
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss_returns_none(self, cache: CacheManager) -> None:
        assert cache.get("nonexistent_key") is None

    def test_overwrite_value(self, cache: CacheManager) -> None:
        cache.set("k", "v1")
        cache.set("k", "v2")
        assert cache.get("k") == "v2"

    def test_complex_data_cached(self, cache: CacheManager) -> None:
        data = {"repos": ["langchain", "autogpt"], "count": 2}
        cache.set("search:ai", data)
        assert cache.get("search:ai") == data

    def test_dict_key_normalised(self, cache: CacheManager) -> None:
        cache.set({"q": "ai", "n": 10}, "result")
        assert cache.get({"q": "ai", "n": 10}) == "result"


class TestCacheExpiry:
    def test_entry_expires(self, cache: CacheManager) -> None:
        cache.set("temp", "value")
        assert cache.get("temp") == "value"
        time.sleep(2.1)
        assert cache.get("temp") is None

    def test_cleanup_expired_removes_entries(self, cache: CacheManager) -> None:
        cache.set("a", 1)
        cache.set("b", 2)
        time.sleep(2.1)
        evicted = cache.cleanup_expired()
        assert evicted == 2
        assert len(cache._cache) == 0


class TestCacheStatistics:
    def test_hit_rate_calculation(self, cache: CacheManager) -> None:
        cache.set("x", 42)
        for _ in range(4):
            cache.get("x")   # 4 hits
        cache.get("missing")  # 1 miss

        stats = cache.get_stats()
        assert stats["hits"] == 4
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 80.0

    def test_eviction_counted(self, cache: CacheManager) -> None:
        cache.set("ev", "val")
        time.sleep(2.1)
        cache.get("ev")  # trigger expiry on get
        assert cache.get_stats()["evictions"] >= 1

    def test_clear_empties_cache(self, cache: CacheManager) -> None:
        cache.set("k1", 1)
        cache.set("k2", 2)
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get_stats()["cache_size"] == 0
