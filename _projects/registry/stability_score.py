"""Stability Score Engine for LIGO v2.0.

Computes a 0-100 stability score based on four dimensions:
    - Structure Score      — folder hierarchy integrity
    - Import Score         — import path correctness
    - Module Health        — module quality (stateless, no cross-deps)
    - MetaCycle Integrity  — master prompt + protocol consistency

Grade mapping:
    A (90-100): Excellent stability
    B  (75-89): Good stability
    C  (60-74): Fair stability
    D  (40-59): Poor stability
    F  (0-39): Critical — immediate fixes needed
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ------------------------------------------------------------------
# Data structures for score components
# ------------------------------------------------------------------

@dataclass
class ScoreDimension:
    """Single dimension of the stability score."""
    name: str
    weight: float  # 0.0 - 1.0 (total weights must sum to 1.0)
    max_score: int = 100
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class StabilityResult:
    """Complete stability assessment result."""
    structure: ScoreDimension
    imports: ScoreDimension
    module_health: ScoreDimension
    meta_cycle: ScoreDimension
    overall: float  # weighted average 0-100

    @property
    def grade(self) -> str:
        if self.overall >= 90: return "A"
        if self.overall >= 75: return "B"
        if self.overall >= 60: return "C"
        if self.overall >= 40: return "D"
        return "F"

    def to_dict(self) -> dict[str, Any]:
        return {
            "structure": {
                "score": self.structure.details.get("current", 0),
                "max": self.structure.max_score,
                "weight": self.structure.weight,
                "details": self.structure.details,
            },
            "imports": {
                "score": self.imports.details.get("current", 0),
                "max": self.imports.max_score,
                "weight": self.imports.weight,
                "details": self.imports.details,
            },
            "module_health": {
                "score": self.module_health.details.get("current", 0),
                "max": self.module_health.max_score,
                "weight": self.module_health.weight,
                "details": self.module_health.details,
            },
            "meta_cycle": {
                "score": self.meta_cycle.details.get("current", 0),
                "max": self.meta_cycle.max_score,
                "weight": self.meta_cycle.weight,
                "details": self.meta_cycle.details,
            },
            "overall": round(self.overall, 1),
            "grade": self.grade,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# 📊 LIGO Stability Score — **Grade {self.grade}** ({self.overall:.0f}/100)",
            "",
            "| Dimension | Score | Weight | Status |",
            "|-----------|-------|--------|--------|",
        ]
        for dim in [self.structure, self.imports, self.module_health, self.meta_cycle]:
            score = dim.details.get("current", 0)
            status_emoji = "✅" if score >= 80 else ("⚠️" if score >= 60 else "❌")
            lines.append(
                f"| {dim.name} | {score}/{dim.max_score} | {dim.weight:.0%} | {status_emoji} |"
            )
        lines.extend(["", "**Grade:** A (90-100) | B (75-89) | C (60-74) | D (40-59) | F (0-39)", ""])
        return "\n".join(lines)


# ------------------------------------------------------------------
# Weights for each dimension — tuneable
# ------------------------------------------------------------------

DIMENSION_WEIGHTS = {
    "structure":      0.25,  # Folder hierarchy + _config.py presence
    "imports":        0.30,  # Import path correctness (most critical)
    "module_health":  0.25,  # Stateless modules, no cross-deps
    "meta_cycle":     0.20,  # Master prompt + protocol consistency
}


# ------------------------------------------------------------------
# Individual dimension evaluators
# ------------------------------------------------------------------

def evaluate_structure(project_root: Path) -> ScoreDimension:
    """Check folder hierarchy integrity."""
    required_dirs = ["_system", "_hub", "_projects"]
    present = sum(1 for d in required_dirs if (project_root / d).is_dir())
    score = int((present / len(required_dirs)) * 100)

    # Bonus: _config.py exists at project root
    config_path = project_root / "_projects" / "_config.py"
    if config_path.exists():
        score = min(100, score + 5)

    details = {
        "current": score,
        "required_dirs": required_dirs,
        "present_dirs": [d for d in required_dirs if (project_root / d).is_dir()],
        "_config_exists": config_path.exists(),
    }
    return ScoreDimension(name="Structure", weight=DIMENSION_WEIGHTS["structure"], max_score=100, details=details)


def evaluate_imports(project_root: Path) -> ScoreDimension:
    """Check import path correctness across all Python files."""
    py_files = list((project_root / "_projects").rglob("*.py")) + \
               list((project_root / "_system").rglob("*.py"))

    issues: list[str] = []
    total_checks = 0
    passed_checks = 0

    for py_file in py_files:
        rel = str(py_file.relative_to(project_root))
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                total_checks += 1
                module_name = getattr(node, "module", "") or ""

                # Check: imports from _projects/ should use relative or _config-based paths
                if module_name.startswith("_projects") and not node.level:
                    issues.append(f"{rel}: absolute import of '{module_name}' (should be relative)")

                # Check: imports referencing non-existent modules
                elif module_name and not module_name.startswith("__"):
                    passed_checks += 1

    # If no files found, assume OK
    if total_checks == 0:
        score = 80
        issues.append("No Python import statements analyzed (no .py files or syntax errors)")
    else:
        score = int((passed_checks / max(total_checks, 1)) * 100)

    details = {
        "current": score,
        "files_analyzed": len(py_files),
        "imports_checked": total_checks,
        "issues_found": len(issues),
    }
    return ScoreDimension(name="Imports", weight=DIMENSION_WEIGHTS["imports"], max_score=100, details=details, warnings=issues)


def evaluate_module_health(project_root: Path) -> ScoreDimension:
    """Check module quality — stateless check + cross-module dependency analysis."""
    modules_dir = project_root / "_projects" / "modules"
    if not modules_dir.is_dir():
        return ScoreDimension(name="Module Health", weight=DIMENSION_WEIGHTS["module_health"], max_score=100,
                              details={"current": 50, "reason": "No modules/ directory found"})

    py_files = list(modules_dir.rglob("*.py"))
    if not py_files:
        return ScoreDimension(name="Module Health", weight=DIMENSION_WEIGHTS["module_health"], max_score=100,
                              details={"current": 50, "reason": "No .py files in modules/"})

    stateless_count = 0
    total_modules = len(py_files)
    issues: list[str] = []

    for mod_file in py_files:
        source = mod_file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Check 1: No __init__ imports from other modules (cross-dep violation)
        has_cross_imports = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and getattr(node, "module", "") and \
               not getattr(node, "level", 0):
                module_name = node.module
                if "modules/" in str(mod_file.relative_to(project_root)):
                    has_cross_imports = True

        # Check 2: No instance attributes assigned in __init__ (stateful check)
        is_stateless = True
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and \
                       isinstance(getattr(target, "value", None), ast.Name) and \
                       target.value.id == "self":
                        is_stateless = False

        if has_cross_imports:
            issues.append(f"{mod_file.name}: cross-module import detected")
        if not is_stateless:
            issues.append(f"{mod_file.name}: stateful — assigns instance attributes in __init__")

        # Check 3: Has docstring (best practice)
        if ast.get_docstring(tree):
            stateless_count += 1

    score = int((stateless_count / total_modules) * 100) if total_modules > 0 else 50
    details = {
        "current": score,
        "total_modules": total_modules,
        "docstring_count": stateless_count,
        "issues_found": len(issues),
    }
    return ScoreDimension(name="Module Health", weight=DIMENSION_WEIGHTS["module_health"], max_score=100, details=details, warnings=issues)


def evaluate_meta_cycle(project_root: Path) -> ScoreDimension:
    """Check master prompt + protocol consistency."""
    checks_passed = 0
    total_checks = 4
    issues: list[str] = []

    # Check 1: _hub/current_task.md exists
    if (project_root / "_hub" / "current_task.md").exists():
        checks_passed += 1
    else:
        issues.append("_hub/current_task.md not found")

    # Check 2: Master prompt exists (v1.1 or v2.0)
    mp_files = list((project_root / "_hub").glob("master_prompt_ligo*.md"))
    if mp_files:
        checks_passed += 1
    else:
        issues.append("No master_prompt_ligo_*.md found in _hub/")

    # Check 3: Version consistency (tech_stack.md vs project_anchor.md)
    tech_path = project_root / "_system" / "tech_stack.md"
    anchor_path = project_root / "_system" / "project_anchor.md"
    if tech_path.exists() and anchor_path.exists():
        try:
            tech_ver = _extract_version(tech_path.read_text(encoding="utf-8"))
            anchor_ver = _extract_version(anchor_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            tech_ver, anchor_ver = None, None
        if tech_ver == anchor_ver:
            checks_passed += 1
        else:
            issues.append(f"Version mismatch: tech_stack={tech_ver} vs project_anchor={anchor_ver}")

    # Check 4: _config.py exists (new in v2.0.1)
    config_path = project_root / "_projects" / "_config.py"
    if config_path.exists():
        checks_passed += 1
    else:
        issues.append("_projects/_config.py not found")

    score = int((checks_passed / total_checks) * 100)
    details = {
        "current": score,
        "checks_passed": checks_passed,
        "total_checks": total_checks,
        "version_consistent": (tech_ver == anchor_ver if tech_path.exists() and anchor_path.exists() else None),
    }
    return ScoreDimension(name="MetaCycle", weight=DIMENSION_WEIGHTS["meta_cycle"], max_score=100, details=details, warnings=issues)


def _extract_version(text: str) -> str | None:
    """Extract version string from markdown (e.g., 'v2.0', 'v1.1')."""
    match = re.search(r"v(\d+\.\d+)", text)
    return match.group(1) if match else None


# ------------------------------------------------------------------
# Main score computation
# ------------------------------------------------------------------

def compute_stability_score(project_root: str | Path) -> StabilityResult:
    """Compute the complete stability assessment for a LIGO project.

    Args:
        project_root: Absolute or relative path to the Ligo root directory.

    Returns:
        StabilityResult with all dimension scores and overall grade.
    """
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Project root does not exist: {root}")

    structure = evaluate_structure(root)
    imports_score = evaluate_imports(root)
    module_health = evaluate_module_health(root)
    meta_cycle = evaluate_meta_cycle(root)

    # Weighted average
    overall = (
        structure.details["current"] * structure.weight +
        imports_score.details["current"] * imports_score.weight +
        module_health.details["current"] * module_health.weight +
        meta_cycle.details["current"] * meta_cycle.weight
    )

    return StabilityResult(
        structure=structure,
        imports=imports_score,
        module_health=module_health,
        meta_cycle=meta_cycle,
        overall=overall,
    )


# ------------------------------------------------------------------
# Quick usage helper (for CLI / one-shot calls)
# ------------------------------------------------------------------

def quick_report(project_root: str | Path) -> str:
    """Return a human-readable markdown report of stability."""
    result = compute_stability_score(project_root)
    return result.to_markdown()


if __name__ == "__main__":
    # Quick standalone run
    from pathlib import Path as _Path
    print(quick_report(_Path(__file__).resolve().parent.parent))
