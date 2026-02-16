#!/usr/bin/env python3
"""Nuitka-based macOS DMG builder for Trainer (Apple Silicon only).

Why this exists
---------------
The legacy DMG builder [`builddmg.py`](builddmg.py:1) constructs an app bundle
that executes the *system* Python at runtime, while also bundling a
`site-packages/` built for a different interpreter version. That can break
compiled wheels (e.g. `pydantic_core`) at runtime.

This script builds a self-contained macOS `.app` bundle using Nuitka, then
creates a drag-to-install DMG.

Outputs
-------
- `trainer-macos-arm64.dmg`

Prereqs
-------
- macOS on Apple Silicon (arm64)
- Python environment with dependencies installed (see requirements.txt)
- Nuitka installed (see requirements.txt)
- Optional: `create-dmg` installed for a styled DMG (falls back to `hdiutil`)
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Iterable, Optional


@dataclass(frozen=True)
class BuildConfig:
    app_name: str = "Trainer"
    # Use an unambiguous filename so users don't accidentally install an older
    # DMG with the same name from Downloads.
    dmg_filename: str = "trainer-macos-arm64.dmg"
    volume_name: str = "Install Trainer"
    entrypoint: Path = Path("main.py")
    icon_path: Path = Path("assets/trainer_icon.png")
    include_data_dir_src_data: str = "src/data=src/data"
    include_data_dir_assets: str = "assets=assets"
    output_dir: Path = Path("dist_macos_arm64")
    staging_dir: Path = Path("staging_macos_arm64")
    background_path: Path = Path("dmg_background.png")
    # Where we place a generated .icns for the app + DMG volume icon.
    generated_icns_path: Path = Path("dist_macos_arm64/Trainer.icns")


def _is_macos_arm64() -> bool:
    return sys.platform == "darwin" and platform.machine() == "arm64"


def _run(cmd: list[str], *, cwd: Optional[Path] = None) -> None:
    print("Executing:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


def _rm_rf(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _find_first_app_bundle(search_dir: Path) -> Path:
    apps = sorted(search_dir.glob("*.app"))
    if not apps:
        # Nuitka sometimes nests bundles; do a deeper search.
        apps = sorted(search_dir.rglob("*.app"))
    if not apps:
        raise FileNotFoundError(f"No .app bundle found under {search_dir}")
    return apps[0]


def _ensure_icns_from_png(*, png_path: Path, icns_path: Path) -> Path:
    """Generate a macOS .icns from a PNG (requires `sips` + `iconutil`).

    Nuitka + create-dmg work best with .icns.
    """

    if icns_path.exists():
        return icns_path

    if not png_path.exists():
        raise FileNotFoundError(f"Icon PNG not found: {png_path}")

    iconset_dir = icns_path.with_suffix(".iconset")
    _rm_rf(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    # Standard icon sizes.
    sizes = [16, 32, 128, 256, 512]
    for s in sizes:
        out1 = iconset_dir / f"icon_{s}x{s}.png"
        out2 = iconset_dir / f"icon_{s}x{s}@2x.png"
        _run(["sips", "-z", str(s), str(s), str(png_path), "--out", str(out1)])
        _run(["sips", "-z", str(s * 2), str(s * 2), str(png_path), "--out", str(out2)])

    # `iconutil` expects the directory to end with `.iconset`.
    _run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)])
    _rm_rf(iconset_dir)
    return icns_path


def _set_custom_file_icon(*, target_path: Path, icon_icns: Path) -> None:
    """Best-effort: set Finder icon for a file (e.g. the .dmg itself).

    `create-dmg --volicon` sets the *mounted volume* icon, not the .dmg file icon.
    Users expect the downloaded DMG file to have an icon too.

    This uses AppleScript (Finder) and does not require extra dependencies.
    """

    if not target_path.exists() or not icon_icns.exists():
        return

    # Strategy order:
    # 1) `fileicon` if present.
    # 2) Xcode/CLT tools (Rez/DeRez/SetFile) via `xcrun`.
    # 3) Finder AppleScript (may require Automation permission prompt).

    fileicon_bin = shutil.which("fileicon")
    if fileicon_bin:
        try:
            _run([fileicon_bin, "set", str(target_path), str(icon_icns)])
            return
        except Exception as exc:
            print(f"Warning: fileicon failed to set DMG icon: {exc}")

    # Try Rez/DeRez/SetFile via `xcrun`.
    try:
        rez = subprocess.check_output(["xcrun", "--find", "Rez"], stderr=subprocess.DEVNULL)
        derez = subprocess.check_output(["xcrun", "--find", "DeRez"], stderr=subprocess.DEVNULL)
        setfile = subprocess.check_output(["xcrun", "--find", "SetFile"], stderr=subprocess.DEVNULL)
        rez_path = rez.decode("utf-8").strip()
        derez_path = derez.decode("utf-8").strip()
        setfile_path = setfile.decode("utf-8").strip()

        if rez_path and derez_path and setfile_path:
            with tempfile.TemporaryDirectory() as td:
                rsrc_path = Path(td) / "icon.rsrc"

                # Extract icon resources from the .icns.
                _run([derez_path, "-only", "icns", str(icon_icns)], cwd=Path(td))
                # DeRez outputs to stdout by default; capture and write to file.
                rsrc_bytes = subprocess.check_output(
                    [derez_path, "-only", "icns", str(icon_icns)],
                    stderr=subprocess.STDOUT,
                )
                rsrc_path.write_bytes(rsrc_bytes)

                # Append resource fork and mark file as having a custom icon.
                _run([rez_path, "-append", str(rsrc_path), "-o", str(target_path)])
                _run([setfile_path, "-a", "C", str(target_path)])
                return
    except Exception as exc:
        # CLT not installed or tools missing.
        print(f"Warning: Rez/SetFile icon set path unavailable: {exc}")

    # Fallback: AppleScript Finder.
    script = f'''
        try
            set dmgFile to POSIX file "{target_path}" as alias
            set iconFile to POSIX file "{icon_icns}" as alias
            tell application "Finder"
                set icon of dmgFile to icon of iconFile
                update dmgFile
            end tell
        on error errMsg number errNum
            return "ERROR: " & errNum & ": " & errMsg
        end try
        return "OK"
    '''

    try:
        out = subprocess.check_output(["osascript", "-e", script], stderr=subprocess.STDOUT)
        result = out.decode("utf-8", errors="replace").strip()
        if result and result != "OK":
            print(f"Warning: failed to set DMG file icon via Finder: {result}")
    except Exception as exc:
        print(f"Warning: failed to set DMG file icon via Finder: {exc}")


def _git_short_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        )
        return out.decode("utf-8").strip() or "unknown"
    except Exception:
        return "unknown"


def _write_nuitka_build_marker(app_bundle: Path) -> None:
    """Write a marker file so installed builds can be distinguished from legacy DMG builds."""

    marker = app_bundle / "Contents" / "MacOS" / "NUITKA_BUILD.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    marker.write_text(
        "\n".join(
            [
                "Trainer Nuitka build marker",
                f"built_utc={stamp}",
                f"git_sha={_git_short_sha()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _print_app_bundle_signature(app_bundle: Path) -> None:
    """Print a short signature so users can verify they installed the correct bundle."""

    macos_dir = app_bundle / "Contents" / "MacOS"
    print("=== App bundle signature (for verification) ===")
    print(f"App: {app_bundle}")
    print(f"MacOS dir: {macos_dir}")
    if macos_dir.exists():
        try:
            for p in sorted(macos_dir.iterdir()):
                if p.is_dir():
                    continue
                # Keep output compact.
                print(f"- {p.name} ({p.stat().st_size} bytes)")
        except Exception:
            pass
    print("=============================================")


def _verify_app_bundle_data(cfg: BuildConfig, app_bundle: Path) -> None:
    """Fail-fast verification that routing/station JSON data is actually present.

    This is primarily to catch packaging regressions where the app launches but
    silently has no offline data (empty station dropdowns, no routes).
    """

    # Common locations depending on packager behavior / app bundle conventions.
    candidates = [
        app_bundle / "Contents" / "MacOS" / "src" / "data",
        app_bundle / "Contents" / "Resources" / "src" / "data",
        app_bundle / "Contents" / "MacOS" / "data",
        app_bundle / "Contents" / "Resources" / "data",
    ]

    marker_name = "railway_lines_index.json"
    ok_dir: Optional[Path] = None
    for d in candidates:
        if (d / marker_name).exists():
            ok_dir = d
            break

    if not ok_dir:
        msg = (
            "Offline data not found in built app bundle. Expected one of: \n"
            + "\n".join(f"- {p}" for p in candidates)
            + f"\nMissing marker: {marker_name}"
        )
        raise RuntimeError(msg)

    lines_dir = ok_dir / "lines"
    line_files = sorted(lines_dir.glob("*.json")) if lines_dir.exists() else []
    # Exclude backups to avoid inflating counts.
    line_files = [p for p in line_files if not p.name.endswith(".backup")]

    print(f"Verified offline data directory: {ok_dir}")
    print(f"Verified marker exists: {ok_dir / marker_name}")
    print(f"Verified lines directory exists: {lines_dir.exists()}")
    print(f"Verified line JSON file count: {len(line_files)}")

    # Sanity: there should be at least a handful of line files.
    if len(line_files) < 10:
        raise RuntimeError(
            "Offline data appears incomplete in app bundle: "
            f"found only {len(line_files)} line JSON files under {lines_dir}"
        )


def _ensure_background_image(path: Path) -> None:
    """Create a simple DMG background image if Pillow is available.

    If Pillow isn't installed, we just skip styling. `create-dmg` works without
    a background.
    """

    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except Exception:
        print("Pillow not available; skipping DMG background image generation")
        return

    width, height = 640, 400
    img = Image.new("RGB", (width, height), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)

    # Light gradient.
    for y in range(height):
        v = int(245 - (y / height) * 15)
        draw.line([(0, y), (width, y)], fill=(v, v, v))

    title = "Install Trainer"
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 28)
    except Exception:
        title_font = ImageFont.load_default()

    title_w = draw.textlength(title, font=title_font)
    draw.text(((width - title_w) / 2, 40), title, fill=(40, 40, 40), font=title_font)

    subtitle = "Drag Trainer to Applications"
    try:
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/SFNSText.ttf", 16)
    except Exception:
        subtitle_font = ImageFont.load_default()

    sub_w = draw.textlength(subtitle, font=subtitle_font)
    draw.text(
        ((width - sub_w) / 2, 78),
        subtitle,
        fill=(80, 80, 80),
        font=subtitle_font,
    )

    img.save(path)
    print(f"Created DMG background image: {path}")


def _create_applications_symlink(staging_dir: Path) -> None:
    link = staging_dir / "Applications"
    if link.exists():
        return
    os.symlink("/Applications", link)


def _ensure_nuitka_available() -> None:
    # Prefer running via current interpreter to avoid PATH issues.
    _run([sys.executable, "-m", "nuitka", "--version"])


def _warn_if_running_in_venv() -> None:
    """Best-effort warning.

    If the user runs this from a venv, that's normally fine, but it can be a
    surprise if they expected system python. This also helps with debugging.
    """

    try:
        if sys.prefix != sys.base_prefix:
            print(f"Note: running inside virtualenv: {sys.prefix}")
    except Exception:
        pass


def _nuitka_cmd(cfg: BuildConfig, *, icon_path: Path) -> list[str]:
    if not cfg.entrypoint.exists():
        raise FileNotFoundError(f"Entrypoint not found: {cfg.entrypoint}")
    if not icon_path.exists():
        raise FileNotFoundError(f"Icon not found: {icon_path} (expected for --macos-app-icon)")

    # NOTE:
    # - We build an app bundle, not onefile.
    # - We rely on Nuitka to include extension modules correctly for the build
    #   interpreter, avoiding the system-python mismatch seen in builddmg.py.
    # - We force the *binary name* to `Trainer` so `Contents/MacOS/Trainer` is a
    #   Mach-O executable (and never the legacy bash launcher). This also makes
    #   post-install verification unambiguous.
    return [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--macos-create-app-bundle",
        "--output-filename=Trainer",
        "--enable-plugin=pyside6",
        "--follow-imports",
        "--assume-yes-for-downloads",
        f"--macos-app-name={cfg.app_name}",
        f"--macos-app-icon={icon_path}",
        "--include-package=src",
        f"--include-data-dir={cfg.include_data_dir_src_data}",
        f"--include-data-dir={cfg.include_data_dir_assets}",
        f"--output-dir={cfg.output_dir}",
        str(cfg.entrypoint),
    ]


def build_app_bundle(cfg: BuildConfig) -> Path:
    print("=== Building macOS .app bundle with Nuitka (arm64) ===")

    _ensure_nuitka_available()

    # Clean output/staging.
    _rm_rf(cfg.output_dir)
    _rm_rf(cfg.staging_dir)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    cfg.staging_dir.mkdir(parents=True, exist_ok=True)

    # Generate .icns once per build for both the app icon + DMG volume icon.
    icns_path = _ensure_icns_from_png(
        png_path=cfg.icon_path,
        icns_path=cfg.generated_icns_path,
    )

    # Build.
    _run(_nuitka_cmd(cfg, icon_path=icns_path))

    # Find/normalize app bundle name.
    built_app = _find_first_app_bundle(cfg.output_dir)
    target_app = cfg.output_dir / f"{cfg.app_name}.app"
    if built_app.resolve() != target_app.resolve():
        if target_app.exists():
            _rm_rf(target_app)
        shutil.move(str(built_app), str(target_app))
    print(f"Built app bundle: {target_app}")

    # Fail fast if data wasn't actually packaged.
    _verify_app_bundle_data(cfg, target_app)

    # Write a marker file to distinguish this from legacy DMG builds.
    _write_nuitka_build_marker(target_app)
    _print_app_bundle_signature(target_app)
    return target_app


def create_dmg(cfg: BuildConfig, app_bundle: Path) -> Path:
    print("=== Creating DMG ===")
    dmg_path = Path(cfg.dmg_filename).resolve()
    if dmg_path.exists():
        dmg_path.unlink()

    # Stage (ensure no leftovers from previous runs).
    _rm_rf(cfg.staging_dir)
    cfg.staging_dir.mkdir(parents=True, exist_ok=True)

    staged_app = cfg.staging_dir / app_bundle.name
    if staged_app.exists():
        _rm_rf(staged_app)
    shutil.copytree(app_bundle, staged_app)

    # Optional background.
    _rm_rf(cfg.background_path)
    _ensure_background_image(cfg.background_path)

    create_dmg_bin = shutil.which("create-dmg")
    if create_dmg_bin:
        # IMPORTANT:
        # `create-dmg` creates the /Applications link inside the image itself.
        # If we also put an Applications symlink into the staging directory we end
        # up with an "Applications/Applications" conflict and the build fails.
        cmd = [
            create_dmg_bin,
            "--volname",
            cfg.volume_name,
            "--window-pos",
            "200",
            "120",
            "--window-size",
            "640",
            "400",
            "--icon-size",
            "100",
            "--text-size",
            "14",
            "--app-drop-link",
            "520",
            "180",
            "--icon",
            app_bundle.name,
            "120",
            "180",
        ]

        # Set the DMG volume icon (Finder icon for the mounted disk image).
        try:
            volicon = cfg.generated_icns_path
            if volicon.exists():
                cmd.extend(["--volicon", str(volicon.resolve())])
        except Exception:
            pass

        if cfg.background_path.exists():
            cmd.extend(["--background", str(cfg.background_path.resolve())])

        # Important: source folder must be the *staging directory* so the DMG contains
        # both the .app and the /Applications symlink.
        cmd.extend([str(dmg_path), str(cfg.staging_dir.resolve())])
        _run(cmd)

        # create-dmg may leave a `rw.*.<name>.dmg` intermediate. If the expected
        # output is missing but an intermediate exists, rename it.
        if not dmg_path.exists():
            candidates = sorted(
                Path.cwd().glob(f"rw.*.{dmg_path.name}"),
                key=lambda p: p.stat().st_mtime,
            )
            if candidates:
                candidates[-1].rename(dmg_path)

        # Best-effort: set the DMG *file* icon (not just the mounted volume icon).
        try:
            volicon = cfg.generated_icns_path
            if volicon.exists() and dmg_path.exists():
                _set_custom_file_icon(target_path=dmg_path, icon_icns=volicon)
        except Exception:
            pass

        print(f"Created DMG with create-dmg: {dmg_path}")
        return dmg_path

    # Fallback: hdiutil (unstyled).
    print("create-dmg not found; falling back to hdiutil")

    # For plain `hdiutil` we must provide the /Applications link ourselves.
    _create_applications_symlink(cfg.staging_dir)

    _run(
        [
            "hdiutil",
            "create",
            "-fs",
            "HFS+",
            "-volname",
            cfg.volume_name,
            "-srcfolder",
            str(cfg.staging_dir.resolve()),
            "-format",
            "UDZO",
            "-imagekey",
            "zlib-level=9",
            str(dmg_path),
        ]
    )

    # Best-effort: set the DMG file icon.
    try:
        volicon = cfg.generated_icns_path
        if volicon.exists() and dmg_path.exists():
            _set_custom_file_icon(target_path=dmg_path, icon_icns=volicon)
    except Exception:
        pass

    print(f"Created DMG with hdiutil: {dmg_path}")
    return dmg_path


def main(argv: Optional[Iterable[str]] = None) -> int:
    _ = argv  # reserved for future CLI flags.

    if not _is_macos_arm64():
        print(
            "ERROR: This script is intended to run on macOS Apple Silicon (arm64).\n"
            f"Detected: platform={sys.platform}, machine={platform.machine()}"
        )
        return 1

    _warn_if_running_in_venv()

    cfg = BuildConfig()

    try:
        app_bundle = build_app_bundle(cfg)
        dmg = create_dmg(cfg, app_bundle)
        print("=== Done ===")
        print(f"Output DMG: {dmg}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return int(getattr(e, "returncode", 1) or 1)
    except Exception as e:
        print(f"Build failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
