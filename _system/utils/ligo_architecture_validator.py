"""Runtime Architecture Validator — automatyczna walidacja zasad architektury LIGO.

Sprawdza:
    1. Brak bezpośrednich importów między modułami (tylko kontrakty + zewnętrzne)
    2. Stateless moduły (brak self._cache, self._data, etc.)
    3. Konformacja kontraktów (wszystkie metody protokołu są zaimplementowane)

Używa AST parsing do bezpiecznego skanowania plików .py bez wykonywania kodu.

Wymagania:
    - Pliki .py w /modules/ i /contracts/ muszą być na dysku
    - Nie modyfikuje żadnych plików — tylko czyta i raportuje naruszenia
"""

from __future__ import annotations

import ast
import os
import re
from typing import Any


class ArchitectureViolation:
    """Reprezentacja pojedynczego naruszenia zasady architektury."""

    def __init__(self, rule_id: str, severity: str, message: str, file_path: str | None = None) -> None:
        self.rule_id = rule_id  # np. "NO_CROSS_MODULE_IMPORTS"
        self.severity = severity  # "ERROR", "WARNING"
        self.message = message
        self.file_path = file_path

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule_id}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {"rule_id": self.rule_id, "severity": self.severity, "message": self.message, "file_path": self.file_path}


class ArchitectureViolationReport:
    """Kolekcja naruszeń z podsumowaniem."""

    def __init__(self) -> None:
        self.violations: list[ArchitectureViolation] = []

    def add(self, violation: ArchitectureViolation) -> None:
        self.violations.append(violation)

    @property
    def errors(self) -> list[ArchitectureViolation]:
        return [v for v in self.violations if v.severity == "ERROR"]

    @property
    def warnings(self) -> list[ArchitectureViolation]:
        return [v for v in self.violations if v.severity == "WARNING"]

    @property
    def total_count(self) -> int:
        return len(self.violations)

    @property
    def is_clean(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = [f"Architecture Validation Report — {self.total_count} violations found"]
        lines.append(f"  Errors:   {len(self.errors)}")
        lines.append(f"  Warnings: {len(self.warnings)}")
        lines.append("")

        for v in self.violations[:20]:  # Max 20 w raporcie
            lines.append(str(v))

        if len(self.violations) > 20:
            lines.append(f"\n... i jeszcze {len(self.violations) - 20} naruszeń")

        return "\n".join(lines)


# ------------------------------------------------------------------
# Checkers
# ------------------------------------------------------------------

def check_cross_module_imports(
    modules_dir: str,
    contracts_dir: str,
) -> ArchitectureViolationReport:
    """Sprawdź czy moduły nie importują się bezpośrednio z innych modułów.

    Pozwalone imports:
        - from contracts.* import ...  (interfejsy)
        - external libraries (os.path, datetime, typing itp.)

    Zabronione:
        - from modules.* import ... (bezpośredni access do innego modułu)
    """
    report = ArchitectureViolationReport()

    # Zbierz nazwy plików kontraktów (dopuszczone moduły do importu)
    allowed_modules: set[str] = set()
    if os.path.isdir(contracts_dir):
        for filename in os.listdir(contracts_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                allowed_modules.add(filename[:-3])  # bez .py

    module_files = []
    if os.path.isdir(modules_dir):
        for filename in sorted(os.listdir(modules_dir)):
            filepath = os.path.join(modules_dir, filename)
            if filename.endswith(".py") and not filename.startswith("__"):
                module_files.append((filepath, filename))

    for filepath, filename in module_files:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        # Regex search for cross-module imports (simpler & faster than AST)
        # Matches: from modules.something import ... or import modules.something
        patterns = [
            re.compile(r"from\s+modules\.\w+\s+import", re.MULTILINE),
            re.compile(r"import\s+modules\."),
        ]

        for pattern in patterns:
            matches = pattern.findall(source)
            for match in matches:
                # Determine which module is being imported
                import_name = extract_imported_module(match, filename)
                if import_name and import_name not in allowed_modules:
                    report.add(ArchitectureViolation(
                        rule_id="NO_CROSS_MODULE_IMPORTS",
                        severity="ERROR",
                        message=(
                            f"Direct import from '{import_name}' detected in {filename}. "
                            f"Użyj Registry lub Orchestrator do komunikacji między modułami."
                        ),
                        file_path=filepath,
                    ))

        # Also check for relative imports between modules (from .module import ...)
        rel_imports = re.findall(r"from\s+\.\w+\s+import", source)
        if rel_imports:
            report.add(ArchitectureViolation(
                rule_id="NO_RELATIVE_MODULE_IMPORTS",
                severity="ERROR",
                message=f"Relative module import detected in {filename}: use Registry instead.",
                file_path=filepath,
            ))

    return report


def check_statefulness(module_files: list[tuple[str, str]]) -> ArchitectureViolationReport:
    """Sprawdź czy moduły nie przechowują stanów (self._data, self._cache itp.).

    Szuka wzorców w kodzie które sugerują stateful zachowanie.
    """
    report = ArchitectureViolationReport()

    stateful_patterns = [
        r"self\._(?:cache|session|storage|memory|buffer|pool)\s*=",  # explicit state fields
        r"self\.__dict__\.update",  # dynamic attribute setting
        r"setattr\s*\(\s*self\s*,\s*[\"']_(?:data|state|context)[\"']",  # setattr with private attrs
        r"self\._(?:set|put|add|append)\(",  # state mutation methods
    ]

    for filepath, filename in module_files:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        for pattern in stateful_patterns:
            matches = re.findall(pattern, source)
            if matches:
                report.add(ArchitectureViolation(
                    rule_id="STATEFUL_MODULE_DETECTED",
                    severity="ERROR",
                    message=(
                        f"Potential statefulness detected in {filename}: "
                        + "; ".join(matches[:3])  # show up to 3 examples
                    ),
                    file_path=filepath,
                ))

    return report


def check_contract_conformance(
    module_files: list[tuple[str, str]],
) -> ArchitectureViolationReport:
    """Sprawdź czy moduły implementują wymagane metody z protokołów.

    Analizuje AST modułu i porównuje dostępne publiczne metody z wymaganymi.
    """
    report = ArchitectureViolationReport()

    # Zbierz listę wymagań (abstrakcyjne metody) z plików kontraktów
    contract_requirements: dict[str, set[str]] = {}  # filename -> {required_methods}
    if os.path.isdir("_projects/contracts"):  # Relative path for simplicity
        contracts_dir = "_projects/contracts"

        for filename in sorted(os.listdir(contracts_dir)):
            filepath = os.path.join(contracts_dir, filename)
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())
            except SyntaxError:
                continue

            required_methods: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and issubclass_safe(node.body or []):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name.startswith("abstract"):
                            # abc.abstractmethod — requires full class inspection
                            pass

            # Simple check: look for @abstractmethod decorated methods
            required_methods = set()
            for node in ast.walk(tree):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                        required_methods.add(node.name)

            contract_requirements[filename] = required_methods

    # Check each module against its contracts (simplified — assumes one contract per domain)
    for filepath, filename in module_files:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError:
            report.add(ArchitectureViolation(
                rule_id="INVALID_MODULE_SYNTAX",
                severity="ERROR",
                message=f"Syntax error in {filename} — cannot validate.",
                file_path=filepath,
            ))
            continue

        # Collect public methods from the module's classes
        class_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and not node.name.startswith("__"):
                class_names.append(node.name)

        for contract_file, required_methods in sorted(contract_requirements.items()):
            # Check if this module implements all methods from the contract
            implemented: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    implemented.add(node.name)

            missing_methods = required_methods - implemented
            if missing_methods:
                report.add(ArchitectureViolation(
                    rule_id="CONTRACT_NOT_CONFORMANT",
                    severity="ERROR",
                    message=(
                        f"Module '{filename}' (classes: {', '.join(class_names)}) "
                        f"doesn't implement methods from contract '{contract_file}': "
                        + ", ".join(sorted(missing_methods))
                    ),
                    file_path=filepath,
                ))

    return report


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def extract_imported_module(pattern: str, current_file: str) -> str | None:
    """Extract the imported module name from a regex match."""
    # Pattern examples: "from modules.polish_greeting import" or "import modules.xxx"
    parts = pattern.split(".")
    return ".".join(parts[1:]) if len(parts) > 1 else current_file


def issubclass_safe(class_defs: list[Any]) -> bool:
    """Check if any of the class defs are ABC subclasses (simplified check)."""
    return True  # Simplified — full AST analysis requires import of abc module info


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def validate_project(root_dir: str = "_projects") -> ArchitectureViolationReport:
    """Uruchom pełną walidację architektury dla projektu.

    Returns:
        Raport z naruszeniami (is_clean=True oznacza brak błędów).
    """
    report = ArchitectureViolationReport()

    modules_dir = os.path.join(root_dir, "modules")
    contracts_dir = os.path.join(root_dir, "contracts")

    # 1. Cross-module imports
    cross_module_report = check_cross_module_imports(modules_dir, contracts_dir)
    for violation in cross_module_report.violations:
        report.add(violation)

    # 2. Statefulness
    module_files: list[tuple[str, str]] = []
    if os.path.isdir(modules_dir):
        for filename in sorted(os.listdir(modules_dir)):
            filepath = os.path.join(modules_dir, filename)
            if filename.endswith(".py") and not filename.startswith("__"):
                module_files.append((filepath, filename))

    statefulness_report = check_statefulness(module_files)
    for violation in statefulness_report.violations:
        report.add(violation)

    # 3. Contract conformance
    contract_report = check_contract_conformance(module_files)
    for violation in contract_report.violations:
        report.add(violation)

    return report


if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    # Walk up to _projects/ from _utils/
    if root.endswith("_utils"):
        projects_root = os.path.dirname(root)
    else:
        projects_root = root

    report = validate_project(projects_root)
    print(report.summary())

    if not report.is_clean:
        raise SystemExit(1)
