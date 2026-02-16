"""
Astronomy system manager for the main window.

This module provides a class for managing the astronomy system,
including initialization, updates, and error handling.
"""

import logging
import asyncio
from typing import Optional, Any, Dict, Callable

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class AstronomySystemManager(QObject):
    """
    Manager for the astronomy system.
    
    Handles astronomy system initialization, updates, and error handling.
    """
    
    # Signals
    astronomy_updated = Signal(object)
    astronomy_error = Signal(str)
    astronomy_loading_changed = Signal(bool)
    astronomy_data_ready = Signal()
    
    def __init__(self, config_manager, parent: Optional[QObject] = None):
        """
        Initialize astronomy system manager.
        
        Args:
            config_manager: Configuration manager for accessing config
            parent: Parent QObject
        """
        super().__init__(parent)
        self.config_manager = config_manager
        # Optional back-reference for injected composition; set by the UI layer.
        self.main_window = None
        self.config = None
        self.astronomy_manager = None
        self.astronomy_widget = None
        
    def setup_astronomy_system(self, config, astronomy_widget: Optional[Any] = None) -> bool:
        """
        Setup astronomy integration system.
        
        Args:
            config: Application configuration
            astronomy_widget: Astronomy widget to connect to
            
        Returns:
            True if astronomy system was initialized successfully, False otherwise
        """
        self.config = config
        self.astronomy_widget = astronomy_widget
        
        # Handle missing astronomy configuration gracefully
        if (
            not self.config
            or not hasattr(self.config, "astronomy")
            or not self.config.astronomy
        ):
            logger.info("Astronomy configuration not available - widget will show placeholder")
            # Still connect widget signals and show placeholder content
            if self.astronomy_widget:
                # Connect astronomy widget signals even without config
                self.astronomy_widget.astronomy_refresh_requested.connect(
                    self.refresh_astronomy
                )
                self.astronomy_widget.astronomy_link_clicked.connect(
                    self.on_astronomy_link_clicked
                )
                logger.info("Astronomy widget signals connected (no config)")
            
            self._update_astronomy_status(False)
            return False

        try:
            # Always connect astronomy widget signals if it exists
            if self.astronomy_widget:
                # Connect astronomy widget signals
                self.astronomy_widget.astronomy_refresh_requested.connect(
                    self.refresh_astronomy
                )
                self.astronomy_widget.astronomy_link_clicked.connect(
                    self.on_astronomy_link_clicked
                )

                # Update astronomy widget config
                self.astronomy_widget.update_config(self.config.astronomy)

            # Only initialize astronomy manager if astronomy is enabled
            if self.config.astronomy.enabled:
                # Phase 2 boundary: composition happens in bootstrap.
                # AstronomySystemManager only wires an injected AstronomyManager.
                if not self.astronomy_manager:
                    self.astronomy_manager = getattr(self.main_window, "astronomy_manager", None)

                if not self.astronomy_manager:
                    logger.warning(
                        "Astronomy system setup requested but no AstronomyManager was injected; skipping"
                    )
                    self._update_astronomy_status(False)
                    return False

                # Connect astronomy manager Qt signals to astronomy widget
                self.astronomy_manager.astronomy_updated.connect(
                    self.on_astronomy_updated
                )
                self.astronomy_manager.astronomy_error.connect(self.on_astronomy_error)
                self.astronomy_manager.loading_state_changed.connect(
                    self.on_astronomy_loading_changed
                )

                # Connect astronomy manager signals directly to astronomy widget
                if self.astronomy_widget:
                    self.astronomy_manager.astronomy_updated.connect(
                        self.astronomy_widget.on_astronomy_updated
                    )
                    self.astronomy_manager.astronomy_error.connect(
                        self.astronomy_widget.on_astronomy_error
                    )
                    self.astronomy_manager.loading_state_changed.connect(
                        self.astronomy_widget.on_astronomy_loading
                    )

                logger.debug("Astronomy system initialized with API key")
                # Emit signal to indicate astronomy manager is ready for data fetch
                self.astronomy_data_ready.emit()
            else:
                logger.info(
                    "Astronomy system initialized without API key - widget will show placeholder"
                )

            # Update astronomy status and visibility
            enabled = self.config.astronomy.enabled
            self._update_astronomy_status(enabled)

            # Only hide the widget if explicitly disabled in config
            # Always show by default (will show placeholder if no API key)
            if self.astronomy_widget:
                # Only hide if explicitly disabled, otherwise show by default
                self.astronomy_widget.setVisible(enabled)
                
            return True

        except Exception as e:
            logger.error(f"Failed to initialize astronomy system: {e}")
            self._update_astronomy_status(False)
            # Don't hide the widget - let it show the error/placeholder state
            return False
    
    def _update_astronomy_status(self, enabled: bool) -> None:
        """
        Update astronomy status display.
        
        Args:
            enabled: Whether astronomy integration is enabled
        """
        # Status bar removed - this method is kept for compatibility but does nothing
        logger.debug(f"Astronomy system status: {'enabled' if enabled else 'disabled'}")
    
    def refresh_astronomy(self) -> None:
        """Trigger manual astronomy refresh."""
        if self.astronomy_manager:
            # Run async refresh using QTimer to defer to next event loop iteration
            import asyncio

            try:
                # Check if there's already an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in an async context, create a task
                    # Additional null check to satisfy Pylance
                    if self.astronomy_manager:
                        asyncio.create_task(self.astronomy_manager.refresh_astronomy())
                        logger.info("Manual astronomy refresh requested (async task created)")
                except RuntimeError:
                    # No running loop, create a new one
                    def run_refresh():
                        # Additional null check to satisfy Pylance
                        if self.astronomy_manager:
                            asyncio.run(self.astronomy_manager.refresh_astronomy())

                    # Use QTimer to run in next event loop iteration
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(0, run_refresh)
                    logger.info("Manual astronomy refresh scheduled (QTimer)")
            except Exception as e:
                logger.warning(f"Failed to refresh astronomy: {e}")
        else:
            logger.info(
                "Astronomy refresh requested but no manager available (missing API key)"
            )
    
    def on_astronomy_updated(self, astronomy_data: Any) -> None:
        """
        Handle astronomy data update.
        
        Args:
            astronomy_data: Updated astronomy data
        """
        logger.debug("Astronomy data updated")
        # Re-emit the signal for other components
        self.astronomy_updated.emit(astronomy_data)
        # Emit data ready signal
        self.astronomy_data_ready.emit()
    
    def on_astronomy_error(self, error_message: str) -> None:
        """
        Handle astronomy error.
        
        Args:
            error_message: Error message
        """
        logger.warning(f"Astronomy error: {error_message}")
        # Re-emit the signal for other components
        self.astronomy_error.emit(error_message)
    
    def on_astronomy_loading_changed(self, is_loading: bool) -> None:
        """
        Handle astronomy loading state change.
        
        Args:
            is_loading: Whether astronomy data is loading
        """
        if is_loading:
            logger.debug("Astronomy data loading...")
        else:
            logger.debug("Astronomy data loading complete")
        # Re-emit the signal for other components
        self.astronomy_loading_changed.emit(is_loading)
    
    def on_astronomy_link_clicked(self, url: str) -> None:
        """
        Handle astronomy link clicks.
        
        Args:
            url: URL that was clicked
        """
        logger.info(f"Astronomy link clicked: {url}")
        # Link will be opened automatically by the astronomy widget
    
    def update_config(self, config) -> None:
        """
        Update configuration.
        
        Args:
            config: Updated configuration
        """
        self.config = config
        
        if hasattr(self.config, "astronomy") and self.config.astronomy:
            # Check if we need to reinitialize the astronomy system
            needs_reinit = False
            needs_data_fetch = False

            if self.config.astronomy.enabled:
                if not self.astronomy_manager:
                    # Astronomy was enabled, initialize manager
                    needs_reinit = True
                    needs_data_fetch = True
                elif self.astronomy_manager:
                    # Update existing astronomy manager configuration
                    self.astronomy_manager.update_config(self.config.astronomy)
                    
            # Reinitialize astronomy system if needed
            if needs_reinit:
                self.setup_astronomy_system(self.config, self.astronomy_widget)
                logger.info("Astronomy system reinitialized with new API key")
                
            # Trigger data fetch if needed
            if needs_data_fetch and self.astronomy_manager:
                logger.info("Triggering astronomy data fetch for new/updated API key")
                self.refresh_astronomy()
                
            # Always update astronomy widget configuration
            if self.astronomy_widget:
                logger.info(f"Updating astronomy widget with config: enabled={self.config.astronomy.enabled}, categories={self.config.astronomy.enabled_link_categories}")
                self.astronomy_widget.update_config(self.config.astronomy)
                logger.info("Updated astronomy widget configuration")
                
            # Update astronomy status
            self._update_astronomy_status(self.config.astronomy.enabled)
            
            logger.debug("Astronomy system configuration updated")
    
    def shutdown(self) -> None:
        """Shutdown astronomy system."""
        if self.astronomy_manager:
            try:
                # Astronomy manager doesn't have a shutdown method, but we can clear references
                self.astronomy_manager = None
                logger.debug("Astronomy system shutdown complete")
            except Exception as e:
                logger.warning(f"Error shutting down astronomy system: {e}")
