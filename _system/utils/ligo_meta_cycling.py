"""LIGO Meta-Cycling Integration — integracja Context Manager i Dependency Graph z ServiceRegistry.

Ten moduł tworzy pełnie zintegrowany system zarządzania stanem między sesjami AI.
Każda modyfikacja kodu jest automatycznie:
    1. Trackowana w ContextManager (co zostało zmienione?)
    2. Analizowana pod kątem bezpieczeństwa w DependencyGraph (co się zepsuje?)
    3. Zapisywana w SessionManager (przywrócenie stanu)

Użyj:
    from _system.utils.ligo_meta_cycling import MetaCyclingManager
    
    manager = MetaCyclingManager()
    
    # Podczas pracy — trackuj modyfikacje
    manager.track_file_modification("modules/polish_greeting.py", new_content)
    
    # Przed zapisem — sprawdź bezpieczeństwo
    result = manager.check_safety_before_save()
    if not result["safe"]:
        print(f"⚠️  Zmiany zepsują: {result['violations']}")
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


class MetaCyclingManager:
    """Zintegrowany menedżer meta-cyklizmu LIGO — Context + Dependencies.

    Łączy w sobie:
        - ContextManager: śledzenie modyfikacji plików między sesjami
        - DependencyGraph: analiza wpływu zmian na zależności projektu
        - SessionManager: trwałe zapisywanie/restaurowanie stanu

    Umożliwia bezpieczne ulepszanie samego LIGO przez AI model.
    """

    def __init__(
        self,
        project_root: str = "_projects",
        context_dir: str | None = None,
        session_dir: str | None = None,
    ) -> None:
        from _system.utils.context_manager import ContextManager
        from _system.utils.dependency_graph import DependencyGraph
        from _system.utils.session_manager import SessionManager

        self.project_root = project_root
        self.context_manager = ContextManager(context_dir=context_dir)
        self.dependency_graph = DependencyGraph(project_root=project_root)
        self.session_manager = SessionManager(session_dir=session_dir or os.path.join("_projects", "_system", "sessions"))

        # Ładowanie istniejącego stanu przy starcie
        self._load_initial_state()

    def _load_initial_state(self) -> None:
        """Załaduj stan z ostatniej sesji (jeśli istnieje)."""
        # Wczytaj kontekst modyfikacji
        context = self.context_manager.load_context(project_id="default")
        if context and context.get("files"):
            print(f"[MetaCycling] Załadowano {context['modified_files_count']} modyfikacji z poprzedniej sesji.")

    # ------------------------------------------------------------------
    # File Modification Tracking (A: Context State)
    # ------------------------------------------------------------------

    def track_file_modification(
        self,
        file_path: str,
        new_content: str | None = None,
        operation: str = "modified",
    ) -> dict[str, Any]:
        """Zarejestruj modyfikację pliku we wszystkich systemach.

        Args:
            file_path: Ścieżka do zmodyfikowanego pliku (względem projektu).
            new_content: Nowa zawartość pliku (opcjonalnie — zapisywana do snapshotu).
            operation: Typ operacji ("modified", "created", "deleted").

        Returns:
            Rejestr modyfikacji z metadanymi.
        """
        modification = self.context_manager.track_modification(
            file_path=file_path,
            new_content=new_content,
            operation=operation,
        )

        # Dodaj do logu sesji w SessionManager
        session_entry = {
            "type": "file_modification",
            "file_path": file_path,
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.session_manager.save_session_log(
            project_id="default",
            log_entry=session_entry,
        )

        return modification

    def get_modified_files(self) -> list[str]:
        """Zwrot listy ścieżek wszystkich zmodyfikowanych plików."""
        return self.context_manager.get_modified_files()

    # ------------------------------------------------------------------
    # Safety Checks (B: Dependency Graph)
    # ------------------------------------------------------------------

    def check_safety_before_save(self) -> dict[str, Any]:
        """Sprawdź bezpieczeństwo zapisu przed faktycznym zapisem.

        Analizuje wszystkie zmodyfikowane pliki pod kątem:
            - Cykli w zależnościach (risk infinite recursion)
            - Brakujących metod/klas w zmodyfikowanych modułach
            - Zmian kontraktów które zepsują zależne moduły

        Returns:
            Słownik z wynikami sprawdzenia bezpieczeństwa.
        """
        self.dependency_graph.scan_project()

        violations: list[dict[str, Any]] = []
        modified_files = self.get_modified_files()

        # Sprawdzaj każdy zmodyfikowany plik
        for file_path in modified_files:
            safety_result = self.dependency_graph.check_safety(file_path)

            if not safety_result.safe:
                violation = {
                    "file": file_path,
                    "dependents_affected": safety_result.dependents,
                    "missing_methods": safety_result.missing_methods,
                }
                violations.append(violation)

        # Wykryj cykle w grafie zależności po zmianach
        cycles = self.dependency_graph.detect_cycles()
        if cycles:
            violations.append({
                "type": "cycle_detected",
                "cycles": cycles[:5],  # Limit do 5 cykli dla czytelności
            })

        return {
            "safe": len(violations) == 0,
            "modified_files_count": len(modified_files),
            "violations": violations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # State Persistence (Full Session Save/Restore)
    # ------------------------------------------------------------------

    def save_full_session(self, project_id: str = "default") -> tuple[str, str]:
        """Zapisz pełny stan sesji: kontekst + modyfikacje.

        Zwraca tuplę (context_snapshot_path, modification_log_path).
        """
        context_path = self.context_manager.save_context_snapshot(
            project_id=project_id,
            include_contents=True,  # Zapisz pełną zawartość plików dla kontekstu
        )

        return context_path, ""

    def restore_full_session(self, project_id: str = "default", restore_contents: bool = True) -> dict[str, Any] | None:
        """Przywróć pełny stan sesji z poprzedniej pracy.

        Args:
            project_id: ID projektu do przywrócenia.
            restore_contents: Czy przywrócić zawartość plików (True) czy tylko metadane (False).

        Returns:
            Wczytany stan kontekstu lub None jeśli brak zapisu.
        """
        return self.context_manager.load_context(
            project_id=project_id,
            restore_contents=restore_contents,
        )

    def get_session_summary(self) -> dict[str, Any]:
        """Podsumowanie aktualnej sesji AI."""
        modified_count = len(self.get_modified_files())
        summary = self.context_manager.get_context_summary(project_id="default")

        return {
            "modified_files": modified_count,
            "context_status": summary.get("status", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    manager = MetaCyclingManager()

    # Demo track modyfikacji
    manager.track_file_modification(
        file_path="modules/polish_greeting.py",
        new_content="# Polish Greeting Service\nprint('Hello from MetaCycling!')",
        operation="modified",
    )

    print("\n=== Session Summary ===")
    session_summary = manager.get_session_summary()
    print(json.dumps(session_summary, indent=2))
