from __future__ import annotations

import sys
from pathlib import Path

import pytest

import src.utils.data_path_resolver as resolver


def test_get_data_directory_packaged_exe_prefers_exe_data_dir(tmp_path: Path, monkeypatch):
    exe_path = tmp_path / "app.exe"
    (tmp_path / "data").mkdir(parents=True)

    monkeypatch.setattr(sys, "executable", str(exe_path))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32", raising=False)

    assert resolver.get_data_directory() == tmp_path / "data"


def test_get_data_directory_packaged_macos_bundle_uses_resources_src_data(tmp_path: Path, monkeypatch):
    # Simulate: <App>.app/Contents/MacOS/app_exe
    contents = tmp_path / "MyApp.app" / "Contents"
    exe_dir = contents / "MacOS"
    resources = contents / "Resources"
    exe_dir.mkdir(parents=True)
    (resources / "src" / "data").mkdir(parents=True)
    exe_path = exe_dir / "myapp"

    monkeypatch.setattr(sys, "executable", str(exe_path))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin", raising=False)

    assert resolver.get_data_directory() == resources / "src" / "data"


def test_get_data_directory_development_mode_uses_module_relative_src_data(tmp_path: Path, monkeypatch):
    # get_data_directory computes dev_data_dir as Path(__file__).parent.parent / "data"
    # so set resolver.__file__ to a temp src/utils/module.py equivalent.
    fake_utils_dir = tmp_path / "src" / "utils"
    fake_utils_dir.mkdir(parents=True)
    (tmp_path / "src" / "data").mkdir(parents=True)

    monkeypatch.setattr(resolver, "__file__", str(fake_utils_dir / "data_path_resolver.py"))
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    assert resolver.get_data_directory() == tmp_path / "src" / "data"


def test_get_data_directory_uses_cwd_src_data_when_present(tmp_path: Path, monkeypatch):
    # Ensure we *don't* hit Method 2 (module-relative dev path) so we can verify
    # the Method 3 cwd lookup.
    fake_utils_dir = tmp_path / "somewhere" / "utils"
    fake_utils_dir.mkdir(parents=True)
    monkeypatch.setattr(resolver, "__file__", str(fake_utils_dir / "data_path_resolver.py"))

    (tmp_path / "src" / "data").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    assert resolver.get_data_directory() == tmp_path / "src" / "data"


def test_get_data_directory_raises_when_no_locations_exist(tmp_path: Path, monkeypatch):
    # Run from an empty directory so Path("data") / Path("src/data") etc don't
    # accidentally resolve to the repository's real paths.
    monkeypatch.chdir(tmp_path)

    # Also ensure Method 2 (module-relative dev path) doesn't exist.
    fake_utils_dir = tmp_path / "somewhere" / "utils"
    fake_utils_dir.mkdir(parents=True)
    monkeypatch.setattr(resolver, "__file__", str(fake_utils_dir / "data_path_resolver.py"))

    monkeypatch.setattr(sys, "frozen", False, raising=False)

    with pytest.raises(FileNotFoundError):
        resolver.get_data_directory()

