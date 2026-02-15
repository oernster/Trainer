"""Styling helpers for [`CallingPointsManager`](src/ui/widgets/train_components/calling_points_manager.py:25)."""

from __future__ import annotations

from typing import Mapping


def stylesheet_for_direct_label(theme: str, colors: Mapping[str, str]) -> str:
    """Return a label stylesheet for direct/standard cases."""

    if theme == "light":
        return """
            QLabel {
                color: #212121;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """

    return f"""
        QLabel {{
            color: {colors['text_primary']};
            background-color: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
    """


def stylesheet_for_station_label(
    *,
    theme: str,
    colors: Mapping[str, str],
    is_walking: bool,
    is_user_interchange: bool,
    is_origin_or_destination: bool,
) -> str:
    """Return the label stylesheet used for station display."""

    if is_walking:
        return """
            QLabel {
                background-color: transparent !important;
                border: none !important;
                margin: 0px !important;
                padding: 0px !important;
            }
        """

    if is_user_interchange:
        interchange_color = colors["warning"]
        return f"""
            QLabel {{
                background-color: transparent !important;
                color: {interchange_color} !important;
                border: none !important;
                margin: 0px !important;
                padding: 0px !important;
            }}
        """

    if is_origin_or_destination and theme == "light":
        return """
            QLabel {
                background-color: transparent !important;
                color: #1976d2 !important;
                border: none !important;
                margin: 0px !important;
                padding: 0px !important;
            }
        """

    if is_origin_or_destination:
        return f"""
            QLabel {{
                background-color: transparent !important;
                color: {colors['text_primary']} !important;
                border: none !important;
                margin: 0px !important;
                padding: 0px !important;
            }}
        """

    return f"""
        QLabel {{
            background-color: transparent !important;
            color: {colors['primary_accent']} !important;
            border: none !important;
            margin: 0px !important;
            padding: 0px !important;
        }}
    """

