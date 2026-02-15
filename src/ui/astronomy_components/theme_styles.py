"""Qt stylesheet builders for astronomy-related UI."""

from __future__ import annotations


def build_astronomy_settings_dialog_stylesheet(*, theme_name: str) -> str:
    """Return the QSS stylesheet for the astronomy settings dialog."""

    if theme_name == "light":
        return """
        QDialog {
            background-color: #ffffff;
            color: #1976d2;
        }
        QGroupBox {
            color: #1976d2;
            border: 1px solid #cccccc;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            color: #1976d2;
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px 0 4px;
            background-color: #ffffff;
        }
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 4px;
            color: #1976d2;
        }
        QLineEdit:focus {
            border-color: #1976d2;
        }
        QCheckBox {
            color: #1976d2;
            background-color: #ffffff;
            spacing: 5px;
            font-size: 12px;
        }
        QCheckBox::text {
            color: #1976d2;
        }
        QCheckBox::indicator {
            background-color: #ffffff;
            border: 1px solid #cccccc;
        }
        QCheckBox::indicator:checked {
            background-color: #1976d2;
            border: 1px solid #1976d2;
        }
        QPushButton {
            background-color: #1976d2;
            border: 1px solid #1976d2;
            border-radius: 4px;
            padding: 6px 12px;
            color: #ffffff;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1565c0;
            border-color: #1565c0;
        }
        QPushButton:pressed {
            background-color: #0d47a1;
            border-color: #0d47a1;
        }
        QLabel {
            color: #1976d2;
            background-color: transparent;
        }
        """

    return """
    QDialog {
        background-color: #1a1a1a;
        color: #ffffff;
    }
    QGroupBox {
        color: #ffffff;
        border: 1px solid #404040;
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
        background-color: #1a1a1a;
    }
    QGroupBox::title {
        color: #1976d2;
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px 0 4px;
        background-color: #1a1a1a;
    }
    QLineEdit {
        background-color: #2d2d2d;
        border: 1px solid #404040;
        border-radius: 4px;
        padding: 4px;
        color: #ffffff;
    }
    QLineEdit:focus {
        border-color: #1976d2;
    }
    QCheckBox {
        color: #ffffff;
        background-color: #1a1a1a;
        spacing: 5px;
        font-size: 12px;
        padding: 2px;
    }
    QCheckBox::text {
        color: #ffffff;
        padding-left: 5px;
    }
    QCheckBox::indicator {
        background-color: #2d2d2d;
        border: 1px solid #404040;
    }
    QCheckBox::indicator:checked {
        background-color: #1976d2;
        border: 1px solid #1976d2;
    }
    QPushButton {
        background-color: #1976d2;
        border: 1px solid #1976d2;
        border-radius: 4px;
        padding: 6px 12px;
        color: #ffffff;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #1565c0;
        border-color: #1565c0;
    }
    QPushButton:pressed {
        background-color: #0d47a1;
        border-color: #0d47a1;
    }
    QLabel {
        color: #ffffff;
        background-color: transparent;
    }
    """

