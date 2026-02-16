# Trainer (Train Times) — Architecture Overview

This document is the **high-level overview** of how the application hangs together.

For the **canonical, code-first module inventory** (package-by-package responsibilities, key classes/functions, and enforced boundaries), use [`docs/codebase-inventory.md`](docs/codebase-inventory.md:1).

---

## What this repository is

Trainer is a desktop application (PySide6/Qt) that:

1. Lets the user choose a route (from/to + optional via route path)
2. Fetches or synthesizes upcoming trains for that route
3. Optionally shows weather + astronomy panels

---

## The three “centres of gravity”

### 1) UI layer (`src/ui/**`)

Everything Qt lives here (windows, dialogs, widgets). The main window implementation is [`python.MainWindow`](src/ui/main_window_refactored.py:69).

The UI is intentionally split into “UI managers” that own specific responsibilities:

- layout/build: [`python.UILayoutManager`](src/ui/managers/ui_layout_manager.py:23)
- widget creation/visibility + wiring: [`python.WidgetLifecycleManager`](src/ui/managers/widget_lifecycle_manager.py:16)
- refresh scheduling + keyboard shortcuts: [`python.EventHandlerManager`](src/ui/managers/event_handler_manager.py:19)
- settings dialogs orchestration: [`python.SettingsDialogManager`](src/ui/managers/settings_dialog_manager.py:16)

### 2) Application orchestration (`src/managers/**`)

Managers coordinate long-running operations and glue UI to services.

- trains: [`python.TrainManager`](src/managers/train_manager.py:39)
- weather: [`python.WeatherManager`](src/managers/weather_manager.py:209)
- startup wiring: [`python.InitializationManager`](src/managers/initialization_manager.py:97)

### 3) Infrastructure/adapters (`src/services/**`, `src/api/**`, `src/cache/**`, `src/utils/**`)

Code that talks to APIs, reads local data, caches results, or implements routing algorithms.

Notable examples:

- routing composition helper: [`python.build_routing_services()`](src/services/routing/composition.py:33)
- weather adapter: [`python.WeatherAPIManager`](src/api/weather_api_manager.py:328)

---

## Phase-2 architecture constraints (enforced by tests)

The repository has **test-enforced boundaries** that are treated as policy.

### Composition root

Concrete object graph assembly lives in [`python.bootstrap_app()`](src/app/bootstrap.py:80) (plus a small allowlist of pure constructor helpers).

### Layering rules

Layering is validated in [`tests/test_architecture_rules.py`](tests/test_architecture_rules.py:208).

### Qt import boundary

Qt imports are intended to be UI-only, with a narrow allowlist enforced by [`tests/test_qt_import_constraints.py`](tests/test_qt_import_constraints.py:43).

---

## Key runtime flows

### Startup

- Entry point: [`main.py`](main.py:1)
- High-level flow:
  1. Load config
  2. Compose app via [`python.bootstrap_app()`](src/app/bootstrap.py:80)
  3. Wire/initialize widgets
  4. Trigger initial refresh (notably a one-shot `window.refresh_weather()` to avoid waiting for the 30-minute timer)
  5. Fetch trains

### Manual refresh (F5 / Ctrl+R)

Keyboard shortcuts are handled by [`python.EventHandlerManager.handle_keyboard_shortcuts()`](src/ui/managers/event_handler_manager.py:354), triggered via `MainWindow.keyPressEvent`.

Refresh triggers:

- `TrainManager.fetch_trains()`
- schedules `WeatherManager.refresh_weather()`
- schedules astronomy refresh

---

## Where to go next

- Canonical module inventory: [`docs/codebase-inventory.md`](docs/codebase-inventory.md:1)
- UI-focused details: [`docs/ui-architecture.md`](docs/ui-architecture.md:1)
- Services/adapters overview: [`docs/service-architecture.md`](docs/service-architecture.md:1)
- End-to-end flows: [`docs/data-flow.md`](docs/data-flow.md:1)
- Patterns: [`docs/design-patterns.md`](docs/design-patterns.md:1)
- External integrations: [`docs/api-integration.md`](docs/api-integration.md:1)
- Widget deep dive: [`docs/widget-system.md`](docs/widget-system.md:1)
