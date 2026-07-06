"""Dependency Graph — skanuje importy i buduje graf zależności między modułami.

Analizuje wszystkie pliki `.py` w projekcie i buduje pełny graf zależności:
    - Kto kogo importuje (caller → callee)
    - Jakie metody/funkcje są używane z danego modułu
    - Bezpieczeństwo modyfikacji (co się złamie jeśli zmienię ten plik?)

Użyj:
    graph = DependencyGraph(project_root="_projects")
    graph.scan_project()
    
    # Sprawdź czy modyfikacja jest bezpieczna
    result = graph.check_safety("modules/polish_greeting.py")
    if not result["safe"]:
        print(f"⚠️  Zmiany zepsują: {result['dependents']}")
"""

from __future__ import annotations

import ast
import os
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ModuleInfo:
    """Informacje o pojedynczym module w projekcie."""

    file_path: str
    relative_path: str  # względem project_root (np. "modules/polish_greeting.py")
    imports: list[str] = field(default_factory=list)  # importowane moduły
    imported_names: dict[str, list[str]] = field(default_factory=dict)  # {module: [names]}
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)


@dataclass
class DependencyCheckResult:
    """Wynik sprawdzenia bezpieczeństwa modyfikacji."""

    safe: bool
    dependents: list[str] = field(default_factory=list)  # moduły zależne od danego pliku
    missing_methods: dict[str, list[str]] = field(default_factory=dict)  # {dependent_module: [missing_methods]}


class DependencyGraph:
    """Buduje graf zależności między modułami Pythona w projekcie.

    Skanuje wszystkie pliki `.py`, wyodrębnia importy i buduje pełny graf
    zależności służący do:
        - Analizy wpływu zmian (what breaks if I change this file?)
        - Wykrywania cykli (infinite recursion risks)
        - Dokumentacji architektury projektu
    """

    def __init__(self, project_root: str = "_projects") -> None:
        self.project_root = Path(project_root).resolve()
        self.modules: dict[str, ModuleInfo] = {}  # {relative_path: ModuleInfo}
        self.dependency_graph: dict[str, set[str]] = defaultdict(set)  # {caller: {callees}}

    # ------------------------------------------------------------------
    # Scanning & Building
    # ------------------------------------------------------------------

    def scan_project(self) -> None:
        """Skanuj wszystkie pliki `.py` w projekcie i zbuduj graf zależności."""
        self.modules.clear()
        self.dependency_graph.clear()

        py_files = list(self.project_root.rglob("*.py"))

        for py_file in py_files:
            # Pomijamy katalogi systemowe (venv, .git, __pycache__)
            if any(part.startswith(".") or part == "__pycache__" for part in py_file.relative_to(self.project_root).parts):
                continue

            module_info = self._parse_python_file(py_file)
            if module_info:
                self.modules[module_info.relative_path] = module_info

        # Zbuduj graf zależności na podstawie zaimportowanych modułów
        self._build_dependency_graph()

    def _parse_python_file(self, file_path: Path) -> ModuleInfo | None:
        """Wyeksportuj importy i strukturę z pliku Pythona."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            return None

        relative_path = str(file_path.relative_to(self.project_root)).replace(os.sep, "/")

        imports: list[str] = []
        imported_names: dict[str, list[str]] = defaultdict(list)
        classes: list[str] = []
        functions: list[str] = []

        for node in ast.walk(tree):
            # Zbieraj importy (import X, from X import Y)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    imports.append(module_name)
                    imported_names[module_name].append(alias.asname or alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module
                    imports.append(module_name)
                    names = [alias.name for alias in node.names]
                    imported_names[module_name].extend(names)

            # Zbieraj definicje klas i funkcji
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)

        return ModuleInfo(
            file_path=str(file_path),
            relative_path=relative_path,
            imports=imports,
            imported_names=dict(imported_names),
            classes=classes,
            functions=functions,
        )

    def _build_dependency_graph(self) -> None:
        """Zbuduj graf zależności na podstawie zaimportowanych modułów."""
        # Mapowanie nazw importowanych modułów (dot-separated) do ich relative_path
        module_name_to_path: dict[str, str] = {}
        for rel_path in self.modules.keys():
            # Zamień "modules/polish_greeting.py" na "modules.polish_greeting"
            name_without_ext = os.path.splitext(rel_path)[0].replace(os.sep, ".").replace("/", ".")
            module_name_to_path[name_without_ext] = rel_path

        for rel_path, module_info in self.modules.items():
            for imported_module in module_info.imports:
                # Znajdź odpowiadający moduł w projekcie
                if imported_module in module_name_to_path:
                    target_path = module_name_to_path[imported_module]
                    self.dependency_graph[target_path].add(rel_path)

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_all_modules(self) -> list[str]:
        """Zwrot listy wszystkich zaadresowanych modułów."""
        return sorted(self.modules.keys())

    def get_module_info(self, relative_path: str) -> ModuleInfo | None:
        """Pobierz informacje o konkretnym module."""
        normalized = relative_path.replace(os.sep, "/")
        return self.modules.get(normalized)

    def get_imports_of(self, relative_path: str) -> list[str]:
        """Zwrot listy modułów importowanych przez dany plik."""
        info = self.get_module_info(relative_path)
        if info is None:
            return []
        return list(info.imports)

    def get_dependents(self, relative_path: str) -> set[str]:
        """Zwrot modułów które importują dany plik (zależne od niego)."""
        normalized = relative_path.replace(os.sep, "/")
        return self.dependency_graph.get(normalized, set())

    def get_call_chain(self, start_module: str) -> list[str]:
        """Zwrot pełnej ścieżki zależności (DFS) zaczynając od danego modułu."""
        normalized = start_module.replace(os.sep, "/")
        visited: set[str] = set()
        chain: list[str] = []

        def _dfs(current: str):
            if current in visited:
                return
            visited.add(current)
            chain.append(current)

            for dependent in self.get_dependents(current):
                _dfs(dependent)

        _dfs(normalized)
        return chain

    def detect_cycles(self) -> list[list[str]]:
        """Wykryj cykle w grafie zależności (potencjalne nieskończone rekurencje)."""
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def _dfs(current: str, path: list[str]):
            if current in rec_stack:
                # Znaleziono cykl — zapisz go
                cycle_start = path.index(current)
                cycles.append(path[cycle_start:] + [current])
                return

            visited.add(current)
            rec_stack.add(current)
            path.append(current)

            for dependent in self.get_dependents(current):
                _dfs(dependent, path.copy())

            rec_stack.discard(current)

        for module in self.modules.keys():
            if module not in visited:
                _dfs(module.replace(os.sep, "/"), [])

        return cycles

    # ------------------------------------------------------------------
    # Safety Checks (Meta-Cycling Feature B)
    # ------------------------------------------------------------------

    def check_safety(self, file_to_modify: str) -> DependencyCheckResult:
        """Sprawdź czy modyfikacja danego pliku jest bezpieczna.

        Analizuje wszystkie moduły zależne i sprawdza czy zmiana nie zepsuje
        ich kontraktów (brakujące metody, zmienne klasy).

        Args:
            file_to_modify: Ścieżka względem projektu do zmodyfikowania.

        Returns:
            DependencyCheckResult z informacją o bezpieczeństwie i ewentualnych problemach.
        """
        normalized = file_to_modify.replace(os.sep, "/")
        dependents = self.get_dependents(normalized)

        if not dependents:
            return DependencyCheckResult(safe=True)

        # Analizuj kontrakty zależnych modułów
        missing_methods: dict[str, list[str]] = {}

        for dependent in dependents:
            dep_info = self.get_module_info(dependent)
            if dep_info is None:
                continue

            # Sprawdź czy moduł importuje coś z modyfikowanego pliku
            imported_names = dep_info.imported_names.get(
                os.path.splitext(normalized)[0].replace(os.sep, "."), []
            )

            # Jeśli importuje klasy/funkcje — sprawdź ich obecność w modyfikowanym module
            target_info = self.get_module_info(normalized)
            if target_info:
                for name in imported_names:
                    missing = False

                    # Sprawdzaj klasy
                    if name not in target_info.classes and name not in target_info.functions:
                        # Sprawdź czy to może być atrybut klasy (Class.method)
                        if "." in name:
                            class_name, method_name = name.split(".", 1)
                            if class_name not in target_info.classes:
                                missing_methods.setdefault(dependent, []).append(name)
                        else:
                            missing_methods.setdefault(dependent, []).append(name)

        is_safe = len(missing_methods) == 0
        return DependencyCheckResult(
            safe=is_safe,
            dependents=list(dependents),
            missing_methods=missing_methods,
        )

    # ------------------------------------------------------------------
    # Visualization & Export
    # ------------------------------------------------------------------

    def export_dependency_dict(self) -> dict[str, list[str]]:
        """Eksport grafu zależności jako słownik."""
        return {k: sorted(v) for k, v in self.dependency_graph.items()}

    def get_architecture_summary(self) -> dict[str, Any]:
        """Podsumowanie architektury projektu."""
        module_count = len(self.modules)
        dependency_pairs = sum(len(deps) for deps in self.dependency_graph.values())
        cycles = self.detect_cycles()

        # Najbardziej zależne moduły (najczęściej importowane przez innych)
        most_depended_on = sorted(
            self.dependency_graph.items(), key=lambda x: len(x[1]), reverse=True
        )[:5]

        return {
            "total_modules": module_count,
            "dependency_pairs": dependency_pairs,
            "cycles_detected": len(cycles),
            "most_depended_on": [
                {"module": mod, "dependents_count": len(deps)}
                for mod, deps in most_depended_on
            ],
        }


if __name__ == "__main__":
    graph = DependencyGraph(project_root="_projects")
    graph.scan_project()

    print("=== Architecture Summary ===")
    summary = graph.get_architecture_summary()
    print(f"Modules: {summary['total_modules']}")
    print(f"Dependencies: {summary['dependency_pairs']}")
    if summary["cycles_detected"]:
        print(f"⚠️  Cycles found: {summary['cycles_detected']}")

    print("\n=== Most Depended On ===")
    for item in summary["most_depended_on"]:
        print(f"  {item['module']}: {item['dependents_count']} dependents")
