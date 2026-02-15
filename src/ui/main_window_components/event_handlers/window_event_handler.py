"""
Window event handler for the main window.

This module provides a class for handling window events like show, resize, and close,
extracted from the MainWindow class.
"""

import logging
import time
import threading
from typing import Optional, Any, Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)


class WindowEventHandler:
    """
    Handler for window events.
    
    Handles window events like show, resize, and close.
    """
    
    def __init__(self, main_window: QMainWindow, header_buttons_manager=None):
        """
        Initialize window event handler.
        
        Args:
            main_window: Parent main window
            header_buttons_manager: Manager for header buttons
        """
        self.main_window = main_window
        self.header_buttons_manager = header_buttons_manager
        self._centered = False
        self._astronomy_data_fetched = False
        self.crash_detector = None
        
        # Try to initialize crash detector if available
        self.crash_detector = None
        try:
            # We'll use a dynamic import approach to avoid hard-coding the path
            import importlib
            crash_detector_module = importlib.import_module("src.utils.crash_detector")
            self.crash_detector = getattr(crash_detector_module, "get_crash_detector")()
            logger.debug("Crash detection system initialized")
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            logger.debug(f"Crash detection system not available: {e}")
    
    def handle_show_event(self, astronomy_manager=None) -> None:
        """
        Handle window show event.
        
        Args:
            astronomy_manager: Astronomy manager to trigger data fetch
        """
        # Center window on all platforms when first shown (unified approach)
        if not self._centered:
            self._centered = True
            self._center_on_screen()

        # Only fetch astronomy data once when window is first shown
        if not self._astronomy_data_fetched and astronomy_manager:
            self._astronomy_data_fetched = True
            logger.debug("UI displayed - emitting astronomy manager ready signal")
            astronomy_manager.astronomy_data_ready.emit()
    
    def handle_resize_event(self) -> None:
        """Handle window resize event."""
        # Reposition the header buttons when window is resized
        if self.header_buttons_manager:
            self.header_buttons_manager.position_header_buttons()
    
    def handle_close_event(self, 
                          save_ui_state_callback: Optional[Callable] = None,
                          weather_manager=None,
                          astronomy_manager=None,
                          initialization_manager=None,
                          train_manager=None) -> None:
        """
        Handle window close event with enhanced error handling.
        
        Args:
            save_ui_state_callback: Callback to save UI state
            weather_manager: Weather manager to shutdown
            astronomy_manager: Astronomy manager to shutdown
            initialization_manager: Initialization manager to shutdown
            train_manager: Train manager to shutdown
        """
        try:
            logger.debug("Application closing - starting main window cleanup")

            # Save UI state before closing
            try:
                if save_ui_state_callback:
                    save_ui_state_callback()
                    logger.debug("UI state saved successfully")
            except Exception as e:
                logger.warning(f"Error saving UI state: {e}")

            # Shutdown weather manager if it exists
            if weather_manager:
                try:
                    weather_manager.shutdown()
                    logger.debug("Weather manager shutdown complete")
                except Exception as e:
                    logger.warning(f"Error shutting down weather manager: {e}")

            # Shutdown initialization manager if it exists
            if initialization_manager:
                try:
                    initialization_manager.shutdown()
                    logger.debug("Initialization manager shutdown complete")
                except Exception as e:
                    logger.warning(f"Error shutting down initialization manager: {e}")

            # Shutdown astronomy manager if it exists
            if astronomy_manager:
                try:
                    astronomy_manager.shutdown()
                    logger.debug("Astronomy manager shutdown complete")
                except Exception as e:
                    logger.warning(f"Error shutting down astronomy manager: {e}")

            # Stop all QTimers in this window
            try:
                from PySide6.QtCore import QTimer
                timers_stopped = 0
                for timer in self.main_window.findChildren(QTimer):
                    try:
                        if timer.isActive():
                            timer.stop()
                            timers_stopped += 1
                    except RuntimeError as timer_error:
                        logger.warning(f"Error stopping timer: {timer_error}")
                
                if timers_stopped > 0:
                    logger.debug(f"Stopped {timers_stopped} QTimers in main window")
                else:
                    logger.debug("No active QTimers found in main window")
                    
            except Exception as timer_cleanup_error:
                logger.warning(f"Error during timer cleanup: {timer_cleanup_error}")

            # Clean up any remaining threads (focus on non-daemon threads only)
            try:
                import threading
                import time
                
                active_threads = threading.active_count()
                if active_threads > 1:  # Main thread + others
                    # Separate daemon and non-daemon threads
                    non_daemon_threads = []
                    daemon_count = 0
                    
                    for thread in threading.enumerate():
                        if thread != threading.current_thread():
                            if thread.daemon:
                                daemon_count += 1
                            else:
                                non_daemon_threads.append(thread)
                    
                    # Only handle non-daemon threads (these can prevent shutdown)
                    if non_daemon_threads:
                        logger.debug(f"🔄 Gracefully stopping {len(non_daemon_threads)} non-daemon threads...")
                        for thread in non_daemon_threads:
                            try:
                                thread.join(timeout=0.5)
                                if not thread.is_alive():
                                    logger.debug(f"✅ Non-daemon thread {thread.name} stopped")
                                else:
                                    logger.warning(f"⚠️ Non-daemon thread {thread.name} did not stop gracefully")
                            except Exception as join_error:
                                logger.warning(f"⚠️ Error joining thread {thread.name}: {join_error}")
                    
                    # Daemon threads are handled silently (they don't prevent shutdown)
                    # No need to actively terminate daemon threads as they won't block shutdown
                    if daemon_count > 0:
                        logger.debug(f"ℹ️ {daemon_count} daemon threads will be cleaned up automatically on exit")
                    
                    # Brief pause for cleanup
                    time.sleep(0.1)
                    
                    # Final check - only warn about non-daemon threads
                    final_non_daemon = []
                    for thread in threading.enumerate():
                        if thread != threading.current_thread() and not thread.daemon:
                            final_non_daemon.append(thread)
                    
                    if final_non_daemon:
                        logger.warning(f"⚠️ {len(final_non_daemon)} non-daemon threads still active after cleanup")
                        for thread in final_non_daemon:
                            logger.warning(f"  - Active thread: {thread.name} (alive: {thread.is_alive()})")
                    else:
                        logger.debug("✅ All critical threads cleaned up successfully")
                else:
                    logger.debug("✅ No background threads to clean up")
                    
            except Exception as thread_cleanup_error:
                logger.warning(f"⚠️ Error during thread cleanup in closeEvent: {thread_cleanup_error}")

            # Clear references to prevent memory leaks
            try:
                weather_manager = None
                astronomy_manager = None
                initialization_manager = None
                train_manager = None
                logger.debug("Manager references cleared")
            except Exception as ref_error:
                logger.warning(f"Error clearing references: {ref_error}")

            logger.debug("Main window cleanup completed successfully")
            
        except Exception as close_error:
            logger.error(f"Critical error in closeEvent: {close_error}")
    
    def _center_on_screen(self) -> None:
        """Center the window on the primary screen."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.main_window.frameGeometry()
            x = (screen_geometry.width() - window_geometry.width()) // 2
            y = (screen_geometry.height() - window_geometry.height()) // 2
            self.main_window.move(x, y)
            logger.debug(f"Centered main window at ({x}, {y})")
    
    def register_widgets_for_crash_monitoring(self, widgets_dict: dict) -> None:
        """
        Register widgets for crash monitoring.
        
        Args:
            widgets_dict: Dictionary of widget names and widgets
        """
        if self.crash_detector:
            for name, widget in widgets_dict.items():
                self.crash_detector.register_widget(name, widget)
                logger.debug(f"Registered {name} for crash monitoring")