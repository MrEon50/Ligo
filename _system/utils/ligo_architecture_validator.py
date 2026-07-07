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
from pathlib import Path
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
    modules_dir: Path,
    contracts_dir: Path,
) -> ArchitectureViolationReport:
    """Sprawdź czy moduły nie importują się bezpośrednio z innych modułów."""
    report = ArchitectureViolationReport()

    allowed_modules: set[str] = set()
    if contracts_dir.is_dir():
        for filename in contracts_dir.iterdir():
            if filename.suffix == ".py" and not filename.name.startswith("__"):
                allowed_modules.add(filename.stem)

    module_files = [
        (f, f.name) for f in sorted(modules_dir.glob("*.py"))
        if not f.name.startswith("__")
    ]

    for filepath, filename in module_files:
        try:
            source = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Matches: from modules.something import ... or import modules.something
        patterns = [
            re.compile(r"from\s+modules\.\w+\s+import", re.MULTILINE),
            re.compile(r"import\s+modules\."),
        ]

        for pattern in patterns:
            matches = pattern.findall(source)
            for match in matches:
                import_name = extract_imported_module(match, filename)
                if import_name and import_name not in allowed_modules:
                    report.add(ArchitectureViolation(
                        rule_id="NO_CROSS_MODULE_IMPORTS",
                        severity="ERROR",
                        message=(
                            f"Direct import from '{import_name}' detected in {filename}. "
                            f"Użyj Registry lub Orchestrator do komunikacji między modułami."
                        ),
                        file_path=str(filepath),
                    ))

        # Also check for relative imports between modules (from .module import ...)
        rel_imports = re.findall(r"from\s+\.\w+\s+import", source)
        if rel_imports:
            report.add(ArchitectureViolation(
                rule_id="NO_RELATIVE_MODULE_IMPORTS",
                severity="ERROR",
                message=f"Relative module import detected in {filename}: use Registry instead.",
                file_path=str(filepath),
            ))

    return report


def check_statefulness(module_files: list[tuple[Path, str]]) -> ArchitectureViolationReport:
    """Sprawdź czy moduły nie przechowują stanów (self._data, self._cache itp.)."""
    report = ArchitectureViolationReport()

    stateful_patterns = [
        re.compile(r"self\._(?:cache|session|storage|memory|buffer|pool)\s*=", re.MULTILINE),
        re.compile(r"self\.__dict__\.update", re.MULTILINE),
        re.compile(r"setattr\s*\(\s*self\s*,\s*[\"']_(?:data|state|context)[\"']", re.MULTILINE),
        re.compile(r"self\._(?:set|put|add|append)\(", re.MULTILINE),
    ]

    for filepath, filename in module_files:
        try:
            source = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for pattern in stateful_patterns:
            matches = pattern.findall(source)
            if matches:
                report.add(ArchitectureViolation(
                    rule_id="STATEFUL_MODULE_DETECTED",
                    severity="ERROR",
                    message=(
                        f"Potential statefulness detected in {filename}: "
                        + "; ".join(matches[:3])
                    ),
                    file_path=str(filepath),
                ))

    return report


def check_contract_conformance(
    module_files: list[tuple[Path, str]],
    contracts_dir: Path,
) -> ArchitectureViolationReport:
    """Sprawdź czy moduły implementują wymagane metody z protokołów ABC."""
    report = ArchitectureViolationReport()

    # Zbierz wymaganе metody z plików kontraktów (AST analysis for @abstractmethod)
    contract_requirements: dict[str, set[str]] = {}

    if not contracts_dir.is_dir():
        return report

    for contract_file in sorted(contracts_dir.glob("*.py")):
        if contract_file.name.startswith("__"):
            continue

        try:
            tree = ast.parse(contract_file.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        required_methods: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and _is_abstract_class(node):
                # Found an ABC class — collect its abstract methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and _has_abstractmethod_decorator(item):
                        required_methods.add(item.name)

        contract_requirements[contract_file.stem] = required_methods

    # Check each module against contracts
    for filepath, filename in module_files:
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            report.add(ArchitectureViolation(
                rule_id="INVALID_MODULE_SYNTAX",
                severity="ERROR",
                message=f"Syntax error in {filename} — cannot validate.",
                file_path=str(filepath),
            ))
            continue

        # Collect public methods from the module's classes
        class_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and not node.name.startswith("__"):
                class_names.append(node.name)

        for contract_file_name, required_methods in sorted(contract_requirements.items()):
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
                        f"doesn't implement methods from contract '{contract_file_name}.py': "
                        + ", ".join(sorted(missing_methods))
                    ),
                    file_path=str(filepath),
                ))

    return report


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def extract_imported_module(pattern: str, current_file: str) -> str | None:
    """Extract the imported module name from a regex match."""
    parts = pattern.split(".")
    return ".".join(parts[1:]) if len(parts) > 1 else current_file


def _is_abstract_class(class_node: ast.ClassDef) -> bool:
    """Check if a ClassDef is an ABC subclass using AST analysis."""
    # Check base classes for ABC or ABCMeta references
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id in ("ABC", "ABCMeta"):
            return True
        if (isinstance(base, ast.Attribute) and base.attr in ("ABC", "ABCMeta")):
            return True

    # Check for __metaclass__ assignment
    for item in class_node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "__metaclass__":
                    return True

    return False


def _has_abstractmethod_decorator(func_node: ast.FunctionDef) -> bool:
    """Check if a function has @abstractmethod or @abc.abstractmethod decorator."""
    for decorator in func_node.decorator_list:
        # @abstractmethod (bare name)
        if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
            return True
        # @abc.abstractmethod (attribute access)
        if (isinstance(decorator, ast.Attribute) and
            decorator.attr == "abstractmethod" and
            hasattr(getattr(decorator, "value", None), "id") and
            getattr(decorator.value, "id") == "abc"):
            return True

    return False


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def validate_project(root_dir: str | Path = "_projects") -> ArchitectureViolationReport:
    """Uruchom pełną walidację architektury dla projektu.

    Args:
        root_dir: Root katalogu projektu (domyślnie _projects/).

    Returns:
        Raport z naruszeniami (is_clean=True oznacza brak błędów).
    """
    root = Path(root_dir)
    report = ArchitectureViolationReport()

    modules_dir = root / "modules"
    contracts_dir = root / "contracts"

    # 1. Cross-module imports
    cross_module_report = check_cross_module_imports(modules_dir, contracts_dir)
    for violation in cross_module_report.violations:
        report.add(violation)

    # 2. Statefulness
    module_files: list[tuple[Path, str]] = []
    if modules_dir.is_dir():
        for filepath in sorted(modules_dir.glob("*.py")):
            if not filepath.name.startswith("__"):
                module_files.append((filepath, filepath.name))

    statefulness_report = check_statefulness(module_files)
    for violation in statefulness_report.violations:
        report.add(violation)

    # 3. Contract conformance
    contract_report = check_contract_conformance(module_files, contracts_dir)
    for violation in contract_report.violations:
        report.add(violation)

    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent  # _projects/
    report = validate_project(root)
    print(report.summary())

    if not report.is_clean:
        raise SystemExit(1)
