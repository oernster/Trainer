"""Application layer.

This package is the *composition root* for the program.

All object graph construction must happen in [`src/app/bootstrap.py`](src/app/bootstrap.py:1).
"""

from __future__ import annotations

from .bootstrap import ApplicationContainer, bootstrap_app

__all__ = [
    "ApplicationContainer",
    "bootstrap_app",
]

