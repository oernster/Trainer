"""
Main entry point for the Trainer train times application.
Author: Oliver Ernster

This module initializes the application, sets up logging, loads the configuration,
and starts the main window with theme support and custom icon.
"""

import sys
import tempfile
import os
import traceback
import io
from pathlib import Path

# ---------------------------------------------------------------------------
# Ultra-early CLI flags
# ---------------------------------------------------------------------------
# build/install scripts may run `trainer --version` to verify installation.
# That must not start Qt or acquire singleton locks.
if "--version" in sys.argv:
    try:
        from version import __app_name__, __version__

        print(f"{__app_name__} {__version__}")
    except Exception:
        # Fall back to something, but always exit cleanly.
        print("Trainer")
    raise SystemExit(0)


def _log_startup(logger) -> None:
    logger.info("Trainer starting")
    try:
        import os
        import sys

        logger.info("sys.executable=%s", sys.executable)
        logger.info("cwd=%s", os.getcwd())
        logger.info("argv=%s", sys.argv)
    except Exception:
        # Keep startup logging best-effort.
        pass

    # Log offline data resolution early. This is critical for diagnosing macOS
    # packaged builds where the UI can otherwise fail "silently" (empty station
    # dropdowns, no routes found).
    try:
        from src.utils.data_path_resolver import get_data_directory

        try:
            data_dir = get_data_directory()
            logger.info("Resolved offline data directory=%s", data_dir)
            lines_dir = data_dir / "lines"
            logger.info(
                "Resolved offline lines directory=%s (exists=%s)",
                lines_dir,
                lines_dir.exists(),
            )
        except Exception as exc:
            logger.exception("Failed to resolve offline data directory: %s", exc)
    except Exception:
        # Resolver import can fail in badly broken environments; ignore.
        pass


def _log_shutdown(logger, exit_code: int) -> None:
    logger.info("Trainer exiting with code %s", exit_code)

# CRITICAL: Ultra-early singleton check before ANY imports or initialization
#
# The previous implementation used PID-in-a-file. That is fragile in Flatpak
# because PIDs can be reused and `/tmp` can be shared across launches, leading to
# false positives (“another instance is running”) after crashes or restarts.
#
# Use an actual OS-level file lock instead.
_ultra_early_lock_handle = None


def _ultra_early_lock_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "trainer_app_ultra_early.lock"
    return Path(tempfile.gettempdir()) / "trainer_app_ultra_early.lock"


def check_single_instance_ultra_early():
    """Ultra-early singleton check using an OS file lock (pre-Qt)."""

    global _ultra_early_lock_handle
    lock_file_path = _ultra_early_lock_path()

    try:
        lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Non-fatal: fall back to attempting to open anyway.
        pass

    try:
        # Keep the file handle open for the lifetime of the process so the lock
        # remains held.
        f = open(lock_file_path, "a+", encoding="utf-8")

        if sys.platform == "win32":
            import msvcrt

            try:
                # Non-blocking exclusive lock
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                print("ERROR: Another instance of Trainer is already running!")
                print("Please close the existing instance before starting a new one.")
                sys.exit(1)
        else:
            import fcntl

            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print("ERROR: Another instance of Trainer is already running!")
                print("Please close the existing instance before starting a new one.")
                sys.exit(1)

        # Record our PID for debugging only (not used for correctness)
        try:
            f.seek(0)
            f.truncate()
            f.write(str(os.getpid()))
            f.flush()
        except Exception:
            pass

        _ultra_early_lock_handle = f
        return lock_file_path

    except Exception as e:
        print(f"Warning: Failed to acquire ultra-early lock file: {e}")
        return None

# Perform ultra-early singleton check BEFORE any other imports
_ultra_early_lock_file = check_single_instance_ultra_early()

# Now proceed with normal imports
import asyncio
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QSize, QSharedMemory
from PySide6.QtGui import QIcon
from src.ui.splash_screen import TrainerSplashScreen
from src.managers.config_manager import ConfigManager, ConfigurationError
from src.app.bootstrap import bootstrap_app
from version import (
    __version__,
    __app_name__,
    __app_display_name__,
    __company__,
    __copyright__,
)

def cleanup_ultra_early_lock():
    """Clean up the ultra-early lock file."""
    global _ultra_early_lock_file
    global _ultra_early_lock_handle

    try:
        if _ultra_early_lock_handle is not None:
            try:
                if sys.platform != "win32":
                    import fcntl

                    fcntl.flock(_ultra_early_lock_handle.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                _ultra_early_lock_handle.close()
            except Exception:
                pass
            _ultra_early_lock_handle = None
    except Exception:
        pass

    if _ultra_early_lock_file and _ultra_early_lock_file.exists():
        try:
            _ultra_early_lock_file.unlink()
        except Exception as e:
            print(f"Warning: Failed to remove ultra-early lock file: {e}")

def cleanup_application_resources():
    """Comprehensive cleanup of all application resources to prevent hanging processes."""
    try:
        
        # Get the current QApplication instance
        app = QApplication.instance()
        if app:
            # Clean up shared memory if it's our SingleInstanceApplication
            try:
                if isinstance(app, SingleInstanceApplication):
                    app.cleanup_shared_memory()
            except:
                pass
            
            # Stop all timers with enhanced error handling
            try:
                for obj in app.findChildren(QTimer):
                    try:
                        if obj.isActive():
                            obj.stop()
                    except:
                        pass
            except:
                pass
            
            # Process any remaining events with timeout protection
            try:
                import time
                start_time = time.time()
                timeout = 2.0
                
                while (time.time() - start_time) < timeout:
                    app.processEvents()
                    time.sleep(0.01)
                    if (time.time() - start_time) > 0.5:
                        break
            except:
                pass
            
            # Quit the application properly with enhanced error handling
            try:
                if app and not app.closingDown():
                    app.quit()
            except:
                pass
        
        # Clean up any remaining threads (focus on non-daemon threads only)
        try:
            import threading
            import time
            
            active_threads = threading.active_count()
            if active_threads > 1:
                non_daemon_threads = []
                
                for thread in threading.enumerate():
                    if thread != threading.current_thread() and not thread.daemon:
                        non_daemon_threads.append(thread)
                
                if non_daemon_threads:
                    for thread in non_daemon_threads:
                        try:
                            thread.join(timeout=1.0)
                        except:
                            pass
                
                time.sleep(0.2)
        except:
            pass
        
        # Keep a user-visible confirmation on stdout, even when console logging
        # is set to WARNING+.
        try:
            print("✅ Application shutdown completed", flush=True)
        except Exception:
            pass

        try:
            logging.getLogger(__name__).info("Application shutdown completed")
        except Exception:
            pass
        
    except:
        pass

def setup_logging():
    """Setup application logging with file and console output."""
    import os
    from pathlib import Path
    
    # Create log directory in user's home directory
    if sys.platform == "darwin":  # macOS
        log_dir = Path.home() / "Library" / "Logs" / "Trainer"
    elif sys.platform == "win32":  # Windows
        log_dir = Path(os.environ.get("APPDATA", Path.home())) / "Trainer" / "logs"
    else:  # Linux and others
        log_dir = Path.home() / ".local" / "share" / "trainer" / "logs"
    
    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "train_times.log"
    
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")

    # Windows consoles can be cp1252. Ensure our console handler can emit unicode
    # (e.g. arrows like → / ↔) without crashing logging.
    console_stream = sys.stderr
    try:
        if hasattr(sys.stderr, "buffer"):
            console_stream = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding="utf-8",
                errors="backslashreplace",
                line_buffering=True,
            )
    except Exception:
        console_stream = sys.stderr
    console_handler = logging.StreamHandler(console_stream)

    # Default to a quiet console for interactive launches, while keeping a more
    # detailed file log for post-mortems.
    #
    # Overrides:
    # - TRAINER_CONSOLE_LOG_LEVEL (default WARNING)
    # - TRAINER_FILE_LOG_LEVEL (default INFO)
    # - TRAINER_LOG_LEVEL (legacy: sets both)
    legacy_level = os.environ.get("TRAINER_LOG_LEVEL")
    console_level_name = (
        legacy_level or os.environ.get("TRAINER_CONSOLE_LOG_LEVEL", "WARNING")
    ).upper()
    file_level_name = (
        legacy_level or os.environ.get("TRAINER_FILE_LOG_LEVEL", "INFO")
    ).upper()

    console_level = getattr(logging, console_level_name, logging.WARNING)
    file_level = getattr(logging, file_level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    file_handler.setLevel(file_level)
    console_handler.setLevel(console_level)

    # Replace any existing handlers (PySide apps sometimes re-enter logging setup).
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

def setup_application_icon(app: QApplication):
    """
    Setup application icon using Unicode train emoji.

    Args:
        app: QApplication instance
    """
    from PySide6.QtGui import QPixmap, QPainter, QFont
    from PySide6.QtCore import Qt
    
    # Create a simple icon from the train emoji
    try:
        # Create a pixmap for the icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Paint the emoji onto the pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set up font for emoji - use system font that supports emojis
        font = QFont()
        font.setPointSize(44)  # Slightly smaller to ensure it fits
        font.setFamily("Apple Color Emoji")  # macOS emoji font
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.black)
        
        # Draw the train emoji centered
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🚂")
        painter.end()
        
        # Create icon and set it
        icon = QIcon(pixmap)
        app.setWindowIcon(icon)
        
        
    except Exception as e:
        logging.warning(f"Failed to create emoji icon, using default: {e}")

class SingleInstanceApplication(QApplication):
    """QApplication subclass that enforces single instance with dual protection."""
    
    def __init__(self, argv):
        # Additional Qt-level singleton check
        existing_app = QApplication.instance()
        if existing_app is not None:
            print("CRITICAL ERROR: QApplication instance already exists!")
            print("This indicates multiple application launches. Exiting immediately.")
            sys.exit(1)
        
        # Create shared memory segment for single instance check
        temp_shared_memory = QSharedMemory("TrainerAppSingleInstance")
        
        # Try to attach to existing shared memory
        if temp_shared_memory.attach():
            # Another instance is already running - exit immediately
            print("ERROR: Another Qt instance of Trainer is already running!")
            print("Please close the existing instance before starting a new one.")
            temp_shared_memory.detach()
            sys.exit(1)
        
        # No existing instance found, proceed with initialization
        super().__init__(argv)
        
        # Now create our own shared memory segment
        self.shared_memory = QSharedMemory("TrainerAppSingleInstance")
        if not self.shared_memory.create(1):
            print("CRITICAL ERROR: Failed to create shared memory for single instance check!")
            print("This should not happen. Exiting to prevent multiple instances.")
            sys.exit(1)
        
    
    def cleanup_shared_memory(self):
        """Clean up shared memory segment with enhanced error handling."""
        try:
            if hasattr(self, 'shared_memory') and self.shared_memory:
                try:
                    if self.shared_memory.isAttached():
                        self.shared_memory.detach()
                except:
                    pass
                
                self.shared_memory = None
        except:
            pass

def main():
    """Main application entry point."""
    try:
        # Setup logging first
        setup_logging()
        logger = logging.getLogger(__name__)
        _log_startup(logger)

        # Create single instance QApplication with dual protection
        app = SingleInstanceApplication(sys.argv)
        app.setApplicationName(__app_name__)
        app.setApplicationDisplayName(__app_display_name__)
        app.setApplicationVersion(__version__)
        app.setOrganizationName(__company__)
        app.setOrganizationDomain("trainer.local")

        # Set desktop file name for better Linux integration
        app.setDesktopFileName("trainer")

        # Prevent multiple instances
        app.setQuitOnLastWindowClosed(True)

        # Setup application icon (must be done early for Windows taskbar)
        setup_application_icon(app)

        # Create and show splash screen first
        splash = TrainerSplashScreen()
        splash.show()
        splash.show_message("Initializing application...")
        app.processEvents()  # Process events to show splash screen

        try:
            # Initialize configuration manager (will use AppData on Windows)
            splash.show_message("Loading configuration...")
            app.processEvents()

            config_manager = ConfigManager()

            # Install default config to AppData if needed
            if config_manager.install_default_config_to_appdata():
                logger.debug("Default configuration installed to AppData")

            # Load configuration
            config = config_manager.load_config()

            # Bootstrap application object graph (composition root)
            splash.show_message("Creating main window...")
            app.processEvents()

            splash.show_message("Initializing train manager...")
            app.processEvents()

            container = bootstrap_app(config_manager=config_manager, config=config)
            window = container.window
            train_manager = container.train_manager

            # Connect signals between components
            splash.show_message("Connecting components...")
            app.processEvents()

            # Wiring is performed by bootstrap; keep this stage for splash parity.

            # The optimized widget initialization will handle weather and NASA widgets
            # Train data will be fetched after widget initialization completes
            splash.show_message("Optimizing widget initialization...")
            app.processEvents()
            
            # Connect to initialization completion to start train data fetch and show window
            def on_widgets_ready():
                splash.show_message("Loading train data...")
                app.processEvents()

                # ------------------------------------------------------------------
                # Weather refresh: fetch immediately after widget wiring
                # ------------------------------------------------------------------
                # Regression fix: the refactor removed the one-shot weather fetch from
                # InitializationManager, and WeatherManager's auto-refresh interval is
                # 30 minutes. Trigger an immediate refresh so the Weather panel
                # populates on first run.
                try:
                    if hasattr(window, "refresh_weather"):
                        window.refresh_weather()
                except Exception as exc:
                    logger.debug("Initial weather refresh failed: %s", exc)

                # Show the main window as soon as widgets are initialized.
                #
                # Rationale: previously the splash was kept open until the first
                # `train_manager.trains_updated` signal. On some launches
                # (especially from the desktop environment), that signal can be
                # delayed/missed due to threading/Qt event timing, leaving the
                # splash stuck indefinitely. Showing the window here removes that
                # failure mode; train data can continue loading in the background.
                splash.show_message("Ready!")
                app.processEvents()

                window.show()
                window.raise_()
                window.activateWindow()
                splash.close()

                # Single train data fetch after widgets are ready (non-blocking)
                try:
                    train_manager.fetch_trains()
                except Exception as exc:
                    logger.debug("Initial train fetch failed: %s", exc)
            
            # Use proper signaling instead of timers
            if window.initialization_manager:
                window_shown = {"value": False}

                def _show_main_window_and_close_splash(*, reason: str) -> None:
                    if window_shown["value"]:
                        return
                    window_shown["value"] = True

                    try:
                        logger.info("Showing main window (%s)", reason)
                    except Exception:
                        pass

                    try:
                        window.show()
                        window.raise_()
                        window.activateWindow()
                    finally:
                        try:
                            splash.close()
                        except Exception:
                            pass

                def on_init_error(message: str) -> None:
                    # Never allow the splash to remain indefinitely if the
                    # initialization manager errors.
                    try:
                        logger.error("Initialization failed: %s", message)
                    except Exception:
                        pass

                    _show_main_window_and_close_splash(reason="initialization_error")

                # Normal happy-path.
                window.initialization_manager.initialization_completed.connect(on_widgets_ready)
                try:
                    window.initialization_manager.initialization_error.connect(on_init_error)
                except Exception:
                    pass

                # Watchdog: if neither completed nor error fires (hang), show
                # the main window anyway after a short grace period.
                def _init_watchdog() -> None:
                    _show_main_window_and_close_splash(reason="init_watchdog")

                QTimer.singleShot(10000, _init_watchdog)
                
            else:
                # Fallback if initialization manager not available - still use signals
                def fallback_startup():
                    # Mirror the initialization-complete path: attempt weather refresh
                    # before fetching trains.
                    try:
                        if hasattr(window, "refresh_weather"):
                            window.refresh_weather()
                    except Exception as exc:
                        logger.debug("Initial weather refresh (fallback) failed: %s", exc)

                    # Mirror the main path: show window immediately, then fetch.
                    window.show()
                    window.raise_()
                    window.activateWindow()
                    splash.close()

                    try:
                        train_manager.fetch_trains()
                    except Exception as exc:
                        logger.debug("Initial train fetch failed (fallback): %s", exc)
                
                QTimer.singleShot(1000, fallback_startup)

            # Don't show main window immediately - wait for initialization to complete
            # The window will be shown by the on_widgets_ready callback

            # Keep a user-visible confirmation on stdout, even when console
            # logging is set to WARNING+.
            print("🚀 Trainer initialized successfully")
            logger.info("Trainer initialized successfully")

            # Start event loop
            exit_code = app.exec()

            # Comprehensive cleanup before exit
            _log_shutdown(logger, exit_code)

            try:
                container.shutdown()
            except Exception:
                # Shutdown must never prevent process exit.
                pass

            cleanup_application_resources()
            sys.exit(exit_code)

        except ConfigurationError as e:
            try:
                traceback.print_exc()
            except Exception:
                pass
            logger.error(f"Configuration error: {e}")
            # Show error message without creating another window
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Configuration Error")
            msg_box.setText(str(e))
            msg_box.exec()
            sys.exit(1)

        except Exception as e:
            try:
                traceback.print_exc()
            except Exception:
                pass
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)

    finally:
        # Always cleanup the ultra-early lock file
        cleanup_ultra_early_lock()


if __name__ == "__main__":
    main()
