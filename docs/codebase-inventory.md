
# Trainer — Codebase Inventory (Canonical)

This is the **canonical, code-first** index of the repository layout and constraints.

Size policy note: this file is intentionally compact; deeper detail is in source links.

---

## 1) Entry points & composition root

- Runtime entry point: [`main.py`](main.py:1)
- Composition root: [`python.bootstrap_app()`](src/app/bootstrap.py:80)
- Allowlisted constructor helper example: [`python.build_routing_services()`](src/services/routing/composition.py:33)

---

## 2) Layering constraints (enforced)

- Layering rules: [`tests/test_architecture_rules.py`](tests/test_architecture_rules.py:208)
- Qt import boundary: [`tests/test_qt_import_constraints.py`](tests/test_qt_import_constraints.py:43)
- LOC limit: [`tests/test_loc_limit.py`](tests/test_loc_limit.py:1)

Layer map (coarse):

- UI: `src/ui/**`
- Shared models: `src/models/**`
- Domain: `src/core/models/**`, `src/core/interfaces/**`
- Orchestration: `src/managers/**`
- Infra/adapters: `src/services/**`, `src/api/**`, `src/cache/**`, `src/utils/**`, `src/workers/**`

---

## 3) Package inventory (key entry points)

### `src/app/**`

- Bootstrap + container: [`python.bootstrap_app()`](src/app/bootstrap.py:80), [`python.ApplicationContainer.shutdown()`](src/app/bootstrap.py:52)

### `src/ui/**`

- Main window: [`python.MainWindow`](src/ui/main_window_refactored.py:69)
- UI wiring: [`python.initialize_main_window()`](src/ui/main_window_components/initialization.py:30)
- Managers: [`src/ui/managers/`](src/ui/managers/__init__.py:1)

### `src/managers/**`

- Trains: [`python.TrainManager`](src/managers/train_manager.py:39)
- Weather: [`python.WeatherManager`](src/managers/weather_manager.py:209)
- Startup wiring: [`python.InitializationManager`](src/managers/initialization_manager.py:97)

Synthetic train determinism: [`python.TrainDataService._build_deterministic_rng()`](src/managers/services/train_data_service.py:98)

### `src/services/routing/**`

- Composition: [`python.build_routing_services()`](src/services/routing/composition.py:33)
- Route service: [`python.RouteServiceRefactored`](src/services/routing/route_service_refactored.py:1)

### `src/api/**` (weather)

- Adapter: [`python.WeatherAPIManager`](src/api/weather_api_manager.py:328)
- Source: [`python.OpenMeteoWeatherSource`](src/api/weather_api_manager.py:89)

### `src/cache/**`

- Disk cache: [`src/cache/disk_cache.py`](src/cache/disk_cache.py:1)
- Memory cache: [`src/cache/memory_cache.py`](src/cache/memory_cache.py:1)


