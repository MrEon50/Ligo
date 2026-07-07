"""LIGO Framework — Minimum Viable Glue (MVG) Entry Point v2.0.

Proves the full 4-layer workflow:
    Contract → Module → Registry → Orchestrator

Run this script to verify that LIGO's glue works end-to-end.

v2.0 improvements:
    - Loop prevention via CallDepthGuard in ServiceRegistry
    - Session persistence (JSON snapshots) in ServiceRegistry
    - Architecture validation hooks in ServiceRegistry
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

os_path = __import__("pathlib").Path(__file__).resolve().parent.parent  # _projects/
if os_path not in sys.path:
    sys.path.insert(0, str(os_path))


# ------------------------------------------------------------------
# Path resolution — centralized via `_config` (no hardcoded paths!)
# ------------------------------------------------------------------

from _config import PROJECT_ROOT as _PROJECT_ROOT, SYSTEM_ROOT as _SYSTEM_ROOT

if TYPE_CHECKING:  # noqa: F401 — type checker only, not imported at runtime
    from registry.service_registry import ServiceRegistry


def bootstrap() -> "ServiceRegistry":
    """Initialize and populate the LIGO service registry with all modules."""
    from registry.service_registry import ServiceRegistry
    from contracts.greeting_protocol import GreetingServiceProtocol
    from contracts.ai_params_protocol import AIParametersProtocol
    from modules.polish_greeting import PolishGreetingService
    from modules.english_greeting import EnglishGreetingService
    from modules.ai_params import AIParamsService

    registry = ServiceRegistry()

    # --- Register Polish greeting module ---
    pl_service = PolishGreetingService()
    registry.register(
        key="greeting.pl",
        instance=pl_service,
        contract_type=GreetingServiceProtocol,
        module_path="modules.polish_greeting.PolishGreetingService",
    )

    # --- Register English greeting module ---
    en_service = EnglishGreetingService()
    registry.register(
        key="greeting.en",
        instance=en_service,
        contract_type=GreetingServiceProtocol,
        module_path="modules.english_greeting.EnglishGreetingService",
    )

    # --- Register AI Parameters service ---
    ai_svc = AIParamsService()
    registry.register(
        key="ai_params",
        instance=ai_svc,
        contract_type=AIParametersProtocol,
        module_path="modules.ai_params.AIParamsService",
    )

    return registry


def show_all_greetings(registry: "ServiceRegistry") -> None:
    """Demonstrate calling every registered greeting service via the Registry."""

    services = registry.list_services()
    print("=== LIGO GREETING DEMO ===")
    print(f"Registered services: {len(services)}\n")

    for key, svc_info in sorted(services.items()):
        svc = svc_info.get("_instance", None) or services[key]  # fallback to original dict
        if not hasattr(svc, "greet"):
            continue

        info = getattr(svc, "get_service_info", lambda: {})()
        greeting = getattr(svc, "greet", lambda n, c=None: "")("World", {"hour": 10})

        print(f"-- {key} ({info.get('language', '?')}) --")
        print(f"   Info : {json.dumps(info, ensure_ascii=False)}")
        print(f"   Greet: {greeting}")
        print()


def main() -> None:
    """Entry point — bootstrap LIGO and demo the greeting services."""

    registry = bootstrap()
    show_all_greetings(registry)

    # --- Direct retrieval example (Orchestrator pattern) ---
    pl_svc = registry.get_service("greeting.pl")
    custom_greeting = pl_svc.greet("Ania", {"hour": 3})
    print(f"Custom call via Registry: {custom_greeting}")


if __name__ == "__main__":
    main()
