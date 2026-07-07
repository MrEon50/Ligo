"""LIGO CLI v2.0 — command-line interface for the LIGO framework.

Usage:
    python -m ligo check              # Full self-check + Stability Score
    python -m ligo lint               # Import + architecture validation  
    python -m ligo new-module <name>  # Generator nowego modułu (3 pliki naraz)
    python -m ligo snapshot           # Zapisz snapshot aktualnego stanu
    python -m ligo health             # Stability Score w formacie Markdown
    python -m ligo analyze            # Pełna analiza projektu
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# Ensure UTF-8 output on Windows (cp1250 can't encode emojis)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _get_project_root() -> Path:
    """Znajdź root katalogu Ligo (parent of _projects/)."""
    from _config import PROJECT_ROOT as pr
    return pr.parent  # Ligo root (parent of _system/)


# ------------------------------------------------------------------
# Command handlers
# ------------------------------------------------------------------

def cmd_check(args) -> int:
    """Pełny self-check + Stability Score."""
    from registry.self_verify import SelfVerifier
    
    root = _get_project_root()
    verifier = SelfVerifier(root)
    
    report = verifier.run_full_check()
    
    print(f"\n=== LIGO Self-Verification Report ===")
    print(f"Project: {report['project_root']}")
    print(f"Score:   {report['stability_score']}/100 (Grade {report['grade']})")
    print(f"Checks:  {report['checks_passed']}/{report['checks_total']} passed")
    
    return 0 if report['grade'] != 'F' else 1


def cmd_lint(args) -> int:
    """Import + architecture validation."""
    from registry.import_checker import ImportChecker
    
    root = _get_project_root()
    
    # Load validator directly via filesystem path (not package import)
    import importlib.util as ilu
    spec = ilu.spec_from_file_location(
        "ligo_arch_validator",
        str(root / "_system" / "utils" / "ligo_architecture_validator.py"),
    )
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    validate_project = mod.validate_project
    
    # Architecture validator
    print("--- Architecture Validation ---")
    arch_report = validate_project(root / "_projects")
    if arch_report.is_clean:
        print("  OK: No architecture violations found.")
    else:
        for v in arch_report.violations[:10]:
            print(f"  [{v.severity}] {v.rule_id}: {v.message}")
    
    # Import checker
    print("\n--- Import Check ---")
    checker = ImportChecker(root)
    report = checker.check_all()
    
    if report["total_issues"] == 0:
        print("  OK: No import issues found.")
    else:
        for issue in report["issues"][:15]:
            print(f"  [{issue.get('severity', '?')}] {issue['file_path']}: {issue['message']}")
    
    if report["total_orphans"] > 0:
        print(f"\n  ⚠️  Orphan modules found: {report['total_orphans']}")
        for orphan in report["orphans"]:
            print(f"     - {orphan['name']} ({orphan.get('type', '?')})")
    
    return 1 if report["total_issues"] > 0 else 0


def cmd_new_module(args) -> int:
    """Generator nowego modułu (3 pliki naraz)."""
    from registry.module_generator import ModuleGenerator
    
    root = _get_project_root()
    gen = ModuleGenerator(root)
    
    result = gen.generate(
        name=args.name,
        service_class=args.service_class,
        methods=[m.strip() for m in args.methods.split(",")] if args.methods else None,
    )
    
    print(f"\n=== Generated: {result.name} ===")
    print(f"Contract: {result.contract_path}")
    print(f"Module:   {result.module_path}")
    print(f"Files created: {len(result.files_created)}")
    
    return 0


def cmd_snapshot(args) -> int:
    """Zapisz snapshot aktualnego stanu registry."""
    from registry.service_registry import ServiceRegistry
    
    root = _get_project_root()
    
    # Create a fresh empty registry and save snapshot
    registry = ServiceRegistry(project_id="default")
    filepath = registry.save_snapshot(str(root / "_projects" / "snapshots"))
    
    print(f"\nSnapshot saved: {filepath}")
    return 0


def cmd_health(args) -> int:
    """Stability Score w formacie Markdown."""
    from registry.stability_score import compute_stability_score
    
    root = _get_project_root()
    result = compute_stability_score(root)
    
    print(result.to_markdown())
    return 0


def cmd_analyze(args) -> int:
    """Pełna analiza projektu."""
    from registry.project_analyzer import ProjectAnalyzer
    
    root = _get_project_root()
    analyzer = ProjectAnalyzer(root)
    
    report = analyzer.analyze()
    
    print(f"\n=== LIGO Project Analysis ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    return 0


# ------------------------------------------------------------------
# CLI argument parser
# ------------------------------------------------------------------

def main() -> None:
    """Main entry point for the LIGO CLI."""
    parser = argparse.ArgumentParser(
        prog="ligo",
        description="LIGO v2.0 — Self-Verifying AI Framework CLI",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # check
    p_check = subparsers.add_parser("check", help="Pełny self-check + Stability Score (Grade A-F)")
    
    # lint
    p_lint = subparsers.add_parser("lint", help="Import + architecture validation")
    
    # new-module
    p_new = subparsers.add_parser("new-module", help="Generator nowego modułu (3 pliki naraz)")
    p_new.add_argument("name", help="Nazwa modułu w snake_case (np. 'weather')")
    p_new.add_argument("--service-class", default=None, help="Nazwa klasy usługi (PascalCase, domyślnie auto)")
    p_new.add_argument("--methods", default=None, help="Metody do wygenerowania (comma-separated, domyślnie: get_info)")
    
    # snapshot
    subparsers.add_parser("snapshot", help="Zapisz snapshot aktualnego stanu registry")
    
    # health
    subparsers.add_parser("health", help="Stability Score w formacie Markdown")
    
    # analyze
    subparsers.add_parser("analyze", help="Pełna analiza projektu (JSON)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        "check": cmd_check,
        "lint": cmd_lint,
        "new-module": cmd_new_module,
        "snapshot": cmd_snapshot,
        "health": cmd_health,
        "analyze": cmd_analyze,
    }
    
    handler = commands.get(args.command)
    if handler:
        sys.exit(handler(args))


if __name__ == "__main__":
    main()
