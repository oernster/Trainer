# Trainer Service Architecture

This document explains the “service + manager” structure outside the UI layer.

- High-level overview: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md:1)
- Canonical inventory: [`docs/codebase-inventory.md`](docs/codebase-inventory.md:1)

---

## 1. What we call a “service” in this repo

Terminology is historical and slightly mixed:

- **Managers** (mostly `src/managers/**`) orchestrate workflows, hold state, and expose Qt signals.
- **Services** (mostly `src/managers/services/**` and `src/services/**`) are focused units of work used by managers.
- **Adapters** (mostly `src/api/**`, plus parts of `src/services/**`) talk to external systems.

The composition root builds the object graph in [`python.bootstrap_app()`](src/app/bootstrap.py:80).

---

## 2. The train stack

### Orchestrator: TrainManager

The central coordinator for trains is [`python.TrainManager`](src/managers/train_manager.py:39). It:

- owns “current route” state
- schedules async fetch work in a Qt-safe way
- emits signals consumed by the UI
- delegates the actual work to injected services

Behavior notes:

- Route changes are persisted, but do not automatically trigger a fetch: the UI owns refresh timing to avoid overload during rapid route switching (see [`python.TrainManager.set_route()`](src/managers/train_manager.py:111)).

### Train services (injected into TrainManager)

These live under `src/managers/services/**` and are assembled by bootstrap.

- routing and route calculation: [`python.RouteCalculationService`](src/managers/services/route_calculation_service.py:1)
- generating/normalizing train objects: [`python.TrainDataService`](src/managers/services/train_data_service.py:18)
- config access + persistence helpers: [`python.ConfigurationService`](src/managers/services/configuration_service.py:1)
- timetable helpers: [`python.TimetableService`](src/managers/services/timetable_service.py:1)

Key behaviour note:

- In synthetic/offline mode, `TrainDataService` uses a deterministic RNG seeded by route + minute bucket to avoid “random” refresh changes (see [`python.TrainDataService._build_deterministic_rng()`](src/managers/services/train_data_service.py:98)).

---

## 3. The weather stack

### Orchestrator: WeatherManager

[`python.WeatherManager`](src/managers/weather_manager.py:209) owns:

- refresh scheduling (Qt timer)
- current forecast state (cached in-memory)
- emitting signals: updated/error/loading

It delegates I/O and parsing to the API adapter layer.

Implementation note:

- Manual refresh uses a Command object (`RefreshWeatherCommand`) which stores prior state for undo (see [`python.RefreshWeatherCommand`](src/managers/weather_manager.py:130) and [`python.WeatherManager.undo_last_command()`](src/managers/weather_manager.py:305)).

### Adapter: WeatherAPIManager + Open-Meteo source

- Adapter: [`python.WeatherAPIManager`](src/api/weather_api_manager.py:328)
- Source/parser: [`python.OpenMeteoWeatherSource`](src/api/weather_api_manager.py:89)

The HTTP client implementation used by the Open-Meteo source is also in [`src/api/weather_api_manager.py`](src/api/weather_api_manager.py:1) (see `AioHttpClient`).

---

## 4. The astronomy stack

Astronomy uses the same “manager orchestrates, services do work” shape.

- orchestrator: [`python.AstronomyManager`](src/managers/astronomy_manager.py:1)
- moon-phase computation/service: [`python.HybridMoonPhaseService`](src/services/moon_phase_service.py:1)
- UI-facing helper facade: [`src/services/astronomy_ui_facade.py`](src/services/astronomy_ui_facade.py:1)

---

## 5. Routing subsystem (services)

The routing code is a fairly self-contained subsystem under `src/services/routing/**`.

Composition helper:

- [`python.build_routing_services()`](src/services/routing/composition.py:33)

Notable building blocks:

- station service: [`python.StationService`](src/services/routing/station_service.py:1)
- route service: [`python.RouteServiceRefactored`](src/services/routing/route_service_refactored.py:1)
- converters/normalizers: [`src/services/routing/route_converter.py`](src/services/routing/route_converter.py:1), [`src/services/routing/station_name_normalizer.py`](src/services/routing/station_name_normalizer.py:1)

---

## 6. Caching

Caching utilities live under `src/cache/**`.

- memory cache: [`src/cache/memory_cache.py`](src/cache/memory_cache.py:1)
- disk cache: [`src/cache/disk_cache.py`](src/cache/disk_cache.py:1)
- station cache manager: [`src/cache/station_cache_manager.py`](src/cache/station_cache_manager.py:1)

The caching policy is pragmatic: cache where it reduces API/load cost and does not complicate UI responsiveness.

---

## 7. Configuration

Configuration models are Pydantic-based and live in [`src/managers/config_models.py`](src/managers/config_models.py:1).

- persistence and validation accessors used by the app are wrapped by [`python.ConfigurationService`](src/managers/services/configuration_service.py:1)

---

## 8. Service lifecycle & shutdown

Shutdown is best-effort and anchored at the composition root container returned by [`python.bootstrap_app()`](src/app/bootstrap.py:80) (see [`python.ApplicationContainer.shutdown()`](src/app/bootstrap.py:52)).
