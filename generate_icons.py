#!/usr/bin/env python3
"""Generate the full Trainer icon set from a single master PNG.

Master: trainer.png at the repo root (1024x1024 RGBA recommended).

Produces, into assets/:
- trainer_icon_<size>.png for every size in PNG_SIZES
- trainer_icon.png (the canonical 256px badge, kept for existing references)
- trainer.ico (multi-size Windows icon for the PE resource and shortcuts)
- trainer.icns (macOS icon for the app bundle and DMG volume icon)

Run from the repo root inside the venv:  python generate_icons.py

This is the single source for every platform icon asset. Pillow is the only
dependency.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent
MASTER_PNG = PROJECT_ROOT / "trainer.png"
ASSETS_DIR = PROJECT_ROOT / "assets"

# Square raster sizes shipped as loose PNGs (hicolor, About badge, taskbar).
PNG_SIZES = (16, 24, 32, 48, 64, 96, 128, 256, 512, 1024)

# Sizes embedded in the multi-resolution Windows .ico.
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

# The canonical badge size used by code paths that want one PNG.
CANONICAL_PNG_SIZE = 256

# Fraction of the square tile the badge occupies along its longest axis. The
# whole badge is scaled up to fill this much of the canvas, leaving a small
# uniform transparent border, so the icon reads big on the taskbar.
CONTENT_FILL_RATIO = 0.92

# Alpha (0-255) above which a pixel counts as opaque artwork rather than the
# transparent surround.
OPAQUE_ALPHA = 8

ICO_NAME = "trainer.ico"
ICNS_NAME = "trainer.icns"
CANONICAL_PNG_NAME = "trainer_icon.png"

RESAMPLE = Image.Resampling.LANCZOS


def _frame_badge(img: Image.Image) -> Image.Image:
    """Trim the transparent surround and scale the whole badge to fill the tile.

    The complete badge (its rounded corners and every motif in their original
    arrangement) is kept intact and reframed to fill ``CONTENT_FILL_RATIO`` of a
    square canvas, leaving a small uniform transparent border around it.
    """
    solid = img.split()[-1].point(lambda v: 255 if v > OPAQUE_ALPHA else 0)
    bbox = solid.getbbox()
    if bbox is None:
        return img
    badge = img.crop(bbox)
    badge_w, badge_h = badge.size
    side = round(max(badge_w, badge_h) / CONTENT_FILL_RATIO)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    offset = ((side - badge_w) // 2, (side - badge_h) // 2)
    canvas.alpha_composite(badge, offset)
    return canvas


def _load_master() -> Image.Image:
    """Load the master PNG and frame the whole badge with a small border."""
    if not MASTER_PNG.exists():
        print(f"Error: master icon not found: {MASTER_PNG}")
        print("Place a square (ideally 1024x1024) trainer.png at the repo root.")
        raise SystemExit(1)

    img = Image.open(MASTER_PNG).convert("RGBA")
    return _frame_badge(img)


def _resized(master: Image.Image, size: int) -> Image.Image:
    """Return master resized to a square of the given size."""
    return master.resize((size, size), RESAMPLE)


def generate() -> int:
    """Generate the full icon set from the master PNG."""
    print("Generating Trainer icon set from trainer.png...")
    ASSETS_DIR.mkdir(exist_ok=True)
    master = _load_master()

    for size in PNG_SIZES:
        out = ASSETS_DIR / f"trainer_icon_{size}.png"
        _resized(master, size).save(out, "PNG")
        print(f"  PNG  {size:>4}x{size:<4} -> {out.name}")

    canonical = ASSETS_DIR / CANONICAL_PNG_NAME
    _resized(master, CANONICAL_PNG_SIZE).save(canonical, "PNG")
    print(f"  PNG  canonical    -> {canonical.name} ({CANONICAL_PNG_SIZE}px)")

    ico_out = ASSETS_DIR / ICO_NAME
    _resized(master, max(ICO_SIZES)).save(
        ico_out, format="ICO", sizes=[(s, s) for s in ICO_SIZES]
    )
    print(f"  ICO  {ICO_SIZES} -> {ico_out.name}")

    icns_out = ASSETS_DIR / ICNS_NAME
    # Pillow derives the standard icns members from a large square source.
    _resized(master, 1024).save(icns_out, format="ICNS")
    print(f"  ICNS 1024 source  -> {icns_out.name}")

    print("\nIcon set generated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(generate())
