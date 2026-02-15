"""Pytest configuration.

These tests import from the application package under `src/`.
When running `pytest` from the repository root, the root directory isn't
necessarily on `sys.path` (depending on how the environment is invoked),
so we ensure imports like `import src...` resolve reliably.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

