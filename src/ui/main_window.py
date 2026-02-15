"""Backward-compatible main window import.

The project historically had a very large `MainWindow` implementation in this
module.

To satisfy the repository's <=400 LOC quality gate and improve separation of
concerns, the active implementation lives in
[`src/ui/main_window_refactored.py`](src/ui/main_window_refactored.py:1).

This file remains as a compatibility shim so existing imports keep working:

```py
from src.ui.main_window import MainWindow
```
"""

from __future__ import annotations

from .main_window_refactored import MainWindow

__all__ = ["MainWindow"]
