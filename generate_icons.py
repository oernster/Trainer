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

# Fraction of the square canvas the solid artwork should occupy along its
# longest axis. The remainder is a uniform transparent margin. Keeping the
# glyph close to the edge (matching typical Windows app icons) is what stops it
# rendering small on the taskbar next to icons that fill their canvas.
CONTENT_FILL_RATIO = 0.88

# Alpha (0-255) above which a pixel counts as solid artwork when measuring the
# crop box. Faint anti-alias fringes, glows and drop shadows fall below this, so
# a soft halo around the glyph does not defeat the trim.
ALPHA_TRIM_THRESHOLD = 8

ICO_NAME = "trainer.ico"
ICNS_NAME = "trainer.icns"
CANONICAL_PNG_NAME = "trainer_icon.png"

RESAMPLE = Image.Resampling.LANCZOS


def _trim_to_square(img: Image.Image) -> Image.Image:
    """Trim the transparent border and re-pad to a square canvas.

    The opaque content is scaled (via the surrounding margin, not by resampling)
    to fill ``CONTENT_FILL_RATIO`` of the canvas along its longest axis, so the
    visible glyph is as large as the standard icon margin allows.
    """
    alpha = img.split()[-1]
    solid = alpha.point(lambda v: 255 if v > ALPHA_TRIM_THRESHOLD else 0)
    bbox = solid.getbbox()
    if bbox is None:
        return img
    content = img.crop(bbox)
    content_w, content_h = content.size
    side = round(max(content_w, content_h) / CONTENT_FILL_RATIO)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    offset = ((side - content_w) // 2, (side - content_h) // 2)
    canvas.paste(content, offset, content)
    return canvas


def _load_master() -> Image.Image:
    """Load the master PNG as a tightly-framed square RGBA image."""
    if not MASTER_PNG.exists():
        print(f"Error: master icon not found: {MASTER_PNG}")
        print("Place a square (ideally 1024x1024) trainer.png at the repo root.")
        raise SystemExit(1)

    img = Image.open(MASTER_PNG).convert("RGBA")
    return _trim_to_square(img)


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
