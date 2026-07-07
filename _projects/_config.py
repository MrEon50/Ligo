"""Centralna konfiguracja projektu LIGO v2.0.

Jedyne miejsce gdzie definiujemy ścieżki projektu — wszystko importuje stąd.
Działa niezależnie od cwd (current working directory).

Zabezpieczenia:
    - WALYDACJA ścieżek: wszystkie ścieżki muszą być podkatogiem PROJECT_ROOT lub SYSTEM_ROOT
    - PATH TRAVERSAL PROTECTION: zabrania wyjścia poza dozwolone obszary
    - AUTO-INITIALIZACJA: ensure_paths() i ensure_directories() wywoływane automatycznie

Użycie:
    from _config import PROJECT_ROOT, SYSTEM_ROOT, ensure_paths, validate_paths, is_safe_path

    # Ensure paths exist on disk
    ensure_paths()

    # Validate
    issues = validate_paths()
    if issues:
        raise RuntimeError("\\n".join(issues))

    # Safe path check
    is_safe_path(PROJECT_ROOT / "registry" / "service_registry.py")  # True
    is_safe_path(Path("/etc/passwd"))  # False
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# ------------------------------------------------------------------
# Core path resolution — obliczane raz na starcie na podstawie położenia tego pliku
# ------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()           # .../_projects/_config.py
PROJECT_ROOT: Path = _THIS_FILE.parent          # .../_projects/
SYSTEM_ROOT: Path  = PROJECT_ROOT.parent        # .../Ligo (root, parent of _system/)
HUB_ROOT: Path     = SYSTEM_ROOT / "_hub"       # .../Ligo/_hub/

# Dozwolone strefy — ścieżki muszą być podkatogiem którejkolwiek z nich
_ALLOWED_STREETS: tuple[Path, ...] = (
    PROJECT_ROOT,
    SYSTEM_ROOT,
    HUB_ROOT,
)

# ------------------------------------------------------------------
# Derived paths — względem core roots
# ------------------------------------------------------------------

TOOLS_ROOT: Path          = PROJECT_ROOT / "tools"
SNAPSHOTS_DIR: Path       = PROJECT_ROOT / "snapshots"
LOGS_DIR: Path            = PROJECT_ROOT / "logs"
SESSIONS_DIR: Path        = SYSTEM_ROOT / "_system" / "sessions"
PROJECTS_DIR: Path        = SYSTEM_ROOT / "projects"  # multi-project dir (v2.0)
ARCHIVE_DIR: Path         = HUB_ROOT / "archive"      # stare wersje promptów itp.

# ------------------------------------------------------------------
# sys.path management — dodaje _projects/ i Ligo root do PATH automatycznie
# ------------------------------------------------------------------

def ensure_paths() -> None:
    """Dodaje PROJECT_ROOT i SYSTEM_ROOT do sys.path (jeśli jeszcze nie ma).

    Wywoływane automatycznie na końcu tego modułu — nie trzeba wywoływać ręcznie.
    """
    _root_str = str(PROJECT_ROOT)
    if _root_str not in sys.path:
        sys.path.insert(0, _root_str)
    _sys_str = str(SYSTEM_ROOT)
    if _sys_str not in sys.path:
        sys.path.insert(0, _sys_str)


def ensure_directories() -> list[Path]:
    """Tworzy brakujące foldery projektu (snapshots, logs, sessions, tools).

    Returns:
        Lista utworzonych katalogów.
    """
    created: list[Path] = []
    for d in [SNAPSHOTS_DIR, LOGS_DIR, SESSIONS_DIR, TOOLS_ROOT]:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)
    return created


# ------------------------------------------------------------------
# Validation — sprawdza czy ścieżki są poprawne
# ------------------------------------------------------------------

def validate_paths() -> list[str]:
    """Sprawdza czy wszystkie kluczowe foldery istnieją na dysku.

    Returns:
        Lista komunikatów o brakujących elementach (pusta = wszystko OK).
    """
    issues: list[str] = []
    required_dirs = [PROJECT_ROOT, SYSTEM_ROOT, HUB_ROOT]
    for d in required_dirs:
        if not d.exists():
            issues.append(f"Brakujący katalog: {d}")
    return issues


def is_safe_path(target: Path) -> bool:
    """Sprawdza czy podana ścieżka jest podkatalogiem dozwolonego obszaru.

    Chroni przed path traversal attack (np. Path("/etc/passwd")).

    Args:
        target: Ścieżka do sprawdzenia.

    Returns:
        True jeśli target jest podkatogiem którejkolwiek z dozwolonych stref.
    """
    try:
        resolved = target.resolve()
        for allowed in _ALLOWED_STREETS:
            try:
                resolved.relative_to(allowed.resolve())
                return True
            except ValueError:
                continue
        return False
    except (OSError, RuntimeError):
        # OSError — nieistniejąca ścieżka
        # RuntimeError — zbyt długa ścieżka na Windows
        return False


# ------------------------------------------------------------------
# Auto-execution — ensure_paths + directories przy imporcie
# ------------------------------------------------------------------

ensure_paths()
ensure_directories()
