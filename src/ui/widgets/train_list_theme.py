"""Theme helpers for [`TrainListWidget`](src/ui/widgets/train_list_widget.py:20)."""

from __future__ import annotations


def theme_colors(theme: str) -> dict[str, str]:
    """Return theme-specific color palette."""

    if theme == "dark":
        return {
            "background_primary": "#1a1a1a",
            "background_secondary": "#2d2d2d",
            "background_hover": "#404040",
            "text_primary": "#ffffff",
            "text_secondary": "#b0b0b0",
            "primary_accent": "#1976d2",
            "border_primary": "#404040",
            "border_secondary": "#555555",
            "success": "#4caf50",
            "warning": "#ff9800",
            "error": "#f44336",
        }

    return {
        "background_primary": "#ffffff",
        "background_secondary": "#f5f5f5",
        "background_hover": "#e0e0e0",
        "text_primary": "#000000",
        "text_secondary": "#757575",
        "primary_accent": "#1976d2",
        "border_primary": "#cccccc",
        "border_secondary": "#e0e0e0",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#f44336",
    }


def scroll_area_stylesheet(theme: str, colors: dict[str, str]) -> str:
    """Return the stylesheet for the scroll area."""

    if theme == "light":
        return """
            QScrollArea {
                border: 1px solid #e0e0e0 !important;
                border-radius: 8px !important;
                background-color: #ffffff !important;
            }

            QWidget {
                background-color: #ffffff !important;
            }

            QScrollBar:vertical {
                background-color: #f5f5f5 !important;
                width: 12px !important;
                border-radius: 6px !important;
                margin: 0px !important;
            }

            QScrollBar::handle:vertical {
                background-color: #e0e0e0 !important;
                border-radius: 6px !important;
                min-height: 20px !important;
                margin: 2px !important;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #d0d0d0 !important;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px !important;
            }
        """

    return f"""
        QScrollArea {{
            border: 1px solid {colors['border_primary']};
            border-radius: 8px;
            background-color: {colors['background_primary']};
        }}

        QScrollBar:vertical {{
            background-color: {colors['background_secondary']};
            width: 12px;
            border-radius: 6px;
            margin: 0px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {colors['border_secondary']};
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {colors['background_hover']};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """

