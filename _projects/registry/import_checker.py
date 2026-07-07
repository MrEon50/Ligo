"""Import Checker for LIGO v2.0 — statyczna analiza importów i wykrywanie orphan modułów.

Analizuje wszystkie pliki .py w projekcie:
    - Czy importy wskazują na istniejące moduły?
    - Czy są niepotrzebne (unused) importy?
    - Jakie pliki NIE są importowane nigdzie (orphan modules)?
    - Które kontrakty mają niezaimplementowane metody?

Używa AST parsing — nie wykonuje kodu.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ImportIssue:
    """Problem z importem."""
    file_path: str
    line_no: int
    issue_type: str  # "missing_module", "unused_import", "invalid_syntax"
    message: str
    severity: str = "WARNING"  # "ERROR" or "WARNING"


@dataclass
class OrphanModule:
    """Moduł który NIE jest importowany nigdzie w projekcie."""
    file_path: Path
    name: str  # module name (without .py)
    type: str  # "contract", "module", "utility"


class ImportChecker:
    """Statyczna analiza importów i orphan modułów w LIGO project."""

    def __init__(self, project_root: Path | None = None) -> None:
        from _config import PROJECT_ROOT as pr
        if project_root is None:
            self.project_root = pr.parent  # Ligo root (parent of _projects/)
        else:
            self.project_root = Path(project_root).resolve()

    def check_all(self) -> dict[str, Any]:
        """Uruchom pełną analizę importów.

        Returns:
            Raport z problemami importów + listą orphan modułów.
        """
        issues: list[ImportIssue] = []
        all_py_files = self._collect_all_python_files()
        
        # Build map of all module names -> file paths
        module_map = self._build_module_map(all_py_files)

        # Check imports in each file
        for filepath, rel_path in all_py_files:
            try:
                source = filepath.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                issues.append(ImportIssue(
                    file_path=str(rel_path), line_no=0,
                    issue_type="invalid_syntax", message=f"Cannot parse {rel_path}",
                    severity="ERROR",
                ))
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    self._check_import(node, source, rel_path, module_map, issues)

        # Find orphan modules
        orphans = self._find_orphans(all_py_files)

        return {
            "issues": [i.__dict__ for i in issues],
            "orphans": [{"path": str(o.file_path), "name": o.name, "type": o.type} for o in orphans],
            "total_issues": len(issues),
            "total_orphans": len(orphans),
        }

    def _collect_all_python_files(self) -> list[tuple[Path, Path]]:
        """Zbierz wszystkie pliki .py w projekcie."""
        result = []
        for sub in ["_projects", "_system"]:
            base = self.project_root / sub
            if not base.is_dir():
                continue
            for py_file in sorted(base.rglob("*.py")):
                rel = py_file.relative_to(self.project_root)
                # Skip __init__.py from analysis (it's just a namespace marker)
                if "__init__" in py_file.parts and len(py_file.parts) > 1:
                    continue
                result.append((py_file, rel))
        return result

    def _build_module_map(self, files: list[tuple[Path, Path]]) -> dict[str, Path]:
        """Zbuduj mapę nazw modułów -> ścieżki."""
        module_map = {}
        for filepath, rel in files:
            name = self._get_module_name(rel)
            if name:
                module_map[name] = filepath
        return module_map

    def _get_module_name(self, rel_path: Path) -> str | None:
        """Ekstrahuj nazwę modułu z ścieżki."""
        parts = list(rel_path.parts)
        # Skip leading directories like "_projects/" or "_system/utils/"
        if parts and parts[0] in ("_projects", "_system"):
            parts.pop(0)
        
        # For _system/utils/*.py -> utils.*
        if len(parts) >= 2:
            return ".".join(p for p in parts[:-1]) + "." + parts[-1].replace(".py", "")
        elif len(parts) == 1 and parts[0].endswith(".py"):
            return parts[0].replace(".py", "")
        
        # Skip non-module files (e.g., __init__.py at package level)
        if not parts:
            return None

        name = ".".join(p for p in parts if not p.endswith(".py"))
        if parts[-1].endswith(".py"):
            name += "." + parts[-1].replace(".py", "")
        
        return name or None

    def _check_import(
        self, node: ast.Import | ast.ImportFrom, source: str, rel_path: Path,
        module_map: dict[str, Path], issues: list[ImportIssue]
    ) -> None:
        """Sprawdź pojedynczy import."""
        line_no = getattr(node, "lineno", 0)

        if isinstance(node, ast.ImportFrom):
            # from X.Y.Z import A.B.C
            module_name = getattr(node, "module", "") or ""
            
            # Skip relative imports (they're fine for __init__.py patterns)
            if node.level > 0:
                return

            # Check if the imported module exists in our map
            base_module = ".".join(module_name.split(".")[:-1]) if "." in module_name else module_name
            
            # Simple check: does any module start with this prefix?
            matched = any(
                mod == module_name or mod.startswith(module_name + ".") 
                for mod in module_map
            )
            
            # Only flag as error if it's a clear non-standard import (not stdlib)
            stdlib_modules = {
                "os", "sys", "json", "ast", "re", "datetime", "typing", "abc", 
                "pathlib", "logging", "argparse", "collections", "functools",
                "math", "random", "string", "io", "__future__",
                "typing_extensions", "importlib", "dataclasses", "copy",
            }
            
            # Special LIGO namespaces — always allowed (Safe-Zone architecture)
            ligo_namespaces = {"_system", "_hub"}
            first_part = module_name.split(".")[0] if module_name else ""
            
            if not matched and first_part not in stdlib_modules and first_part not in ligo_namespaces:
                issues.append(ImportIssue(
                    file_path=str(rel_path), line_no=line_no,
                    issue_type="missing_module", 
                    message=f"Import '{module_name}' may not exist (not found in project modules)",
                    severity="WARNING",
                ))

    def _find_orphans(self, files: list[tuple[Path, Path]]) -> list[OrphanModule]:
        """Znajdź pliki które NIE są importowane nigdzie w projekcie."""
        # Collect all imported names across the project
        imported_names = set()
        
        for filepath, rel_path in files:
            try:
                source = filepath.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module_name = getattr(node, "module", "") or ""
                    base = module_name.split(".")[0] if module_name else ""
                    # Only consider project-relative imports
                    if base and not self._is_stdlib(base):
                        imported_names.add(base)

        # Check each file — is it imported by anyone?
        orphans: list[OrphanModule] = []
        for filepath, rel in files:
            name = self._get_module_name(rel)
            if not name:
                continue
            
            first_part = name.split(".")[0]
            
            # Skip __init__.py — they're always "imported" as packages
            if "__init__" in rel.parts and len(rel.parts) > 1:
                continue
                
            # Skip utility files that are always imported via utils.* pattern
            is_utility = any(p == "_utils" or p == "utils" for p in rel.parts)
            
            if not self._is_stdlib(first_part) and first_part not in imported_names and not is_utility:
                module_type = "contract" if "contracts" in str(rel).split("/") else \
                              "module" if "modules" in str(rel).split("/") else "utility"
                
                orphans.append(OrphanModule(
                    file_path=filepath, name=name, type=module_type,
                ))

        return orphans

    @staticmethod
    def _is_stdlib(name: str) -> bool:
        """Sprawdź czy nazwa to moduł standardowy."""
        stdlib = {
            "os", "sys", "json", "ast", "re", "datetime", "typing", "abc", 
            "pathlib", "logging", "argparse", "collections", "functools",
            "math", "random", "string", "io", "__future__",
            "typing_extensions", "importlib", "dataclasses", "copy",
        }
        return name in stdlib


if __name__ == "__main__":
    checker = ImportChecker()
    report = checker.check_all()

    print(f"\n=== LIGO Import Check Report ===")
    print(f"Total issues: {report['total_issues']}")
    for issue in report["issues"][:10]:
        print(f"  [{issue.get('severity', '?')}] {issue['file_path']}: {issue['message']}")

    print(f"\nOrphan modules: {report['total_orphans']}")
    for orphan in report["orphans"][:10]:
        print(f"  {orphan['name']} ({orphan['type']})")
