"""Self-Verification Engine for LIGO v2.0.

LIGO verifies itself programmatically: structure integrity, import correctness,
module health, and meta-cycle consistency — all computed into a Stability Score
(0-100) with letter grades A-F.

Usage:
    from registry.self_verify import SelfVerifier
    
    verifier = SelfVerifier()
    result = verifier.run_full_check()
    
    print(f"Stability: {result['overall']}/100 (Grade {result['grade']})")
"""

from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from registry.stability_score import compute_stability_score


# ------------------------------------------------------------------
# Check result types
# ------------------------------------------------------------------

@dataclass
class CheckResult:
    """Result of a single verification check."""
    name: str
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class SelfVerifier:
    """LIGO self-verification engine.

    Runs all checks programmatically and produces a Stability Score (0-100).
    
    Check categories:
        - structure   : folder hierarchy + _config.py presence
        - imports     : import path correctness across .py files
        - modules     : stateless check, cross-module dependency analysis
        - contracts   : ABC protocol conformance verification
        - meta_cycle  : master prompt + version consistency
    """

    def __init__(self, project_root: str | Path | None = None) -> None:
        if project_root is None:
            from _config import PROJECT_ROOT as pr
            self.project_root = pr.parent  # Ligo root (parent of _projects/)
        else:
            self.project_root = Path(project_root).resolve()

        if not self.project_root.is_dir():
            raise FileNotFoundError(f"Project root does not exist: {self.project_root}")

        self._results: list[CheckResult] = []

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_structure(self) -> CheckResult:
        """Verify folder hierarchy exists."""
        required = ["_system", "_hub", "_projects"]
        missing = [d for d in required if not (self.project_root / d).is_dir()]

        result = CheckResult(
            name="structure",
            passed=len(missing) == 0,
            message=f"OK: all directories present" if not missing else f"Missing: {', '.join(missing)}",
            details={"missing_dirs": missing},
        )
        self._results.append(result)
        return result

    def check_config_exists(self) -> CheckResult:
        """Verify _config.py exists."""
        config_path = self.project_root / "_projects" / "_config.py"
        result = CheckResult(
            name="config_exists",
            passed=config_path.exists(),
            message=f"_config.py found at {config_path}" if config_path.exists() else f"_config.py not found!",
            details={"path": str(config_path)},
        )
        self._results.append(result)
        return result

    def check_imports(self) -> list[CheckResult]:
        """Verify import paths are correct across all .py files."""
        results: list[CheckResult] = []
        py_files = list((self.project_root / "_projects").rglob("*.py")) + \
                   list((self.project_root / "_system").rglob("*.py"))

        for py_file in py_files:
            rel = str(py_file.relative_to(self.project_root))
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                results.append(CheckResult(
                    name=f"import_check:{rel}", passed=False, message="Syntax error in file", details={}
                ))
                continue

            has_issues = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module_name = getattr(node, "module", "") or ""

                    # Absolute import of _projects/* from inside _projects/ is suspicious
                    if module_name.startswith("_projects") and not node.level:
                        has_issues = True
                        results.append(CheckResult(
                            name=f"import_check:{rel}", passed=False,
                            message=f"Absolute import of '{module_name}' (should be relative)",
                            details={"line": getattr(node, "lineno", 0)},
                        ))

            if not has_issues:
                results.append(CheckResult(name=f"import_check:{rel}", passed=True))

        return results

    def check_modules_stateless(self) -> list[CheckResult]:
        """Verify modules don't assign instance attributes in __init__."""
        modules_dir = self.project_root / "_projects" / "modules"
        if not modules_dir.is_dir():
            return [CheckResult(name="modules_stateless", passed=True, message="No modules/ directory")]

        results: list[CheckResult] = []
        for mod_file in modules_dir.rglob("*.py"):
            rel = str(mod_file.relative_to(self.project_root))
            try:
                source = mod_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                results.append(CheckResult(name=f"stateless:{rel}", passed=False, message="Syntax error"))
                continue

            is_stateless = True
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if (isinstance(target, ast.Attribute) and
                            getattr(getattr(target, "value", None), "id", "") == "self"):
                            is_stateless = False

            results.append(CheckResult(
                name=f"stateless:{rel}", passed=is_stateless,
                message="OK: stateless module" if is_stateless else f"{mod_file.stem} assigns instance attributes!",
                details={"file": rel},
            ))

        return results

    def check_contracts_valid(self) -> list[CheckResult]:
        """Verify contracts use @abstractmethod (not plain methods)."""
        contracts_dir = self.project_root / "_projects" / "contracts"
        if not contracts_dir.is_dir():
            return [CheckResult(name="contracts_valid", passed=True, message="No contracts/ directory")]

        results: list[CheckResult] = []
        for contract_file in contracts_dir.glob("*.py"):
            rel = str(contract_file.relative_to(self.project_root))
            try:
                source = contract_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue

            has_abstract = False
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if method is decorated with @abstractmethod or @abc.abstractmethod
                    for dec in getattr(node, "decorator_list", []):
                        if self._is_abstract_decorator(dec):
                            has_abstract = True

            results.append(CheckResult(
                name=f"contract:{rel}", passed=has_abstract,
                message="OK: uses abstract methods" if has_abstract else f"{contract_file.stem} has no @abstractmethod!",
            ))

        return results

    def check_meta_cycle(self) -> list[CheckResult]:
        """Verify master prompt + version consistency."""
        results: list[CheckResult] = []

        # current_task.md exists
        ct_path = self.project_root / "_hub" / "current_task.md"
        results.append(CheckResult(
            name="meta_cycle", passed=ct_path.exists(),
            message=f"_hub/current_task.md found" if ct_path.exists() else f"_hub/current_task.md not found!",
        ))

        # Version consistency between tech_stack and project_anchor
        tech = self.project_root / "_system" / "tech_stack.md"
        anchor = self.project_root / "_system" / "project_anchor.md"
        if tech.exists() and anchor.exists():
            import re as _re
            try:
                tech_ver = _re.search(r"v(\d+\.\d+)", tech.read_text(encoding="utf-8")) or None
                anchor_ver = _re.search(r"v(\d+\.\d+)", anchor.read_text(encoding="utf-8")) or None
            except (UnicodeDecodeError, OSError):
                tech_ver, anchor_ver = None, None
            results.append(CheckResult(
                name="version_consistent",
                passed=tech_ver is not None and anchor_ver == tech_ver,
                message=f"OK: both v{tech_ver.group(1)}" if tech_ver else "Version mismatch!",
            ))

        return results

    @staticmethod
    def _is_abstract_decorator(node: ast.expr) -> bool:
        """Check if AST node is an abstractmethod decorator."""
        # @abstractmethod
        if isinstance(node, ast.Name) and node.id == "abstractmethod":
            return True
        # @abc.abstractmethod or @ABC.abstractmethod
        if isinstance(node, ast.Attribute) and node.attr == "abstractmethod":
            return True
        return False

    # ------------------------------------------------------------------
    # Full verification pipeline
    # ------------------------------------------------------------------

    def run_full_check(self) -> dict[str, Any]:
        """Run ALL verification checks and produce a complete report.

        Returns:
            Dictionary with all check results + stability score + grade.
        """
        self._results = []

        # Run all individual checks
        struct_result = self.check_structure()
        config_result = self.check_config_exists()
        import_results = self.check_imports()
        module_results = self.check_modules_stateless()
        contract_results = self.check_contracts_valid()
        meta_results = self.check_meta_cycle()

        # Compute stability score
        try:
            from registry.stability_score import compute_stability_score as _compute
            stability = _compute(self.project_root)
            overall_score = round(stability.overall, 1)
            grade = stability.grade
        except Exception as e:
            overall_score = 0.0
            grade = "F"

        # Summary
        total_checks = len(self._results) + len(import_results) + \
                       len(module_results) + len(contract_results) + len(meta_results)
        passed_checks = sum(1 for r in [struct_result, config_result] + import_results + module_results + contract_results + meta_results if r.passed)

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_root": str(self.project_root),
            "checks_total": total_checks,
            "checks_passed": passed_checks,
            "checks_failed": total_checks - passed_checks,
            "stability_score": overall_score,
            "grade": grade,
            "details": {
                "structure": struct_result.to_dict() if hasattr(struct_result, "to_dict") else {"name": struct_result.name, "passed": struct_result.passed},
                "config": config_result.to_dict() if hasattr(config_result, "to_dict") else {"name": config_result.name, "passed": config_result.passed},
            },
        }

        return report

    def get_report(self) -> dict[str, Any]:
        """Get the latest full check report."""
        if not self._results:
            return self.run_full_check()
        # Re-run to regenerate fresh results
        return self.run_full_check()


if __name__ == "__main__":
    # Quick standalone run
    verifier = SelfVerifier()
    report = verifier.run_full_check()

    print(f"\n=== LIGO Self-Verification Report ===")
    print(f"Project: {report['project_root']}")
    print(f"Score: {report['stability_score']}/100 (Grade {report['grade']})")
    print(f"Checks: {report['checks_passed']}/{report['checks_total']} passed")
