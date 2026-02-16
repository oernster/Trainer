"""
Data path resolver for finding data files in both development and packaged environments.
"""
import os
import sys
from pathlib import Path
import logging
from functools import lru_cache


def get_data_directory() -> Path:
    """
    Get the data directory path that works in both development and packaged environments.
    
    Returns:
        Path to the data directory
    """
    # NOTE: this function is called frequently at runtime, so we do cache the
    # resolved path. However, unit tests monkeypatch `sys.executable`,
    # `sys.frozen`, cwd, and even `resolver.__file__`. A simple `@lru_cache` on
    # this function would leak values across tests. To keep both performance and
    # testability, delegate to a cached implementation keyed by the relevant
    # runtime inputs.

    override = os.environ.get("TRAINER_DATA_DIR")
    frozen = bool(getattr(sys, "frozen", False))
    platform = str(getattr(sys, "platform", ""))
    executable = str(getattr(sys, "executable", ""))
    module_file = str(__file__)
    cwd = str(Path.cwd())

    nuitka_containing_dir: str | None = None
    try:
        import __compiled__  # type: ignore

        nuitka_containing_dir = str(getattr(__compiled__, "containing_dir"))
    except Exception:
        nuitka_containing_dir = None

    return _get_data_directory_cached(
        override,
        frozen,
        platform,
        executable,
        module_file,
        cwd,
        nuitka_containing_dir,
    )


@lru_cache(maxsize=64)
def _get_data_directory_cached(
    override: str | None,
    frozen: bool,
    platform: str,
    executable: str,
    module_file: str,
    cwd: str,
    nuitka_containing_dir: str | None,
) -> Path:
    logger = logging.getLogger(__name__)

    # Method 0: Explicit override (useful for debugging broken packaged builds)
    if override:
        override_path = Path(override).expanduser()
        if override_path.exists() and override_path.is_dir():
            logger.info("Using TRAINER_DATA_DIR override: %s", override_path)
            return override_path

    # Method 1: Packaged executable environments
    #
    # We support multiple packagers:
    # - PyInstaller-style (`sys.frozen`)
    # - Nuitka (`__compiled__.containing_dir`)
    #
    # Nuitka does not typically set `sys.frozen`, so we detect it explicitly.

    # Nuitka: `__compiled__.containing_dir` points at the directory that contains
    # the embedded payload. With `--macos-create-app-bundle` this is typically
    # `.../Trainer.app/Contents/MacOS`.
    try:
        if nuitka_containing_dir is None:
            raise RuntimeError("not nuitka")

        containing_dir = Path(nuitka_containing_dir)
        if containing_dir.exists():
            # Prefer src/data if present (matches dev layout).
            nuitka_src_data_dir = containing_dir / "src" / "data"
            if nuitka_src_data_dir.exists():
                logger.info("Resolved data directory via Nuitka containing_dir/src/data: %s", nuitka_src_data_dir)
                return nuitka_src_data_dir

            # Also allow a flattened data dir.
            nuitka_data_dir = containing_dir / "data"
            if nuitka_data_dir.exists():
                logger.info("Resolved data directory via Nuitka containing_dir/data: %s", nuitka_data_dir)
                return nuitka_data_dir
    except Exception:
        # Not Nuitka or not available.
        pass

    # PyInstaller (and some other packagers) set `sys.frozen`.
    if frozen:
        exe_dir = Path(executable).parent
        
        # Handle macOS app bundle structure
        # On macOS, executable is in Contents/MacOS/ but resources are in Contents/Resources/
        if platform == "darwin" and exe_dir.name == "MacOS":
            bundle_contents = exe_dir.parent
            resources_dir = bundle_contents / "Resources"
            if resources_dir.exists():
                # Check for src/data structure in Resources directory
                src_data_dir = resources_dir / "src" / "data"
                if src_data_dir.exists():
                    logger.info("Resolved data directory via frozen macOS Resources/src/data: %s", src_data_dir)
                    return src_data_dir
                    
                # Also check for direct data directory in Resources
                data_dir = resources_dir / "data"
                if data_dir.exists():
                    logger.info("Resolved data directory via frozen macOS Resources/data: %s", data_dir)
                    return data_dir
        
        # Standard packaged executable structure (Windows, Linux)
        data_dir = exe_dir / "data"
        if data_dir.exists():
            logger.info("Resolved data directory via frozen exe_dir/data: %s", data_dir)
            return data_dir
            
        # Also check for src/data structure (for compatibility)
        src_data_dir = exe_dir / "src" / "data"
        if src_data_dir.exists():
            logger.info("Resolved data directory via frozen exe_dir/src/data: %s", src_data_dir)
            return src_data_dir

    # Method 1b: Nuitka app bundle without relying on `__compiled__`.
    #
    # With `--macos-create-app-bundle`, Nuitka places the executable in
    # `.../Contents/MacOS/`. Data files included via `--include-data-dir=src/data=src/data`
    # end up under `Contents/MacOS/src/data`.
    if platform == "darwin":
        try:
            if executable:
                exe_dir = Path(executable).parent
                if exe_dir.name == "MacOS":
                    # Prefer the location we actually ship for Nuitka app bundles.
                    macos_src_data = exe_dir / "src" / "data"
                    if macos_src_data.exists():
                        logger.info("Resolved data directory via macOS app bundle MacOS/src/data: %s", macos_src_data)
                        return macos_src_data
                    macos_data = exe_dir / "data"
                    if macos_data.exists():
                        logger.info("Resolved data directory via macOS app bundle MacOS/data: %s", macos_data)
                        return macos_data

                    # Also check the canonical app-bundle resources location.
                    resources_dir = exe_dir.parent / "Resources"
                    resources_src_data = resources_dir / "src" / "data"
                    if resources_src_data.exists():
                        logger.info(
                            "Resolved data directory via macOS app bundle Resources/src/data: %s",
                            resources_src_data,
                        )
                        return resources_src_data
                    resources_data = resources_dir / "data"
                    if resources_data.exists():
                        logger.info(
                            "Resolved data directory via macOS app bundle Resources/data: %s",
                            resources_data,
                        )
                        return resources_data
        except Exception:
            pass

    # Method 1c: importlib.resources
    #
    # This is robust for packaged builds where `src.data` is embedded as a
    # package and `as_file()` can materialize a filesystem location.
    #
    # IMPORTANT: Do not use this in normal dev/test runs because it bypasses
    # monkeypatched paths in unit tests (the package is importable from the repo).
    if frozen or nuitka_containing_dir or (platform == "darwin" and Path(executable).parent.name == "MacOS"):
        try:
            from importlib.resources import files as resource_files, as_file

            pkg_root = resource_files("src.data")
            marker = pkg_root / "railway_lines_index.json"
            if marker.is_file():
                with as_file(pkg_root) as pkg_path:
                    pkg_path = Path(pkg_path)
                    if pkg_path.exists() and pkg_path.is_dir():
                        logger.info("Resolved data directory via importlib.resources: %s", pkg_path)
                        return pkg_path
        except Exception:
            pass
    
    # Method 2: Development environment - relative to this file
    # This file is in src/utils/, so data is at ../data/
    dev_data_dir = Path(module_file).parent.parent / "data"
    if dev_data_dir.exists():
        logger.info("Resolved data directory via dev path: %s", dev_data_dir)
        return dev_data_dir
    
    # Method 3: Check current working directory
    cwd_data_dir = Path(cwd) / "src" / "data"
    if cwd_data_dir.exists():
        logger.info("Resolved data directory via cwd/src/data: %s", cwd_data_dir)
        return cwd_data_dir
        
    # Method 4: Check one level up from current working directory
    parent_data_dir = Path(cwd).parent / "src" / "data"
    if parent_data_dir.exists():
        logger.info("Resolved data directory via parent cwd/src/data: %s", parent_data_dir)
        return parent_data_dir
    
    # Method 5: Last resort - check common locations
    possible_locations = [
        Path("data"),
        Path("src/data"),
        Path("../data"),
        Path("../src/data"),
    ]
    
    for location in possible_locations:
        if location.exists() and location.is_dir():
            logger.info("Resolved data directory via fallback location: %s", location.resolve())
            return location.resolve()
    
    # If we still can't find it, raise an error
    raise FileNotFoundError(
        "Could not find data directory. Searched in:\n" +
        f"- Executable directory: {Path(executable).parent if frozen else 'N/A'}\n" +
        f"- Development path: {Path(module_file).parent.parent / 'data'}\n" +
        f"- Current directory: {Path(cwd)}\n" +
        "Please ensure the data directory exists in the expected location."
    )


def get_lines_directory() -> Path:
    """Get the lines subdirectory within the data directory."""
    return get_data_directory() / "lines"


def get_data_file_path(filename: str) -> Path:
    """
    Get the full path to a data file.
    
    Args:
        filename: Name of the file (e.g., 'railway_lines_index.json')
        
    Returns:
        Full path to the file
    """
    return get_data_directory() / filename


def get_line_file_path(line_filename: str) -> Path:
    """
    Get the full path to a line data file.
    
    Args:
        line_filename: Name of the line file (e.g., 'central_line.json')
        
    Returns:
        Full path to the line file
    """
    return get_lines_directory() / line_filename
