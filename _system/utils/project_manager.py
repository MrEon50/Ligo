"""LIGO Framework v2.0 — Multi-Project Bootstrapper.

Auto-discovery i bootstrapping projektów z podfolderu `projects/<project_id>/`.
Każdy projekt ma własną instance ServiceRegistry, kontrakty, moduły i snapshoty.

Użycie:
    # Uruchomienie domyślnego projektu (bez podfolderów):
        python orchestrator/main.py

    # Bootstrapping konkretnego projektu z projects/:
        python _system/utils/project_manager.py --demo project_alpha

    # Lista dostępnych projektów:
        python -c "from utils.project_manager import list_projects; print(list_projects())"
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any


# Ensure _projects/ is on sys.path for relative imports (run from Ligo root)
LIGO_ROOT = os.path.dirname(os.path.abspath(__file__))  # .../_projects or wherever this lives
if not os.path.isabs(LIGO_ROOT):
    LIGO_ROOT = os.path.join(os.getcwd(), LIGO_ROOT)

# If we're running from _projects/ (project root), that's fine for relative imports.
# But if service_registry.py is importing from utils/, it needs PROJECT_ROOT on sys.path.
sys.path.insert(0, LIGO_ROOT)


from registry.service_registry import ServiceRegistry, info  # type: ignore[no-redef]


# ------------------------------------------------------------------
# Project Discovery & Registration
# ------------------------------------------------------------------

DEFAULT_PROJECTS_DIR = "projects"


class LigoHub:
    """Centralny hub zarządzający wieloma projektami LIGO v2.0.

    Każdy projekt ma własną instance ServiceRegistry z unikalnym prefixem kluczy.
    Struktura folderów (v2.0):

        Ligo/
            ├── _system/                    # Konstytucja LIGO (read-only)
            │   └── sessions/               # JSON snapshoty sesji
            ├── _hub/                       # Centrum komend
            ├── _projects/                  # Framework LIGO (silnik)
            │   ├── bootstrap.py            # Auto-discovery i start projektu
            │   ├── projects/               # 🚀 WSPÓLNY katalog projektów!
            │   │   ├── project_alpha/      # ← podfolder = projekt
            │   │   │   ├── contracts/
            │   │   │   ├── modules/
            │   │   │   └── orchestrator/
            │   │   └── project_beta/
            │   │       ├── contracts/
            │   │       └── modules/
            │   ├── registry/               # Core ServiceRegistry (v2.0)
            │   ├── _utils/                 # Narzędzia frameworkowe
            │   ├── snapshots/              # Snapshoty rejestratorów (JSON)
            │   └── tests/                  # Testy frameworkowe
            │
            └── scratchpad.md               # Eksperymenty LIGO (nie projektu)

    Użycie:
        hub = LigoHub()
        project_info = hub.register_project("mvg", root_dir=".")
        registry = hub.activate_project("mvg")
    """

    def __init__(self, projects_dir: str | None = None) -> None:
        self.projects_dir = projects_dir or DEFAULT_PROJECTS_DIR
        self._registries: dict[str, ServiceRegistry] = {}
        self._active_project: str | None = None
        self._project_metadata: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Project Registration
    # ------------------------------------------------------------------

    def register_project(
        self,
        project_id: str,
        root_dir: str = ".",
        create_registry: bool = True,
    ) -> tuple[ServiceRegistry, dict[str, Any]]:
        """Zarejestruj nowy projekt z jego własnym ServiceRegistry.

        Args:
            project_id: Unikalny identyfikator projektu (np. "mvg", "ecommerce").
            root_dir: Root katalogu Ligo.
            create_registry: Utwórz nową instance ServiceRegistry dla tego projektu.

        Returns:
            Tuple (registry_instance, metadata_dict).

        Raises:
            FileNotFoundError: If project directory does not exist and auto-discover fails.
        """
        project_path = os.path.join(root_dir, self.projects_dir, project_id)

        if os.path.isdir(project_path):
            info(f"Project '{project_id}' registered at {project_path}")
        else:
            info(f"Project '{project_id}' directory not found at {project_path}. "
                 f"AUTO-DISCOVERY MODE.")

        # Create registry for this project (multi-project isolation)
        registry = ServiceRegistry(project_id=project_id) if create_registry else {}  # type: ignore[assignment]

        metadata = {
            "id": project_id,
            "path": project_path,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "registry_project_id": project_id,
        }

        self._registries[project_id] = registry
        if self._active_project is None:
            self._active_project = project_id

        # Save to global projects registry (JSON)
        self._save_projects_registry(root_dir=root_dir)

        return registry, metadata

    def activate_project(self, project_id: str) -> ServiceRegistry | None:
        """Przełącz na aktywny projekt. Zwraca jego ServiceRegistry."""
        if project_id not in self._registries:
            raise ValueError(f"Project '{project_id}' not registered.")
        self._active_project = project_id
        return self._registries[project_id]

    # ------------------------------------------------------------------
    # Project Queries
    # ------------------------------------------------------------------

    @property
    def active_registry(self) -> ServiceRegistry | None:
        """Registry aktualnie aktywnego projektu."""
        if self._active_project is None:
            return None
        return self._registries[self._active_project]

    @property
    def active_project_id(self) -> str | None:
        """ID aktualnie aktywnego projektu."""
        return self._active_project

    def list_projects(
        self,
        root_dir: str = ".",
        include_metadata: bool = True,
    ) -> list[dict[str, Any]]:
        """Lista dostępnych projektów (zarządzanych + auto-discovered)."""
        projects = []

        # List managed projects from hub
        for project_id in sorted(self._registries.keys()):
            reg = self._registries[project_id]
            entry = {"id": project_id}
            if include_metadata:
                meta = self._project_metadata.get(project_id, {})
                entry.update({k: v for k, v in meta.items() if "path" not in k})

            # Try to auto-discover services from the folder
            project_path = os.path.join(root_dir, self.projects_dir, project_id)
            if os.path.isdir(project_path):
                contracts_count = sum(1 for f in os.listdir(
                    os.path.join(project_path, "contracts")
                ) if f.endswith(".py") and not f.startswith("__")) if os.path.isdir(
                    os.path.join(project_path, "contracts")
                ) else 0

                modules_count = sum(1 for f in os.listdir(
                    os.path.join(project_path, "modules")
                ) if f.endswith(".py") and not f.startswith("__")) if os.path.isdir(
                    os.path.join(project_path, "modules")
                ) else 0

                entry["contracts"] = contracts_count
                entry["modules"] = modules_count

            projects.append(entry)

        return projects

    def get_project_path(self, project_id: str) -> str | None:
        """Zwrot ścieżki do projektu lub None."""
        base = os.path.dirname(os.path.abspath(__file__))  # _projects/ or wherever this lives
        projects_dir = os.path.join(base, "..", self.projects_dir)
        return os.path.join(projects_dir, project_id)

    def _save_projects_registry(self, root_dir: str = ".") -> None:
        """Zapisz meta-dane wszystkich projektów do JSON."""
        session_dir = os.path.join(root_dir, "_system", "sessions")
        filepath = os.path.join(session_dir, "projects_registry.json")

        projects_data = {
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "projects": [],
        }

        for project_id in self._registries:
            meta = self._project_metadata.get(project_id, {})
            projects_data["projects"].append({
                "id": project_id,
                "registered_at": meta.get("registered_at"),
                "metadata": {k: v for k, v in meta.items() if k != "path"},
            })

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(projects_data, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------
# Auto-discovery of projects from folder structure
# ------------------------------------------------------------------

def discover_projects(root_dir: str = ".") -> list[str]:
    """Auto-discover project folders in Ligo/projects/.

    Returns list of project_id strings found.
    """
    projects_path = os.path.join(root_dir, DEFAULT_PROJECTS_DIR)
    if not os.path.isdir(projects_path):
        return []

    projects: list[str] = []
    for entry in sorted(os.listdir(projects_path)):
        entry_path = os.path.join(projects_path, entry)
        # Valid project folder: contains contracts/, modules/ (at minimum one)
        has_contracts = os.path.isdir(os.path.join(entry_path, "contracts"))
        has_modules = os.path.isdir(os.path.join(entry_path, "modules"))

        if has_contracts or has_modules:
            projects.append(entry)

    return projects


def bootstrap_project(
    project_id: str | None = None,
    root_dir: str = ".",
) -> ServiceRegistry:
    """Bootstrapping domyślnego projektu (bez podfolderów).

    Zwraca instance ServiceRegistry gotową do rejestracji usług.
    """
    from utils.call_depth_guard import CallDepthGuard  # type: ignore[no-redef]

    registry = ServiceRegistry()
    return registry


def bootstrap_ligo(
    project_id: str | None = None,
    root_dir: str = ".",
) -> tuple[LigoHub, ServiceRegistry]:
    """Bootstrapping z auto-discovery i hub.

    Args:
        project_id: Konkretny projekt do uruchomienia (opcjonalnie).
                    Jeśli None — uruchamia pierwszy dostępny projekt.
        root_dir: Root katalogu Ligo.

    Returns:
        Tuple (hub, registry_instance).
    """
    from utils.call_depth_guard import CallDepthGuard  # type: ignore[no-redef]

    hub = LigoHub()

    # Auto-discover projects
    available_projects = discover_projects(root_dir=root_dir)

    if project_id is not None:
        # Try explicit project registration
        try:
            return hub.register_project(project_id, root_dir=root_dir), \
                   ServiceRegistry(project_id=project_id)  # type: ignore[return-value]
        except (FileNotFoundError, ValueError):
            pass

    if not available_projects:
        info("No projects found. Use register_project() to create one.")
        return hub, ServiceRegistry()  # type: ignore[return-value]

    # Pick first project as default
    active_id = available_projects[0]
    info(f"Bootstrapping project '{active_id}' (auto-discovered).")
    return hub.register_project(active_id, root_dir=root_dir), \
           ServiceRegistry(project_id=active_id)  # type: ignore[return-value]


# ------------------------------------------------------------------
# Convenience functions
# ------------------------------------------------------------------

def list_projects(root_dir: str = ".") -> list[str]:
    """Zwrot listy ID dostępnych projektów."""
    return discover_projects(root_dir=root_dir)


if __name__ == "__main__":
    # Quick demo / CLI tool
    import argparse

    parser = argparse.ArgumentParser(description="LIGO v2.0 Multi-Project Bootstrapper")
    parser.add_argument("project_id", nargs="?", default=None, help="Project ID to bootstrap")
    args = parser.parse_args()

    root_dir = os.path.dirname(os.path.abspath(__file__))  # _projects/ or wherever this lives

    hub = LigoHub()
    registry, metadata = hub.register_project(args.project_id or "mvg", root_dir=root_dir)

    print(f"\n=== LIGO v2.0 Multi-Project Bootstrapper ===")
    print(f"Active project: {hub.active_project_id}")
    print(f"Available projects: {[p['id'] for p in hub.list_projects(root_dir=root_dir)]}")
    print(f"Registry: {registry.project_id}:{registry.list_services()}")
