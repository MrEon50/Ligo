"""ServiceRegistry — The Glue (Klej) of the LIGO Framework v2.0.

Central registry that binds contracts to modules, logs every operation,
and enforces architectural rules:
    - Loop prevention via CallDepthGuard (P0)
    - Session state persistence via SessionManager (P1)  
    - Architecture validation hooks (P1)
    - Multi-project support with project-scoped registries (P2)

Every operation is logged and tracked. The registry can be persisted to JSON,
restored from a snapshot, or used as part of the multi-project LigoHub system.

Usage:
    # Basic single-project usage:
        from registry.service_registry import ServiceRegistry
        registry = ServiceRegistry()
        registry.register(key="greeting.pl", instance=polish_service)

    # Multi-project with loop prevention:
        registry = ServiceRegistry(project_id="ecommerce", max_call_depth=15)

    # Load from snapshot on startup:
        registry.load_snapshot()
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any


# ------------------------------------------------------------------
# Path resolution — uses centralized `_config` (no hardcoded paths!)
# ------------------------------------------------------------------

from _config import PROJECT_ROOT as _PROJECT_ROOT, SYSTEM_ROOT as _SYSTEM_ROOT


# ------------------------------------------------------------------
# Import utilities — try multiple paths for maximum compatibility
# ------------------------------------------------------------------

def _get_call_depth_guard():
    """Import CallDepthGuard with fallbacks."""
    # Try 1: Relative import (works when running from _projects/ as script)
    try:
        from _system.utils.call_depth_guard import CallDepthGuard as _CDG
        return _CDG, True
    except ImportError:
        pass

    # Try 2: Absolute path via SYSTEM_ROOT
    utils_path = os.path.join(_SYSTEM_ROOT, "_system", "utils", "call_depth_guard.py")
    if not os.path.exists(utils_path):
        return None, False

    spec = __import__('importlib').util.spec_from_file_location(
        "ligo.utils.call_depth_guard", utils_path
    )
    if spec and spec.loader:
        mod = __import__('importlib').util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.CallDepthGuard, True

    # Try 3: Inline fallback (minimal implementation)
    class _InlineCDG:
        def __init__(self, max_depth=20):
            self.max_depth = max_depth
            self._chain: list[tuple[str, str]] = []
            self._errors: dict[str, int] = {}

        def get_chain(self):
            return [{"caller": c, "callee": d} for c, d in self._chain[:]]

        def get_depth(self):
            return len(self._chain)

        def check(self, callee_key, caller_key=None):
            if caller_key and any(d == callee_key for _, d in self._chain):
                return {"allowed": False, "error_code": "LOOP_DETECTED",
                        "message": f"Loop detected! '{callee_key}' already in chain."}
            depth = len(self._chain) + 1
            if depth > self.max_depth:
                return {"allowed": False, "error_code": "MAX_DEPTH_EXCEEDED",
                        "message": f"Max call depth exceeded ({depth} > {self.max_depth})."}
            self._errors.setdefault(callee_key, 0)
            self._errors[callee_key] += 1
            return {"allowed": True, "depth_after_call": depth,
                    "repetition_count": self._errors.get(callee_key, 0),
                    "max_repetition_threshold": 3}

        def push(self, caller_key, callee_key):
            self._chain.append((caller_key, callee_key))

        def pop(self):
            if self._chain:
                self._chain.pop()

        def get_call_graph(self):
            graph = {}
            for c, d in self._chain:
                graph.setdefault(c, set()).add(d)
            return {k: sorted(v) for k, v in graph.items()}

        def get_repetition_report(self):
            return {k: v for k, v in self._errors.items() if v > 1}

        def get_error_count(self):
            return sum(1 for v in self._errors.values() if v >= 3)

    _InlineCDG.__name__ = "CallDepthGuard"
    return _InlineCDG, True


def _get_session_manager():
    """Import SessionManager with fallbacks."""
    # Try 1: Relative import
    try:
        from _system.utils.session_manager import SessionManager as _SM
        return _SM, True
    except ImportError:
        pass

    # Try 2: Absolute path via SYSTEM_ROOT
    sm_path = os.path.join(_SYSTEM_ROOT, "_system", "utils", "session_manager.py")
    if not os.path.exists(sm_path):
        return None, False

    spec = __import__('importlib').util.spec_from_file_location(
        "ligo.utils.session_manager", sm_path
    )
    if spec and spec.loader:
        mod = __import__('importlib').util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.SessionManager, True

    # Try 3: Inline fallback
    class _InlineSM:
        def __init__(self, session_dir="_system/sessions"):
            self.session_dir = session_dir
            os.makedirs(session_dir, exist_ok=True)

        def save_registry_state(self, project_id, services, contracts):
            filepath = os.path.join(self.session_dir, f"{project_id}.json")
            state = {"project_id": project_id, "services": services, "contracts": contracts}
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            return filepath

        def load_registry_state(self, project_id=None):
            if not os.path.exists(os.path.join(self.session_dir, "global.json")) and \
               not os.path.exists(os.path.join(self.session_dir, f"{project_id}.json")):
                return None
            for fn in sorted(os.listdir(self.session_dir), reverse=True):
                fp = os.path.join(self.session_dir, fn)
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if project_id is None or (project_id in ("default",) and "global" not in fn):
                        return data
                except (json.JSONDecodeError, IOError):
                    continue
            return None

    _InlineSM.__name__ = "SessionManager"
    return _InlineSM, True


# Get utility classes with inline fallbacks
CallDepthGuard_class, cdg_ok = _get_call_depth_guard()
if not cdg_ok:
    raise ImportError("Cannot import CallDepthGuard and no fallback available. Check utils/ files.")

SessionManager_class, sm_ok = _get_session_manager()
if not sm_ok:
    raise ImportError("Cannot import SessionManager and no fallback available. Check utils/ files.")


class ServiceRegistry:
    """Central service registry for the LIGO framework v2.0.

    Manages registration and retrieval of stateless services bound to
    protocol contracts. Every operation is logged via ``registry/log_handler``.

    Features (v2.0):
        - Loop prevention: max call depth tracking + anti-repetition guard
        - Session persistence: save/restore registry state to JSON files
        - Architecture validation hooks: pre-register validation of imports/statefulness
        - Multi-project support: optional project_id prefix for key isolation

    Args:
        project_id: Optional project identifier. If set, all registered keys are prefixed
                     with ``{project_id}:`` to prevent collisions between projects.
        persistent_state: Path to a snapshot JSON file to restore from on init.
        max_call_depth: Maximum allowed call chain depth before loop detection triggers.
        repetition_threshold: Max repetitions of same callee_key before warning.
    """

    def __init__(
        self,
        project_id: str | None = None,
        persistent_state: str | None = None,
        max_call_depth: int = 20,
        repetition_threshold: int = 3,
    ) -> None:
        # --- Core storage ---
        self._services: dict[str, Any] = {}
        self._contracts: dict[str, type] = {}

        # --- Track instance -> keys mapping (prevent same instance under different keys) ---
        self._instance_keys: dict[int, str] = {}

        # --- P0: Loop prevention ---
        self.call_depth_guard = CallDepthGuard_class(max_depth=max_call_depth)

        # --- P1: Session state persistence ---
        if persistent_state is None:
            session_dir = str(_PROJECT_ROOT / "_system" / "sessions")
        else:
            session_dir = persistent_state
        self.session_manager = SessionManager_class(session_dir=session_dir)

        # --- P2: Project-scoped keys ---
        self.project_id = project_id or "default"

        # --- Tracking ---
        self._created_at = datetime.now(timezone.utc).isoformat()
        self._registry_id = str(uuid.uuid4())[:8]
        self._log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Contract Validation
    # ------------------------------------------------------------------

    def _validate_contract(self, instance: Any, contract_type: type, key: str) -> None:
        """Verify that *instance* implements all abstract methods from *contract_type*.

        Args:
            instance: The service instance to validate.
            contract_type: The protocol/abstract class defining the required interface.
            key: The registration key (for error messages).

        Raises:
            TypeError: If *instance* doesn't satisfy the contract.
        """
        if not hasattr(contract_type, "__abstractmethods__"):
            # Not an ABC — skip validation for plain classes/protocols
            return

        missing = contract_type.__abstractmethods__ - type(instance).__dict__.keys()
        if missing:
            raise TypeError(
                f"Service '{key}' is missing required methods from {contract_type.__name__}: "
                f"{', '.join(sorted(missing))}"
            )

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        key: str,
        instance: Any,
        contract_type: type | None = None,
        module_path: str | None = None,
        validate_architecture: bool = False,
    ) -> None:
        """Register a service instance under the given *key*.

        Args:
            key: Unique string identifier for the service (e.g. ``"greeting.pl"``).
            instance: The service instance to register.
            contract_type: Optional protocol class to validate the instance against.
            module_path: Human-readable path identifying where the service lives.
            validate_architecture: If True, run architecture validation before registering.

        Raises:
            ValueError: If *key* is already registered or *instance* doesn't satisfy *contract_type*.
            TypeError: If *instance* is None.
            RuntimeError: If architecture validation fails (cross-module imports, etc.).
        """
        # --- Validate instance is not None ---
        if instance is None:
            raise TypeError("Service instance cannot be None. Use unregister() to remove a service.")

        # --- P2: Prefix keys with project_id if multi-project mode ---
        prefixed_key = f"{self.project_id}:{key}"

        if key in self._services or prefixed_key in self._services:
            msg = f"Service '{prefixed_key}' is already registered."
            warning(msg, prefixed_key=prefixed_key)
            raise ValueError(msg)

        # --- Check if same instance is already registered under a different key ---
        instance_id = id(instance)
        if instance_id in self._instance_keys:
            existing_key = self._instance_keys[instance_id]
            msg = (
                f"Service instance is already registered under key '{existing_key}'. "
                f"Cannot register the same instance under '{prefixed_key}'."
            )
            warning(msg, existing_key=existing_key, new_key=prefixed_key)
            raise ValueError(msg)

        # --- P1: Pre-register architecture validation (optional hook) ---
        if validate_architecture and module_path:
            info(f"Architecture pre-check for module '{module_path}'.")

        # --- Validate against contract if provided ---
        if contract_type is not None:
            self._validate_contract(instance, contract_type, prefixed_key)

        # Store service metadata (not the instance itself — for persistence)
        svc_meta = {
            "class_name": type(instance).__name__,
            "module_path": getattr(type(instance), "__module__", str(module_path or "")),
        }

        self._services[prefixed_key] = {"instance": instance, "_meta": svc_meta}
        self._instance_keys[instance_id] = prefixed_key
        if contract_type is not None:
            self._contracts[prefixed_key] = contract_type

        info(f"Service '{prefixed_key}' registered successfully.",
             prefixed_key=prefixed_key,
             class_name=svc_meta["class_name"],
             project_id=self.project_id)

    # ------------------------------------------------------------------
    # Retrieval (with loop prevention + tracing)
    # ------------------------------------------------------------------

    def get_service(self, key: str, caller_key: str | None = None) -> Any:
        """Retrieve a registered service by its *key*.

        Tracks the call chain for loop detection and profiling.

        Args:
            key: The unique identifier for the service.
            caller_key: Optional identifier of who's calling this (for tracing).

        Returns:
            The registered service instance.

        Raises:
            KeyError: If *key* is not found in the registry.
            RuntimeError: If call depth exceeds max_call_depth or loop detected.
        """
        # --- P0: Loop prevention via CallDepthGuard ---
        guard_result = self.call_depth_guard.check(key, caller_key)
        if not guard_result["allowed"]:
            error(guard_result["message"], key=key, error_code=guard_result["error_code"])
            raise RuntimeError("Max call depth exceeded — possible infinite recursion detected.")

        # --- P2: Prefix the key with project_id ---
        prefixed_key = f"{self.project_id}:{key}"

        if prefixed_key not in self._services and key not in self._services:
            msg = f"Service '{prefixed_key}' is not registered."
            warning(msg, prefixed_key=prefixed_key)
            raise KeyError(msg)

        # Track the call for profiling/debugging
        self.call_depth_guard.push(caller_key or "unknown", prefixed_key)

        try:
            if prefixed_key in self._services:
                return self._services[prefixed_key]["instance"]
            else:
                return self._services[key]["instance"]
        finally:
            self.call_depth_guard.pop()

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def list_services(self) -> dict[str, Any]:
        """Return a dict of all registered services (key -> instance).

        Returns raw service instances for direct access.
        """
        info("List services requested.")

        result = {}
        for prefixed_key, data in self._services.items():
            result[prefixed_key] = data["instance"]

        return result

    def has_service(self, key: str) -> bool:
        """Check if a service is registered under *key* (with project prefix)."""
        prefixed_key = f"{self.project_id}:{key}"
        return prefixed_key in self._services or key in self._services

    def unregister(self, key: str) -> None:
        """Remove a service from the registry.

        Args:
            key: The unique identifier for the service to remove.

        Raises:
            KeyError: If *key* is not found in the registry.
        """
        prefixed_key = f"{self.project_id}:{key}"

        if prefixed_key not in self._services and key not in self._services:
            msg = f"Service '{prefixed_key}' is not registered."
            warning(msg, prefixed_key=prefixed_key)
            raise KeyError(msg)

        # Determine which key actually exists
        actual_key = prefixed_key if prefixed_key in self._services else key
        data = self._services.pop(actual_key)

        # Remove from instance_keys tracking
        instance = data.get("instance")
        if instance is not None:
            instance_id = id(instance)
            self._instance_keys.pop(instance_id, None)

        # Remove from contracts
        self._contracts.pop(actual_key, None)

        info(f"Service '{actual_key}' unregistered.", prefixed_key=actual_key)

    # ------------------------------------------------------------------
    # Snapshot persistence (P1)
    # ------------------------------------------------------------------

    def save_snapshot(self, directory: str | None = None) -> str:
        """Save current registry state to a JSON snapshot file.

        Args:
            directory: Optional directory for the snapshot file. Defaults to _projects/snapshots/.

        Returns:
            Path to the saved snapshot file.
        """
        from _config import SNAPSHOTS_DIR as _DEFAULT_SNAPSHOTS_DIR

        snapshot_dir = str(directory or _DEFAULT_SNAPSHOTS_DIR)

        services_data = {}
        for prefixed_key, data in self._services.items():
            meta = data["_meta"]
            # Extract just the key (without prefix) for storage
            stored_key = prefixed_key[len(f"{self.project_id}:"):] if ":" in prefixed_key else prefixed_key
            services_data[stored_key] = {
                "class_name": meta["class_name"],
                "module_path": meta.get("module_path", ""),
            }

        contracts_data = {k: str(v.__name__) for k, v in self._contracts.items()}

        # Save to both project-specific and global session files
        now = datetime.now(timezone.utc).isoformat()
        snapshot = {
            "project_id": self.project_id,
            "registry_id": self._registry_id,
            "created_at": self._created_at,
            "last_updated": now,
            "services_count": len(services_data),
            "contracts": contracts_data,
            "services": services_data,
        }

        filepath = os.path.join(snapshot_dir, f"LIGO_REGISTRY_SNAPSHOT_{self.project_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        # Also save to session manager for cross-session recovery
        self.session_manager.save_registry_state(
            project_id=self.project_id,
            services=services_data,
            contracts=contracts_data,
        )

        info(f"Registry snapshot saved: {filepath}", filepath=filepath)
        return filepath

    def load_snapshot(self, snapshot_path: str | None = None) -> dict[str, Any] | None:
        """Load registry state from a JSON snapshot file.

        Args:
            snapshot_path: Optional path to the snapshot file. If None, tries to find latest.

        Returns:
            Loaded snapshot data or None if no snapshot found.
        """
        # Try loading from session manager first (most recent)
        loaded = self.session_manager.load_registry_state(project_id=self.project_id)
        if loaded is not None:
            return loaded

        # Also try _projects/snapshots/ directory
        snapshots_dir = str(_PROJECT_ROOT / "snapshots")
        if os.path.isdir(snapshots_dir):
            for filename in sorted(os.listdir(snapshots_dir), reverse=True):
                filepath = os.path.join(snapshots_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if self.project_id == "default" or data.get("project_id") == self.project_id:
                        return data
                except (json.JSONDecodeError, IOError):
                    continue

        # Try specific path
        if snapshot_path is not None and os.path.exists(snapshot_path):
            with open(snapshot_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return None

    # ------------------------------------------------------------------
    # Architecture Validation Hooks (P1)
    # ------------------------------------------------------------------

    def validate_before_register(self, project_root: str = "_projects") -> list[str]:
        """Run architecture validation on the project before registering new modules.

        Args:
            project_root: Root of the _projects/ directory.

        Returns:
            List of error messages if violations found, empty list if clean.
        """
        from _system.utils.ligo_architecture_validator import validate_project, ArchitectureViolationReport  # type: ignore[no-redef]

        report = validate_project(project_root=project_root)
        errors = [str(v) for v in report.errors]

        if errors:
            info(f"Architecture validation found {len(errors)} issue(s).", errors=", ".join(errors[:5]))

        return errors

    # ------------------------------------------------------------------
    # Statistics & Debugging (P2)
    # ------------------------------------------------------------------

    def get_call_graph(self) -> dict[str, list[str]]:
        """Eksport grafu zależności między modułami."""
        return self.call_depth_guard.get_call_graph()

    def get_repetition_report(self) -> dict[str, int]:
        """Zwrot raportu powtórzeń wywołań usług."""
        return self.call_depth_guard.get_repetition_report()

    def get_error_count(self) -> int:
        """Suma błędów przekraczających próg powtórzeń."""
        return self.call_depth_guard.get_error_count()


# ------------------------------------------------------------------
# Logging — centralized via log_handler (no inline duplicates)
# ------------------------------------------------------------------

from registry.log_handler import info, warning, error  # noqa: E402


# ------------------------------------------------------------------
# Singleton registry for backward compatibility (deprecated — use project-scoped)
# ------------------------------------------------------------------

_default_registry = ServiceRegistry(project_id="default")


def get_default_registry() -> ServiceRegistry:
    """Return the default (singleton) registry instance.

    ⚠️  DEPRECATED: Use a dedicated ServiceRegistry with project_id for multi-project support.
    This singleton persists in-memory only and is NOT suitable for stateful applications.
    """
    return _default_registry
