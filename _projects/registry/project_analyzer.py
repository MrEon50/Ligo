"""Project Analyzer for LIGO v2.0 — analiza struktury projektu i metryk.

Analizuje cały projekt:
    - Ilość modułów, kontraktów, testów
    - Graf zależności między modułami (przez importy)
    - Score stabilności z Self-Verification Engine
    - Podsumowanie w formacie Markdown

Używa AST parsing + stability_score + import_checker.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class ProjectAnalyzer:
    """Analizuje strukturę i metryki projektu LIGO v2.0."""

    def __init__(self, project_root: Path | None = None) -> None:
        from _config import PROJECT_ROOT as pr
        if project_root is None:
            self.project_root = pr.parent  # Ligo root (parent of _projects/)
        else:
            self.project_root = Path(project_root).resolve()

    def analyze(self) -> dict[str, Any]:
        """Pełna analiza projektu.

        Returns:
            Słownik z metrykami i podsumowaniem.
        """
        from registry.stability_score import compute_stability_score
        from registry.import_checker import ImportChecker

        # Collect stats
        contracts = self._count_files(self.project_root / "_projects" / "contracts")
        modules = self._count_files(self.project_root / "_projects" / "modules")
        tests = self._count_files(self.project_root / "_projects" / "tests", suffix="test_*.py")
        
        # Stability score
        try:
            stability = compute_stability_score(self.project_root)
            stability_data = stability.to_dict()
        except Exception:
            stability_data = {"overall": 0, "grade": "F"}

        # Import analysis
        try:
            checker = ImportChecker(self.project_root)
            import_report = checker.check_all()
        except Exception:
            import_report = {"total_issues": 0, "total_orphans": 0}

        # Dependency graph (AST-based)
        dep_graph = self._build_dependency_graph()

        total_py_files = sum(1 for _ in self.project_root.rglob("*.py"))

        return {
            "project_root": str(self.project_root),
            "total_python_files": total_py_files,
            "contracts": contracts,
            "modules": modules,
            "tests": tests,
            "stability_score": stability_data,
            "imports": import_report,
            "dependency_graph": dep_graph,
        }

    def report_markdown(self) -> str:
        """Generuj raport w formacie Markdown."""
        data = self.analyze()
        
        lines = [
            f"# 📊 LIGO Project Analysis Report",
            f"",
            f"**Project:** `{data['project_root']}`",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Python files | {data['total_python_files']} |",
            f"| Contracts | {data['contracts']} |",
            f"| Modules | {data['modules']} |",
            f"| Tests | {data['tests']} |",
            f"",
        ]

        # Stability score section
        stab = data["stability_score"]
        if isinstance(stab, dict):
            lines.extend([
                "## 🎯 Stability Score",
                "",
                f"**Grade:** {stab.get('grade', 'N/A')} ({stab.get('overall', 0)}/100)",
                "",
            ])

        # Import issues section
        imports = data["imports"]
        if isinstance(imports, dict):
            total_issues = imports.get("total_issues", 0)
            orphans = imports.get("total_orphans", 0)
            
            lines.extend([
                "## 📦 Imports & Orphans",
                "",
                f"- Issues: {total_issues}",
                f"- Orphan modules: {orphans}",
                "",
            ])

        # Dependency graph section (if available)
        dep_graph = data.get("dependency_graph")
        if dep_graph and dep_graph.get("nodes"):
            lines.extend([
                "## 🔗 Dependency Graph",
                "",
                f"- Nodes: {len(dep_graph['nodes'])}",
                f"- Edges: {len(dep_graph['edges'])}",
                "",
            ])

        return "\n".join(lines)

    def _count_files(self, directory: Path, suffix: str | None = None) -> int:
        """Policz pliki .py w katalogu."""
        if not directory.is_dir():
            return 0
        
        pattern = "*.py"
        if suffix:
            # Convert test_*.py to a glob pattern (Python doesn't have built-in glob with prefix)
            count = sum(1 for f in directory.rglob("*.py") 
                       if f.name.startswith(suffix.split("*")[0]) and not f.name.startswith("__"))
            return count
        
        return sum(1 for f in directory.rglob("*.py") if not f.name.startswith("__"))

    def _build_dependency_graph(self) -> dict[str, Any]:
        """Buduj graf zależności między modułami (AST-based)."""
        contracts_dir = self.project_root / "_projects" / "contracts"
        modules_dir = self.project_root / "_projects" / "modules"
        
        nodes: list[str] = []
        edges: list[dict[str, str]] = []
        
        # Collect all module/contract names as nodes
        for d in [contracts_dir, modules_dir]:
            if not d.is_dir():
                continue
            for py_file in d.glob("*.py"):
                name = py_file.stem.replace("_protocol", "")  # normalize contract names
                if not name.startswith("__") and name not in nodes:
                    nodes.append(name)

        # Build edges from imports (only within-contract/module imports)
        all_py_files = list(self.project_root.rglob("*.py"))
        
        for py_file in all_py_files:
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue

            module_name = py_file.stem
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imported = getattr(node, "module", "") or ""
                    base = imported.split(".")[0] if "." in imported else imported
                    
                    # Only track project-relative imports (not stdlib)
                    if base in nodes and module_name != base:
                        edge = {"from": module_name, "to": base}
                        if edge not in edges:  # deduplicate
                            edges.append(edge)

        return {"nodes": sorted(nodes), "edges": edges}


if __name__ == "__main__":
    analyzer = ProjectAnalyzer()
    print(analyzer.report_markdown())
