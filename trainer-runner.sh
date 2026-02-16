#!/bin/bash

# Set Python path to include app directory and site-packages
export PYTHONPATH="/app:/app/lib/python3.12/site-packages:$PYTHONPATH"

# PySide6/Qt6 Configuration for KDE Platform
export QT_PLUGIN_PATH="/app/lib/python3.12/site-packages/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="/app/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms"

# Platform detection for PySide6 on KDE runtime
if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$FORCE_X11" ]; then
    export QT_QPA_PLATFORM=wayland
    echo 'Trainer: Using Wayland platform'
elif [ -n "$DISPLAY" ]; then
    export QT_QPA_PLATFORM=xcb
    echo 'Trainer: Using X11/XCB platform'
else
    export QT_QPA_PLATFORM=xcb
    echo 'Trainer: Using XCB as fallback'
fi

# Additional Qt6 environment variables
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_ENABLE_HIGHDPI_SCALING=1

# Change to app directory and run Trainer
cd /app
exec python3 main.py "$@"
