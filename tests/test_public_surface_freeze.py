from __future__ import annotations

import pkgutil
from pathlib import Path


def _discover_modules(package_root: Path, *, package_prefix: str) -> list[str]:
    """Discover importable module names under a package directory (filesystem only)."""

    if not package_root.exists():
        return []

    modules: list[str] = []
    for mod in pkgutil.walk_packages([str(package_root)], prefix=package_prefix + "."):
        # mod.name is the fully-qualified module name
        modules.append(mod.name)
    return sorted(modules)


def test_public_surface_freeze_core_models_and_interfaces():
    """Freeze the public module surface for core domain packages.

    This is a structural guardrail: changes must be intentional.
    """

    repo_root = Path(__file__).resolve().parents[1]

    core_models = repo_root / "src" / "core" / "models"
    core_interfaces = repo_root / "src" / "core" / "interfaces"

    models_modules = _discover_modules(core_models, package_prefix="src.core.models")
    interfaces_modules = _discover_modules(core_interfaces, package_prefix="src.core.interfaces")

    assert models_modules == [
        "src.core.models.railway_line",
        "src.core.models.route",
        "src.core.models.station",
    ]

    assert interfaces_modules == [
        "src.core.interfaces.i_data_repository",
        "src.core.interfaces.i_route_service",
        "src.core.interfaces.i_station_service",
    ]


def test_public_surface_freeze_services_top_level_modules():
    """Freeze the top-level `src.services` modules.

    We intentionally *do not* snapshot every subpackage (routing has many modules)
    to keep this test stable and actionable.
    """

    repo_root = Path(__file__).resolve().parents[1]
    services_root = repo_root / "src" / "services"

    # Only capture the immediate `.py` files directly under src/services.
    top_level = sorted(p.stem for p in services_root.glob("*.py") if p.name != "__init__.py")

    assert top_level == [
        "astronomy_ui_facade",
        "geocoding_service",
        "moon_phase_service",
    ]

