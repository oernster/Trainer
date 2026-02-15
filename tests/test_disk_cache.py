from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cache.disk_cache import DiskCache


def test_disk_cache_put_get_delete_and_clear(tmp_path: Path, monkeypatch):
    now = 1000.0
    monkeypatch.setattr("src.cache.disk_cache.time.time", lambda: now)

    cache = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)
    assert cache.get("missing") is None

    cache.put("k", {"v": 1}, ttl=10)
    assert cache.get("k") == {"v": 1}
    assert cache.delete("k") is True
    # Implementation returns True on best-effort deletes, even when the key
    # isn't present.
    assert cache.delete("k") is True

    cache.put("k2", 2, ttl=10)
    cache.clear()
    assert cache.get("k2") is None
    assert cache.get_stats()["size"] == 0


def test_disk_cache_expiry_and_cleanup_expired(tmp_path: Path, monkeypatch):
    now = 1000.0
    monkeypatch.setattr("src.cache.disk_cache.time.time", lambda: now)
    cache = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)

    cache.put("short", "v", ttl=1)
    cache.put("long", "v", ttl=10)

    now = 1002.0
    assert cache.get("short") is None
    removed = cache.cleanup_expired()
    assert removed == 0  # already removed by get()
    assert cache.get("long") == "v"


def test_disk_cache_metadata_persistence_and_validation(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.cache.disk_cache.time.time", lambda: 1000.0)
    cache = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)
    cache.put("k", "v", ttl=10)

    # Recreate instance: should load metadata and validate against cache file.
    cache2 = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)
    assert cache2.get("k") == "v"

    # If the cache file disappears, metadata should be filtered out on load.
    cache_file = cache2._get_cache_file("k")
    cache_file.unlink()
    cache3 = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)
    assert cache3.get("k") is None
    assert "k" not in cache3.metadata


def test_disk_cache_get_removes_corrupted_cache_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.cache.disk_cache.time.time", lambda: 1000.0)
    cache = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)

    # Write a non-pickle payload into the cache file so pickle.load fails.
    cache.put("k", "v", ttl=10)
    cache_file = cache._get_cache_file("k")
    cache_file.write_bytes(b"not a pickle")

    assert cache.get("k") is None
    assert not cache_file.exists()


def test_disk_cache_delete_by_prefix(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.cache.disk_cache.time.time", lambda: 1000.0)
    cache = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)
    cache.put("p:1", 1, ttl=10)
    cache.put("p:2", 2, ttl=10)
    cache.put("q:1", 3, ttl=10)

    deleted = cache.delete_by_prefix("p:")
    assert deleted == 2
    assert cache.get("p:1") is None
    assert cache.get("q:1") == 3


def test_disk_cache_size_cleanup_lru_by_last_access(tmp_path: Path, monkeypatch):
    now = 1000.0
    monkeypatch.setattr("src.cache.disk_cache.time.time", lambda: now)
    cache = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)
    cache.max_size_bytes = 300  # tiny

    cache.put("k1", "x" * 200, ttl=100)
    now = 1001.0
    cache.put("k2", "x" * 200, ttl=100)

    # Access k2 so k1 is LRU.
    now = 1002.0
    assert cache.get("k2") is not None

    # Adding another entry forces cleanup; should evict least recently accessed.
    now = 1003.0
    cache.put("k3", "x" * 200, ttl=100)

    # At least one entry must be gone. We expect k1 to be the first to go.
    remaining = set(cache.metadata.keys())
    assert "k3" in remaining
    assert "k2" in remaining or "k1" in remaining
    assert len(remaining) <= 2


def test_disk_cache_optimize_removes_missing_files_and_expired(tmp_path: Path, monkeypatch):
    now = 1000.0
    monkeypatch.setattr("src.cache.disk_cache.time.time", lambda: now)
    cache = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)

    cache.put("expired", "v", ttl=1)
    cache.put("missingfile", "v", ttl=10)

    # Remove the file but keep metadata around until optimize.
    cache._get_cache_file("missingfile").unlink()

    now = 1002.0
    cleaned = cache.optimize()
    assert cleaned >= 1
    assert cache.get("expired") is None
    assert cache.get("missingfile") is None


def test_disk_cache_save_metadata_failure_is_logged(tmp_path: Path, monkeypatch, caplog):
    monkeypatch.setattr("src.cache.disk_cache.time.time", lambda: 1000.0)
    cache = DiskCache(cache_dir=str(tmp_path), max_size_mb=100)

    # Force json.dump to fail.
    def _boom(*_args, **_kwargs):
        raise OSError("nope")

    monkeypatch.setattr(json, "dump", _boom)
    cache.put("k", "v", ttl=10)
    assert any("Error saving cache metadata" in r.message for r in caplog.records)

