from __future__ import annotations

import runpy
import sys


def test_main_version_flag_exits_cleanly_without_qt_imports(monkeypatch, capsys):
    """Regression test: `--version` must not start the UI.

    Build scripts call `flatpak run … --version` as an install smoke-test.
    That must not acquire singleton locks or start Qt, otherwise it can leave a
    stuck background instance that blocks subsequent launches from the desktop.
    """

    # Simulate `python main.py --version`
    monkeypatch.setattr(sys, "argv", ["main.py", "--version"])

    try:
        runpy.run_path("main.py", run_name="__main__")
    except SystemExit as e:
        assert int(getattr(e, "code", 0) or 0) == 0

    out = capsys.readouterr().out.strip()
    assert out.startswith("Trainer"), out

