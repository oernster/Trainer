"""Theme-related helpers for MainWindow."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def setup_theme_system(*, window) -> None:
    """Setup theme switching system."""

    window.theme_manager.theme_changed.connect(window.on_theme_changed)


def get_theme_colors(*, theme_name: str) -> dict:
    """Get theme colors dictionary for widgets."""

    return {
        "background_primary": "#1a1a1a" if theme_name == "dark" else "#ffffff",
        "background_secondary": "#2d2d2d" if theme_name == "dark" else "#f5f5f5",
        "background_hover": "#404040" if theme_name == "dark" else "#e0e0e0",
        "text_primary": "#ffffff" if theme_name == "dark" else "#000000",
        "primary_accent": "#1976d2",
        "border_primary": "#404040" if theme_name == "dark" else "#cccccc",
    }


def apply_theme(*, window) -> None:
    """Apply current theme styling."""

    main_style = window.theme_manager.get_main_window_stylesheet()
    widget_style = window.theme_manager.get_widget_stylesheet()

    # Add custom styling to remove borders under menu bar
    if window.theme_manager.current_theme == "dark":
        custom_style = """
        QMainWindow {
            border: none;
        }
        QMainWindow::separator {
            border: none;
            background: transparent;
        }
        """
    else:
        custom_style = """
        QMainWindow {
            border: none;
        }
        QMainWindow::separator {
            border: none;
            background: transparent;
        }
        """

    window.setStyleSheet(main_style + widget_style + custom_style)


def apply_theme_to_all_widgets(*, window) -> None:
    """Apply theme to all widgets after creation."""

    current_theme = window.theme_manager.current_theme
    widgets = window.ui_layout_manager.get_widgets()

    train_list_widget = widgets.get("train_list_widget")
    if train_list_widget:
        train_list_widget.apply_theme(current_theme)

    weather_widget = widgets.get("weather_widget")
    if weather_widget:
        weather_widget.apply_theme(get_theme_colors(theme_name=current_theme))

    astronomy_widget = widgets.get("astronomy_widget")
    if astronomy_widget:
        astronomy_widget.apply_theme(get_theme_colors(theme_name=current_theme))


def on_theme_changed(*, window, theme_name: str) -> None:
    """Handle theme change."""

    apply_theme(window=window)
    window.ui_layout_manager.update_theme_elements(theme_name)

    widgets = window.ui_layout_manager.get_widgets()

    train_list_widget = widgets.get("train_list_widget")
    if train_list_widget:
        train_list_widget.apply_theme(theme_name)

    weather_widget = widgets.get("weather_widget")
    if weather_widget:
        weather_widget.apply_theme(get_theme_colors(theme_name=theme_name))

    astronomy_widget = widgets.get("astronomy_widget")
    if astronomy_widget:
        astronomy_widget.apply_theme(get_theme_colors(theme_name=theme_name))

    window.theme_changed.emit(theme_name)
    logger.info("Theme changed to %s", theme_name)

