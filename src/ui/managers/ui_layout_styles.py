"""Styling helpers for [`UILayoutManager`](src/ui/managers/ui_layout_manager.py:21)."""

from __future__ import annotations


def header_button_stylesheet(theme: str) -> str:
    """Return stylesheet for header buttons based on theme."""

    if theme == "dark":
        return """
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #404040;
                border-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1976d2;
            }
        """

    return """
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #cccccc;
            border-radius: 4px;
            color: #000000;
            padding: 4px;
            font-size: 24px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
            border-color: #1976d2;
        }
        QPushButton:pressed {
            background-color: #1976d2;
            color: #ffffff;
        }
    """


def menu_bar_stylesheet(theme: str) -> str:
    """Return menu bar stylesheet based on theme."""

    if theme == "dark":
        return """
            QMenuBar {
                background-color: #2d2d2d;
                color: #ffffff;
                border: none;
                border-bottom: none;
                padding: 2px;
                margin: 0px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
                margin: 0px;
                border: none;
            }
            QMenuBar::item:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
            QMenuBar::item:pressed {
                background-color: #0d47a1;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
            }
            QMenu::item {
                padding: 4px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #404040;
                margin: 2px 0px;
            }
        """

    return """
        QMenuBar {
            background-color: #f0f0f0;
            color: #000000;
            border: none;
            border-bottom: none;
            padding: 2px;
            margin: 0px;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
            margin: 0px;
            border: none;
        }
        QMenuBar::item:selected {
            background-color: #1976d2;
            color: #ffffff;
        }
        QMenuBar::item:pressed {
            background-color: #0d47a1;
        }
        QMenu {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
        }
        QMenu::item {
            padding: 4px 20px;
            background-color: transparent;
        }
        QMenu::item:selected {
            background-color: #1976d2;
            color: #ffffff;
        }
        QMenu::separator {
            height: 1px;
            background-color: #cccccc;
            margin: 2px 0px;
        }
    """

