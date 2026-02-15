from __future__ import annotations

from typing import Any

import pytest

from src.cache.memory_cache import CacheKey, MemoryCache


def test_memory_cache_get_miss_increments_misses():
    cache = MemoryCache(max_size=10, default_ttl=60)
    assert cache.get("missing") is None
    assert cache.get_stats()["misses"] == 1
    assert cache.get_stats()["hits"] == 0


def test_memory_cache_put_and_get_hit(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("src.cache.memory_cache.time.time", lambda: now)

    cache = MemoryCache(max_size=10, default_ttl=60)
    cache.put("k", "v")
    assert cache.get("k") == "v"
    assert cache.get_stats()["hits"] == 1
    assert cache.get_stats()["misses"] == 0


def test_memory_cache_get_expired_removes_entry_and_counts_miss(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("src.cache.memory_cache.time.time", lambda: now)

    cache = MemoryCache(max_size=10, default_ttl=60)
    cache.put("k", "v", ttl=1)

    now = 1002.0
    assert cache.get("k") is None
    assert cache.get_stats()["misses"] == 1
    assert cache.get_stats()["size"] == 0


def test_memory_cache_eviction_lru(monkeypatch):
    # Control time to avoid expiry.
    monkeypatch.setattr("src.cache.memory_cache.time.time", lambda: 1000.0)

    cache = MemoryCache(max_size=2, default_ttl=60)
    cache.put("a", 1)
    cache.put("b", 2)

    # Touch 'a' so 'b' becomes oldest.
    assert cache.get("a") == 1
    cache.put("c", 3)

    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_memory_cache_set_is_alias_for_put(monkeypatch):
    monkeypatch.setattr("src.cache.memory_cache.time.time", lambda: 1000.0)
    cache = MemoryCache(max_size=10, default_ttl=60)
    cache.set("k", "v")
    assert cache.get("k") == "v"


def test_memory_cache_delete_returns_bool(monkeypatch):
    monkeypatch.setattr("src.cache.memory_cache.time.time", lambda: 1000.0)
    cache = MemoryCache(max_size=10, default_ttl=60)
    cache.put("k", "v")
    assert cache.delete("k") is True
    assert cache.delete("k") is False


def test_memory_cache_clear_resets_state(monkeypatch):
    monkeypatch.setattr("src.cache.memory_cache.time.time", lambda: 1000.0)
    cache = MemoryCache(max_size=10, default_ttl=60)
    cache.put("k", "v")
    _ = cache.get("k")
    cache.clear()
    assert cache.get_stats()["size"] == 0
    assert cache.get_stats()["hits"] == 0
    assert cache.get_stats()["misses"] == 0


def test_memory_cache_cleanup_expired(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("src.cache.memory_cache.time.time", lambda: now)
    cache = MemoryCache(max_size=10, default_ttl=60)
    cache.put("fresh", "v", ttl=10)
    cache.put("stale", "v", ttl=1)

    now = 1002.0
    removed = cache.cleanup_expired()
    assert removed == 1
    assert cache.get("stale") is None
    assert cache.get("fresh") == "v"


def test_memory_cache_get_keys_and_delete_by_prefix(monkeypatch):
    monkeypatch.setattr("src.cache.memory_cache.time.time", lambda: 1000.0)
    cache = MemoryCache(max_size=10, default_ttl=60)
    cache.put("p:1", 1)
    cache.put("p:2", 2)
    cache.put("q:1", 3)

    assert cache.get_keys_by_prefix("p:") == ["p:1", "p:2"]
    deleted = cache.delete_by_prefix("p:")
    assert deleted == 2
    assert cache.get("p:1") is None
    assert cache.get("q:1") == 3


def test_memory_cache_stats_hit_rate_and_utilization(monkeypatch):
    monkeypatch.setattr("src.cache.memory_cache.time.time", lambda: 1000.0)
    cache = MemoryCache(max_size=4, default_ttl=60)

    assert cache.get("missing") is None
    cache.put("k", "v")
    assert cache.get("k") == "v"

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1
    assert stats["utilization"] == 0.25
    assert stats["hit_rate"] == 0.5


@pytest.mark.parametrize(
    ("fn", "args", "expected"),
    [
        (CacheKey.search_key, ("AbC", 10), "search:abc:10"),
        (CacheKey.route_key, ("From", "To", 2), "route:from:to:2"),
        (CacheKey.via_stations_key, ("From", "To"), "via:from:to"),
        (CacheKey.validation_key, ("hash",), "validation:hash"),
    ],
)
def test_cache_key_generators(fn, args: tuple[Any, ...], expected: str):
    assert fn(*args) == expected

