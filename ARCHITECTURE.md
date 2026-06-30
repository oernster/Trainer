# Trainer Architecture

Invariants-first overview of how Trainer is structured. For the build and development
workflow see [DEVELOPMENT-README.md](DEVELOPMENT-README.md), for testing see
[TESTING.md](TESTING.md), and for component deep-dives see the documents under `docs/`
(architecture, ui-architecture, service-architecture, data-flow, design-patterns,
api-integration, widget-system).

Trainer is a PySide6 desktop application that shows UK train times with integrated
weather and astronomy data. It follows a layered design with a stable, pure core at the
centre and the user interface, the external APIs and the local data at the edges.

## Invariants

1. **The core is the stable centre and is purity-gated.** `src/core/models` (the domain
   value objects: railway lines, routes and stations) and `src/core/interfaces` (the
   service and repository contracts) carry no UI, no I/O and no framework imports. This is
   the only surface under a hard 100% branch-coverage gate. Enforced by `pytest.ini`
   (`--cov=src/core/models --cov=src/core/interfaces --cov-branch --cov-fail-under=100`)
   and `.coveragerc`.
2. **Dependencies point inward.** The UI depends on the managers and services; the
   managers and services depend on the core interfaces; the core models and interfaces
   depend on nothing else in the application. The API, data and cache layers sit at the
   edge and are reached through the interfaces, never imported by the core.
3. **Packaged-vs-development paths are isolated behind resolvers.** Code never assumes a
   filesystem layout. `src/utils/data_path_resolver.py` locates the offline railway data
   and `src/utils/icon_resolver.py` locates the icon assets, each across development, a
   Nuitka standalone build, a PyInstaller-style frozen build, a macOS app bundle and a
   Flatpak. New code that needs a bundled resource goes through a resolver.
4. **The version is single-sourced.** `version.py` (`__version__`, `__version_info__`)
   drives the application, the packaging metadata and the `--version` CLI output. Nothing
   else hardcodes a version. Enforced by `tests/test_version_single_source_of_truth.py`.
5. **One master icon drives every platform.** All icon assets derive from `trainer.png`
   via `generate_icons.py`. The UI loads the real icon file through the resolver and never
   paints an emoji glyph for the window or About icon.

## Components

- **`src/core/models`** the immutable domain objects (railway line, route, station). Pure
  Python, no framework, no I/O. The high-value, fully-gated surface.
- **`src/core/interfaces`** the abstract contracts (data repository, route service,
  station service) that the rest of the app depends on. Also fully gated.
- **`src/managers`** orchestration and application services: theme management, the service
  layer wiring, formatters and the station-database components. Depends on the core
  interfaces, not on concrete UI.
- **`src/services`** concrete service implementations including route finding. Implements
  the core interfaces.
- **`src/api`** clients for the external providers (train times, the Open-Meteo weather
  API and the hybrid moon-phase astronomy service). Edge layer, reached via interfaces.
- **`src/data`** the bundled offline railway data, including `lines/` line definitions.
  Located at runtime through the data resolver.
- **`src/cache`** local caching of fetched and computed data.
- **`src/workers`** background workers that perform network and IO-bound work off the UI
  thread.
- **`src/ui`** the PySide6 presentation layer (the main window and its components, dialogs,
  widgets, formatters, handlers and UI-side managers). A client of the services. Must not
  be imported by the core, the services or the managers.
- **`src/utils`** cross-cutting helpers, notably the data and icon path resolvers.
- **`main.py`** the composition root and entry point.

## Dependency direction

```
            ui  ->  managers / services  ->  core/interfaces  <-  core/models
                          |                        ^
                          v                        |
                   api / data / cache / workers ---+
```

`core/models` and `core/interfaces` import nothing else in the app. The UI sits at the
top and is never depended upon. The API, data, cache and worker layers are concrete edge
components reached through the interfaces.

## Execution flow

1. `main.py` handles the ultra-early `--version` flag (it prints the version and exits
   without starting Qt or acquiring the single-instance lock), sets up logging, then
   resolves the offline data directory through `src/utils/data_path_resolver.py` (logged
   early because a missing data directory is the usual cause of empty station lists in a
   packaged build).
2. The single-instance application is created, the window icon is set from the resolved
   icon file, and the main window is constructed.
3. The UI requests data through the service interfaces. Services use the API clients and
   the local data, with the cache in front, and run network work on the workers so the UI
   thread stays responsive.
4. The theme manager applies the dark or light palette; dialogs and the About screen load
   the real application icon through the icon resolver.

## Packaging and delivery

All platform assets derive from one master icon and a single version source. See
[DEVELOPMENT-README.md](DEVELOPMENT-README.md) for the commands.

- **Icons:** `generate_icons.py` turns `trainer.png` into the full PNG set, the multi-size
  Windows `trainer.ico` and the macOS `trainer.icns`.
- **Windows:** `buildexe.py` builds a Nuitka standalone bundle into
  `installer/payload/Trainer/`; `buildinstaller.py` wraps it as a bespoke per-user GUI
  installer (`dist-installer/TrainerSetup.exe`) themed in the application's Material blue,
  installing without administrator rights and registering a normal uninstall entry.
- **Linux:** `build_flatpak.sh` generates its own manifest, launcher and metadata and
  builds `trainer.flatpak` on the KDE 6.8 runtime, running the app from source;
  `clean_flatpak.sh` uninstalls and removes the build artefacts.
- **macOS:** `builddmg.py` builds a self-contained Nuitka `.app` (the interpreter and the
  UI toolkit are frozen in) and produces `trainer-macos-arm64.dmg`, signing and notarising
  when credentials are supplied.

## Design decisions

| Decision | Why |
|---|---|
| A pure core with a scoped 100% branch gate | The domain models and contracts are the stable, high-value surface; gating them fully catches regressions where they matter, without forcing brittle 100% coverage on the fast-moving UI and integration layers. |
| Resolver modules for packaged-vs-dev paths | Path layout differs across source, Nuitka, PyInstaller and Flatpak; isolating that logic keeps the rest of the code layout-agnostic and makes packaged-build failures diagnosable. |
| Single-master icon pipeline | One master image plus one generator removes drift between platforms and gives one place to update the artwork. |
| Per-user, no-admin Windows installer | Lets users install without elevation while still registering a normal uninstall entry and shortcuts. |
| Run-from-source Flatpak | Keeps the Linux build simple and transparent: the app runs `main.py` from the staged source against pip-installed dependencies in the Flatpak prefix. |
| Single version source in `version.py` | Prevents version drift across the runtime, the packaging metadata and the docs; enforced by a test. |

## Quality enforcement

- The 100% branch-coverage gate on the core (`pytest.ini`, `.coveragerc`).
- The version single-source-of-truth test and the `--version` CLI test.
- Coverage exclusions are limited to `pragma: no cover`, `raise NotImplementedError` and
  the `__main__` guard (`.coveragerc`).
- See [TESTING.md](TESTING.md) for how to run the suite and extend the gate.
