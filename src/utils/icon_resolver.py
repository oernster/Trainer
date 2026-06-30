"""
Icon asset resolver for finding bundled icon files in both development and
packaged environments.

Modelled on `data_path_resolver`: it locates the shipped `assets/` directory
across development, Nuitka standalone, PyInstaller frozen and Flatpak layouts,
honouring an optional TRAINER_ASSETS_DIR override. This module stays dependency
light (stdlib + pathlib + logging only) and never imports PySide6.
"""
import os
import sys
from pathlib import Path
import logging
from functools import lru_cache

# Named constants for the icon asset set (no magic strings/numbers in logic).
ASSETS_DIR_NAME = "assets"
ICON_ICO_NAME = "trainer.ico"
ICON_PNG_DEFAULT_NAME = "trainer_icon.png"
ICON_PNG_PREFIX = "trainer_icon_"
ICON_PNG_SUFFIX = ".png"

# Sizes for which `trainer_icon_<size>.png` files are generated.
AVAILABLE_PNG_SIZES = (16, 24, 32, 48, 64, 96, 128, 256, 512, 1024)

# Path fragments used when locating the assets directory.
_MACOS_PLATFORM = "darwin"
_MACOS_EXE_PARENT_NAME = "MacOS"
_MACOS_RESOURCES_NAME = "Resources"
_FLATPAK_ASSETS_DIR = "/app/assets"
_SRC_DIR_NAME = "src"


def get_asset_directory() -> Path:
    """
    Get the assets directory path that works in both development and packaged
    environments.

    Returns:
        Path to the assets directory
    """
    # The cached helper is keyed by the relevant runtime inputs so unit tests can
    # monkeypatch `sys.executable`, `sys.frozen`, cwd or this module's `__file__`
    # without values leaking across tests (mirrors data_path_resolver).
    override = os.environ.get("TRAINER_ASSETS_DIR")
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

    return _get_asset_directory_cached(
        override,
        frozen,
        platform,
        executable,
        module_file,
        cwd,
        nuitka_containing_dir,
    )


@lru_cache(maxsize=64)
def _get_asset_directory_cached(
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
            logger.info("Using TRAINER_ASSETS_DIR override: %s", override_path)
            return override_path

    # Method 1: Flatpak. The launcher does `cd /app` and the manifest copies the
    # assets to `/app/assets`.
    flatpak_assets = Path(_FLATPAK_ASSETS_DIR)
    if flatpak_assets.exists() and flatpak_assets.is_dir():
        logger.info("Resolved assets directory via Flatpak path: %s", flatpak_assets)
        return flatpak_assets

    # Method 2: Nuitka standalone. `--include-data-dir` ships `assets` beside the
    # exe; `__compiled__.containing_dir` points at the directory that contains the
    # payload. On a macOS app bundle this is `.../Contents/MacOS`.
    if nuitka_containing_dir is not None:
        try:
            containing_dir = Path(nuitka_containing_dir)
            nuitka_assets = containing_dir / ASSETS_DIR_NAME
            if nuitka_assets.exists() and nuitka_assets.is_dir():
                logger.info(
                    "Resolved assets directory via Nuitka containing_dir/assets: %s",
                    nuitka_assets,
                )
                return nuitka_assets
        except Exception:
            pass

    # Method 3: PyInstaller (and other packagers) set `sys.frozen`.
    if frozen and executable:
        exe_dir = Path(executable).parent

        # macOS app bundle: executable in Contents/MacOS, resources in
        # Contents/Resources.
        if platform == _MACOS_PLATFORM and exe_dir.name == _MACOS_EXE_PARENT_NAME:
            resources_dir = exe_dir.parent / _MACOS_RESOURCES_NAME
            resources_assets = resources_dir / ASSETS_DIR_NAME
            if resources_assets.exists() and resources_assets.is_dir():
                logger.info(
                    "Resolved assets directory via frozen macOS Resources/assets: %s",
                    resources_assets,
                )
                return resources_assets

        # Standard packaged structure (Windows, Linux): assets beside the exe.
        exe_assets = exe_dir / ASSETS_DIR_NAME
        if exe_assets.exists() and exe_assets.is_dir():
            logger.info(
                "Resolved assets directory via frozen exe_dir/assets: %s", exe_assets
            )
            return exe_assets

    # Method 4: Nuitka macOS app bundle without relying on `__compiled__`.
    if platform == _MACOS_PLATFORM and executable:
        exe_dir = Path(executable).parent
        if exe_dir.name == _MACOS_EXE_PARENT_NAME:
            macos_assets = exe_dir / ASSETS_DIR_NAME
            if macos_assets.exists() and macos_assets.is_dir():
                logger.info(
                    "Resolved assets directory via macOS app bundle MacOS/assets: %s",
                    macos_assets,
                )
                return macos_assets

    # Method 5: Development environment. This file is in src/utils/, so the repo
    # root is two levels up and assets live at repo_root/assets.
    dev_assets = Path(module_file).parent.parent.parent / ASSETS_DIR_NAME
    if dev_assets.exists() and dev_assets.is_dir():
        logger.info("Resolved assets directory via dev path: %s", dev_assets)
        return dev_assets

    # Method 6: Current working directory and one level up.
    cwd_assets = Path(cwd) / ASSETS_DIR_NAME
    if cwd_assets.exists() and cwd_assets.is_dir():
        logger.info("Resolved assets directory via cwd/assets: %s", cwd_assets)
        return cwd_assets

    parent_assets = Path(cwd).parent / ASSETS_DIR_NAME
    if parent_assets.exists() and parent_assets.is_dir():
        logger.info("Resolved assets directory via parent cwd/assets: %s", parent_assets)
        return parent_assets

    # Could not resolve. Return the development location so callers see a clear
    # path in any "missing icon" log even though it does not exist.
    fallback = Path(module_file).parent.parent.parent / ASSETS_DIR_NAME
    logger.warning(
        "Could not find assets directory. Falling back to development path: %s",
        fallback,
    )
    return fallback


def _png_name_for_size(size: int) -> str:
    """Build the `trainer_icon_<size>.png` filename for a given size."""
    return f"{ICON_PNG_PREFIX}{size}{ICON_PNG_SUFFIX}"


def get_app_icon_path() -> Path | None:
    """
    Get the best path for the application window icon.

    Prefers `assets/trainer.ico` (multi-size), then `assets/trainer_icon_256.png`,
    then `assets/trainer_icon.png`. Returns None if none are present.
    """
    assets_dir = get_asset_directory()

    ico_path = assets_dir / ICON_ICO_NAME
    if ico_path.is_file():
        return ico_path

    preferred_png = 256
    png_256 = assets_dir / _png_name_for_size(preferred_png)
    if png_256.is_file():
        return png_256

    default_png = assets_dir / ICON_PNG_DEFAULT_NAME
    if default_png.is_file():
        return default_png

    return None


def get_app_icon_png_path(size: int) -> Path | None:
    """
    Get the path to `assets/trainer_icon_<size>.png` for a requested size.

    Falls back to the nearest larger available size, then to
    `assets/trainer_icon.png`. Returns None if no PNG is available.

    Args:
        size: Desired square icon size in pixels.

    Returns:
        Path to a suitable PNG, or None if none exists.
    """
    assets_dir = get_asset_directory()

    exact = assets_dir / _png_name_for_size(size)
    if exact.is_file():
        return exact

    # Prefer the nearest larger generated size so the image is downscaled, not
    # upscaled, by the caller.
    larger_sizes = sorted(s for s in AVAILABLE_PNG_SIZES if s > size)
    for candidate_size in larger_sizes:
        candidate = assets_dir / _png_name_for_size(candidate_size)
        if candidate.is_file():
            return candidate

    default_png = assets_dir / ICON_PNG_DEFAULT_NAME
    if default_png.is_file():
        return default_png

    return None
