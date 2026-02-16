# Trainer Design Patterns

This document describes the patterns that are **actually present in the current codebase**, and where to find them.

- Overview doc: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md:1)
- Canonical inventory: [`docs/codebase-inventory.md`](docs/codebase-inventory.md:1)

---

## 1) Composition Root / Dependency Injection (Phase 2)

**Pattern**: Composition Root + manual dependency injection.

**Where**:

- composition root: [`python.bootstrap_app()`](src/app/bootstrap.py:80)

**Why it matters**:

- keeps construction in one place
- enables test-enforced architecture boundaries

---

## 2) Manager pattern (UI + application orchestration)

This repo uses a pragmatic “manager” convention:

- UI managers live under `src/ui/managers/**` and keep `MainWindow` from becoming a god-object.
- Application managers live under `src/managers/**` and coordinate long-running operations.

**Where**:

- UI managers: [`src/ui/managers/`](src/ui/managers/__init__.py:1)
- Main window: [`python.MainWindow`](src/ui/main_window_refactored.py:69)
- Train orchestration: [`python.TrainManager`](src/managers/train_manager.py:39)
- Weather orchestration: [`python.WeatherManager`](src/managers/weather_manager.py:209)

---

## 3) Observer (Qt Signals/Slots)

**Pattern**: Observer (implemented via Qt signals).

**Where**:

- `TrainManager` emits signals that drive UI updates (see methods around [`python.TrainManager.fetch_trains()`](src/managers/train_manager.py:130)).
- Weather manager emits updated/error/loading signals (see [`python.WeatherManager.refresh_weather()`](src/managers/weather_manager.py:279)).

**Notes**:

- UI wiring connects these signals inside the UI layer (see [`python.WidgetLifecycleManager.setup_weather_system()`](src/ui/managers/widget_lifecycle_manager.py:44)).

---

## 4) Adapter (external APIs)

**Pattern**: Adapter around external APIs.

**Where**:

- Weather: [`python.WeatherAPIManager`](src/api/weather_api_manager.py:328) + [`python.OpenMeteoWeatherSource`](src/api/weather_api_manager.py:89)

The adapter layer translates HTTP responses into internal model objects (`WeatherForecastData`, etc.).

---

## 5) Facade (UI-facing service helper)

**Pattern**: Facade.

**Where**:

- [`src/services/astronomy_ui_facade.py`](src/services/astronomy_ui_facade.py:1) provides UI-friendly access to astronomy data.

---

## 6) Command (weather)

**Pattern**: Command.

**Where**:

- Weather refresh uses a command object: [`python.RefreshWeatherCommand`](src/managers/weather_manager.py:130)

This isolates the “action” (refresh weather) from how/when it is executed and enables a small command history with an undo operation (see [`python.WeatherManager.undo_last_command()`](src/managers/weather_manager.py:305)).

---

## 7) Strategy (routing subsystem)

The routing subsystem is built from several algorithmic components (graph building, walking penalties, etc.). It is not a classic “Strategy object per algorithm” everywhere, but the subsystem is composed from independent components.

**Where**:

- routing services: [`src/services/routing/`](src/services/routing/__init__.py:1)
- walking penalties: [`src/services/routing/pathfinding_components/walking_penalties.py`](src/services/routing/pathfinding_components/walking_penalties.py:1)

---

## 8) Patterns we *avoid* by policy

### Singletons / service locators

Phase-2 policy forbids module-level singletons and service locators (enforced in [`tests/test_architecture_rules.py`](tests/test_architecture_rules.py:444)).

Configuration and theme state are held on injected instances (e.g. `ConfigManager`, `ThemeManager`), not globals.
