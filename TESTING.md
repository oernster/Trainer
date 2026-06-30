# Testing

This document describes the testing architecture of the Trainer project and how to run and extend it.

## Testing philosophy

The suite uses a **phased, scoped coverage gate**. A hard 100% branch-coverage requirement is enforced on the stable core only:

- `src/core/models`
- `src/core/interfaces`

Everything else in `tests/` provides behavioural coverage (managers, services, UI, regressions, architecture rules) without a hard coverage gate.

**Why the gate is scoped.** The core domain models (`Station`, `Route`, `RouteSegment`, `RailwayLine`) and the service interfaces (`IDataRepository`, `IRouteService`, `IStationService`) are the stable, pure, high-value surface of the system. They have no UI or I/O dependencies, change slowly and are depended on by everything else, so a regression there is costly and a 100% branch gate is both achievable and worth enforcing. The UI and integration layers are still tested, but they churn faster and involve Qt, network and filesystem concerns that make a blanket 100% gate brittle rather than valuable. The gate is therefore phased: it is locked to the core today and is meant to be widened package by package over time (see "Extending the gate").

The scope is declared in two places that must stay in sync:

`pytest.ini`

```ini
[pytest]
addopts =
    -ra
    --strict-markers
    --cov=src/core/models
    --cov=src/core/interfaces
    --cov-branch
    --cov-report=term-missing
    --cov-fail-under=100
testpaths =
    tests
qt_api = pyside6
```

`.coveragerc`

```ini
[run]
branch = True
source =
    src/core/models
    src/core/interfaces

[report]
fail_under = 100
show_missing = True
skip_covered = False
precision = 2
```

`--cov-branch` (and `branch = True`) means every conditional branch in the scoped packages must be exercised, not just every line.

## Running the suite

Qt tests run headless. `qt_api = pyside6` selects the binding for `pytest-qt`, and the test dependencies (`pytest`, `pytest-qt`, `pytest-xvfb`, `pytest-cov`, `pytest-mock`, `pytest-asyncio`, `pytest-benchmark`) are listed in `requirements.txt`. On Linux CI `pytest-xvfb` provides a virtual display; on Windows (and as a portable default everywhere) set the offscreen Qt platform so no real display is needed:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest
```

Run a single file:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_core_models.py
```

Run without the coverage gate (faster, plain pass/fail count):

```bash
QT_QPA_PLATFORM=offscreen python -m pytest --no-cov
# or disable the cache provider as well:
QT_QPA_PLATFORM=offscreen python -m pytest --no-cov -p no:cacheprovider
```

## Reading the result correctly

When the coverage gate is active (the default), the **coverage table prints last** and there is no `N passed` summary line in the same view directly underneath it. Do not scan for a green "passed" line and conclude failure when you do not see one. **Trust the exit code:**

- exit code `0` = every test passed and the 100% gate was met
- non-zero = a test failed or coverage fell below 100%

If you want a plain pass count instead, run with `--no-cov`, which restores the familiar `N passed in Xs` line and skips the coverage report.

## Test layers and the `tests/` layout

All tests live flat under `tests/` with a single shared `tests/conftest.py`, which only ensures the repository root is on `sys.path` so `import src...` resolves reliably. There are no other fixtures defined there. The files map to these layers:

- **Core model unit tests** (gated to 100%): `test_core_models.py`, `test_astronomy_models.py`.
- **Interface contract tests** (gated to 100%): the `src/core/interfaces` protocols are exercised through the core model tests and contract checks; the `--cov` scope guarantees every branch of `i_data_repository.py`, `i_route_service.py` and `i_station_service.py` is covered.
- **Manager and service tests**: `test_cache_manager.py`, `test_station_cache_manager.py`, `test_disk_cache.py`, `test_memory_cache.py`, `test_moon_phase_service.py`, `test_simple_route_finder.py`, `test_train_manager_fastpath_no_config.py`, `test_combined_forecast_data.py`, `test_weather_data.py`, `test_geo.py`, `test_url_utils.py`, `test_helpers.py`, `test_data_path_resolver.py`, `test_loc_limit.py`.
- **UI tests** (PySide6 via `pytest-qt`, offscreen): `test_astronomy_icons.py`, `test_light_theme_contrast.py`, `test_minimal_segment_ui_compat.py`, `test_startup_splash_invariants.py`, `test_weather_startup_regression.py`.
- **Architecture / invariant guards**: `test_architecture_rules.py`, `test_phase2_boundaries.py`, `test_public_surface_freeze.py`, `test_qt_import_constraints.py`, `test_flatpak_import_invariants.py`.
- **Version single source of truth**: `test_version_single_source_of_truth.py` asserts `__version__` is assigned only in the root `version.py` and that previously hardcoded schema-version literals are not reintroduced.
- **CLI `--version`**: `test_cli_version_flag.py` runs `main.py --version` via `runpy` and asserts it exits cleanly with output starting with `Trainer` without starting Qt or acquiring singleton locks.

## Extending the coverage gate

To bring a new package under the 100% branch gate (the intended phased progression), update both files in lockstep:

1. Add the package to `.coveragerc` `[run] source`:

   ```ini
   [run]
   branch = True
   source =
       src/core/models
       src/core/interfaces
       src/new/package
   ```

2. Add a matching `--cov=` entry to `pytest.ini` `addopts`:

   ```ini
   --cov=src/new/package
   ```

3. Keep the new code fully covered. Because `--cov-fail-under=100` and `branch = True` apply to the whole scope, any uncovered line or branch in the newly added package fails the run. Add tests before (or with) the source change so the gate stays green.

When adding new core code to an already-gated package, write tests for every branch as part of the same change; the gate will fail otherwise.

## Coverage exclusions

`.coveragerc` `[report] exclude_lines` removes lines that should not count against coverage:

```ini
exclude_lines =
    pragma: no cover
    ^\s*raise NotImplementedError\b
    ^\s*if __name__ == ['\"]__main__['\"]:\s*$
```

- `pragma: no cover` excludes any line explicitly marked with that comment.
- `raise NotImplementedError` excludes abstract-method bodies (the interface protocols), which are contracts, not executable behaviour.
- the `if __name__ == "__main__":` guard excludes module entry-point blocks that are not run under test.
