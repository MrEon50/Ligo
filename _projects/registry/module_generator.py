"""Module Generator for LIGO v2.0 — tworzy spójne moduły zgodnie z protokołem LIGO.

Generator tworzy 2 pliki jednocześnie:
    1. Kontrakt (ABC protocol) w _projects/contracts/<name>_protocol.py
    2. Moduł (stateless implementation) w _projects/modules/<name>.py

Używanie:
    from registry.module_generator import ModuleGenerator
    
    gen = ModuleGenerator()
    result = gen.generate("weather", "WeatherService")
    
    # result = {
    #     "contract_path": "...",
    #     "module_path": "...",
    #     "files_created": 2,
    # }
"""

from __future__ import annotations

import json as _json_module
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class GeneratedModule:
    """Wynik generowania modułu."""
    name: str
    service_class: str
    contract_path: Path
    module_path: Path
    files_created: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "service_class": self.service_class,
            "contract_path": str(self.contract_path),
            "module_path": str(self.module_path),
            "files_created": len(self.files_created),
        }


class ModuleGenerator:
    """Generuje kompletne moduły LIGO v2.0 zgodnie z protokołem Safe-Zone."""

    def __init__(self, project_root: Path | None = None) -> None:
        from _config import PROJECT_ROOT as pr
        if project_root is None:
            self.project_root = pr.parent  # Ligo root (parent of _projects/)
        else:
            self.project_root = Path(project_root).resolve()

    def generate(
        self,
        name: str,
        service_class: str | None = None,
        methods: list[str] | None = None,
    ) -> GeneratedModule:
        """Generuj nowy moduł LIGO (3 pliki naraz).

        Args:
            name: Nazwa modułu w snake_case (np. "weather", "calculator").
            service_class: Nazwa klasy usługi (PascalCase). Domyślnie {name_capitalized}Service.
            methods: Lista nazw metod do wygenerowania w kontrakcie (default: ["get_info"]).

        Returns:
            GeneratedModule z ścieżkami utworzonych plików.
        """
        # Normalize inputs
        if service_class is None:
            base = name.replace("_", " ").title().replace(" ", "")
            # Avoid double "Service" suffix (e.g. weather → WeatherService, not WeatherServiceService)
            service_class = f"{base}Service" if not base.endswith("Service") else base
        
        if methods is None:
            methods = ["get_info"]

        contract_path, module_path = self._create_files(name, service_class, methods)
        files_created = [str(contract_path), str(module_path)]

        return GeneratedModule(
            name=name,
            service_class=service_class,
            contract_path=contract_path,
            module_path=module_path,
            files_created=files_created,
        )

    def _create_files(
        self, name: str, service_class: str, methods: list[str]
    ) -> tuple[Path, Path]:
        """Utwórz kontrakty i moduł zgodnie z szablonem LIGO v2.0."""
        contracts_dir = self.project_root / "_projects" / "contracts"
        modules_dir = self.project_root / "_projects" / "modules"

        # Ensure directories exist
        contracts_dir.mkdir(parents=True, exist_ok=True)
        modules_dir.mkdir(parents=True, exist_ok=True)

        # --- 1. Kontrakt (ABC Protocol) ---
        contract_path = contracts_dir / f"{name}_protocol.py"
        contract_code = self._generate_contract_template(name, service_class, methods)
        contract_path.write_text(contract_code, encoding="utf-8")

        # --- 2. Moduł (Stateless Implementation) ---
        module_path = modules_dir / f"{name}.py"
        module_code = self._generate_module_template(name, service_class, methods)
        module_path.write_text(module_code, encoding="utf-8")

        return contract_path, module_path

    @staticmethod
    def _generate_contract_template(
        name: str, service_class: str, methods: list[str]
    ) -> str:
        """Generuj szablon kontraktu ABC."""
        method_defs = []
        for m in methods:
            # Keep snake_case — consistent with Python conventions
            method_defs.append(f"    @abc.abstractmethod\n    def {m}(self, *args: Any, **kwargs: Any) -> Any:\n        \"\"\"{m} — implementacja w module.\"\"\"\n        ...\n")

        # Build a docstring based on the service class name
        title = " ".join(w.capitalize() for w in service_class.replace("Service", "").split("_"))

        return f'''"""{title} Protocol — ABC kontrakt dla {service_class}.

Ten plik definiuje interfejs (ABSTRACT BASE CLASS), który implementacje muszą spełnić.
Moduły w _projects/modules/ implementują ten protokół jako stanless usługi.

Użycie:
    from contracts.{name}_protocol import {service_class}Protocol
    
    @dataclass
    class MyService({service_class}Protocol):
        def get_info(self, *args, **kwargs) -> Any:
            return {{...}}
"""

from __future__ import annotations

import abc
from typing import Any


class {service_class}Protocol(abc.ABC):
    """Abstract base class defining the interface for {service_class}.

    All methods must be implemented by concrete service classes.
    The protocol ensures type-safety and architecture compliance.
    """{chr(10)}{"".join(method_defs)}'''

    @staticmethod
    def _generate_module_template(
        name: str, service_class: str, methods: list[str]
    ) -> str:
        """Generuj szablon stateless modułu implementującego kontrakt."""
        title = " ".join(w.capitalize() for w in service_class.replace("Service", "").split("_"))
        _methods_json = _json_module.dumps(methods)

        # Generate stub implementations for all user-specified methods (skip get_info + __call__)
        _extra_methods = ""
        for m in methods:
            if m in ("get_info", "__call__"):
                continue  # get_info is the main method, __call__ is handled below
            _extra_methods += f'\n    def {m}(self, *args: Any, **kwargs: Any) -> Any:\n        """TODO — implementuj w module."""\n        return None\n'

        # Use ''' docstring inside the f-string (avoids conflict with """ outer quotes)
        return f'''"""{title} Service — stateless implementation of {service_class}Protocol.

Ten moduł jest stanless (nie przechowuje stanu między wywołaniami).
Każde wywołanie zwraca wynik oparty wyłącznie na parametrach wejściowych.

Użycie:
    from registry.service_registry import ServiceRegistry
    
    registry = ServiceRegistry()
    registry.register(
        key="{name}",
        instance={service_class}(),
        contract_type={service_class}Protocol,  # if imported
    )
"""

from __future__ import annotations

import json
from typing import Any

# Import the protocol from the contracts package (relative to _projects root)
try:
    from contracts.{name}_protocol import {service_class}Protocol
except ImportError:
    import abc
    class {service_class}Protocol(abc.ABC):
        pass  # Fallback for standalone execution without full project setup


class {service_class}({service_class}Protocol):
    """Stateless service implementing {service_class}Protocol.

    No instance attributes are stored between method calls.
    All operations are deterministic given the same input.
    """

    VERSION = "1.0.0"
    
    def get_info(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Zwraca metadane usługi."""
        return {{
            "service_name": "{service_class}",
            "language": "{name[:2]}",  # ISO 639-1 (auto-detect from name)
            "version": self.VERSION,
            "description": "{title} service",
            "methods": {_methods_json},
        }}{_extra_methods}

    def __call__(self, *args: Any, **kwargs: Any) -> str | None:
        """Wywołanie usługi — implementacja domyślna."""
        # Placeholder — override in subclasses if needed
        return "{{svc}}: called with {{nargs}} args, {{nkwargs}} kwargs".format(
            svc=self.__class__.__name__, nargs=len(args), nkwargs=len(kwargs)
        )
'''


if __name__ == "__main__":
    gen = ModuleGenerator()
    
    # Demo: generate a weather service
    result = gen.generate(
        name="weather",
        service_class="WeatherService",
        methods=["get_info", "forecast"],
    )
    
    print(f"Generated module: {result.name}")
    print(f"Contract: {result.contract_path}")
    print(f"Module: {result.module_path}")
