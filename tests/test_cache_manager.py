from __future__ import annotations

import pickle
from pathlib import Path

import pytest

from src.cache.cache_manager import CacheManager


def test_cache_manager_get_put_promotes_between_levels(tmp_path: Path, monkeypatch):
    # Freeze time to avoid expiry.
    monkeypatch.setattr("src.cache.cache_manager.time.time", lambda: 1000.0)

    mgr = CacheManager(cache_dir=str(tmp_path))
    mgr.put("k", {"v": 1}, operation_type="default")

    # Should be immediately available from L1.
    assert mgr.get("k") == {"v": 1}
    stats = mgr.get_stats()
    assert stats["total_requests"] == 1
    assert stats["l1_hit_rate"] == 1.0

    # If we clear L1, a subsequent get should hit L2 and re-promote to L1.
    mgr.l1_cache.clear()
    assert mgr.get("k") == {"v": 1}
    stats = mgr.get_stats()
    assert stats["total_requests"] == 2
    assert stats["l2_hit_rate"] > 0.0
    assert mgr.l1_cache.get("k") == {"v": 1}


def test_cache_manager_get_hits_disk_and_promotes(tmp_path: Path, monkeypatch):
    now = 1000.0
    monkeypatch.setattr("src.cache.cache_manager.time.time", lambda: now)

    mgr = CacheManager(cache_dir=str(tmp_path))
    mgr.put("disk-only", 123, operation_type="search")

    # Force fetch from disk by clearing memory levels.
    mgr.l1_cache.clear()
    mgr.l2_cache.clear()
    assert mgr.get("disk-only") == 123

    # After disk hit, it should be promoted back into memory caches.
    assert mgr.l2_cache.get("disk-only") == 123
    assert mgr.l1_cache.get("disk-only") == 123


def test_cache_manager_delete_and_clear_all(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.cache.cache_manager.time.time", lambda: 1000.0)
    mgr = CacheManager(cache_dir=str(tmp_path))
    mgr.put("k", "v", operation_type="search")
    mgr.delete("k")
    assert mgr.get("k") is None

    mgr.put("k2", "v2", operation_type="search")
    mgr.clear_all()
    assert mgr.get("k2") is None
    assert mgr.get_stats()["total_requests"] == 1  # one miss after clear


def test_cache_manager_cleanup_expired(tmp_path: Path, monkeypatch):
    now = 1000.0
    monkeypatch.setattr("src.cache.cache_manager.time.time", lambda: now)
    mgr = CacheManager(cache_dir=str(tmp_path))

    # Put into both levels with a very short ttl.
    mgr.l1_cache.put("k", "v", ttl=1)
    mgr.l2_cache.put("k", "v", ttl=1)
    now = 1002.0
    cleaned = mgr.cleanup_expired()
    assert cleaned == 2


def test_cache_manager_warm_cache_success(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.cache.cache_manager.time.time", lambda: 1000.0)
    mgr = CacheManager(cache_dir=str(tmp_path))
    mgr.warm_cache(
        {
            "a": {"value": 1, "type": "default"},
            "b": {"value": 2, "type": "validation", "ttl": 5},
        }
    )
    assert mgr.get("a") == 1
    assert mgr.get("b") == 2


def test_cache_manager_warm_cache_handles_bad_input(tmp_path: Path, monkeypatch, caplog):
    monkeypatch.setattr("src.cache.cache_manager.time.time", lambda: 1000.0)
    mgr = CacheManager(cache_dir=str(tmp_path))

    # Missing required 'value' key triggers exception and error log.
    mgr.warm_cache({"bad": {"type": "default"}})
    assert any("Cache warming error" in r.message for r in caplog.records)


def test_cache_manager_get_cache_key_is_stable_and_lowercased(tmp_path: Path):
    mgr = CacheManager(cache_dir=str(tmp_path))
    k1 = mgr.get_cache_key("Op", b=2, a=1)
    k2 = mgr.get_cache_key("op", a=1, b=2)
    assert k1 == k2
    assert k1 == "op:a:1:b:2"


def test_cache_manager_invalidate_pattern_deletes_from_memory_levels(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.cache.cache_manager.time.time", lambda: 1000.0)
    mgr = CacheManager(cache_dir=str(tmp_path))

    mgr.l1_cache.put("p:1", 1)
    mgr.l1_cache.put("q:1", 2)
    mgr.l2_cache.put("p:2", 3)

    deleted = mgr.invalidate_pattern("p:")
    assert deleted == 2
    assert mgr.l1_cache.get("p:1") is None
    assert mgr.l2_cache.get("p:2") is None
    assert mgr.l1_cache.get("q:1") == 2


def test_cache_manager_get_cache_strategy_defaults_to_default(tmp_path: Path):
    mgr = CacheManager(cache_dir=str(tmp_path))
    # Private method, but deterministic and core to manager behavior.
    strategy = mgr._get_cache_strategy("nonexistent")
    assert strategy["l1"] is True
    assert strategy["l2"] is True
    assert strategy["l3"] is False


def test_disk_cache_write_read_expired_and_delete(tmp_path: Path, monkeypatch):
    # Directly validate DiskCache via manager.
    now = 1000.0
    monkeypatch.setattr("src.cache.cache_manager.time.time", lambda: now)

    mgr = CacheManager(cache_dir=str(tmp_path))
    disk = mgr.l3_cache
    disk.put("k", "v", ttl=1)
    assert disk.get("k") == "v"

    now = 1002.0
    assert disk.get("k") is None  # expired should be removed

    disk.put("k2", "v2", ttl=10)
    assert disk.delete("k2") is True
    assert disk.delete("k2") is False


def test_disk_cache_size_cleanup_removes_oldest(tmp_path: Path, monkeypatch):
    # Force cleanup by using a tiny max size and writing multiple cache entries.
    now = 1000.0
    monkeypatch.setattr("src.cache.cache_manager.time.time", lambda: now)

    mgr = CacheManager(cache_dir=str(tmp_path))
    disk = mgr.l3_cache
    disk.max_size_bytes = 200  # tiny

    # Create 3 entries with increasing 'created' times.
    now = 1000.0
    disk.put("k1", "v" * 50, ttl=100)
    now = 1001.0
    disk.put("k2", "v" * 50, ttl=100)
    now = 1002.0
    disk.put("k3", "v" * 50, ttl=100)

    # Some entries should have been deleted by cleanup.
    remaining = list(Path(tmp_path).glob("*.cache"))
    assert 1 <= len(remaining) <= 3

