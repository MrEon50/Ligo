"""Context Manager — zarządza stanem modyfikacji plików między sesjami AI.

Śledzi które pliki zostały zmodyfikowane, zapisuje ich aktualną zawartość
w `_system/contexts/` i pozwala na przywrócenie stanu z poprzedniej sesji.

Użyj:
    manager = ContextManager()
    manager.track_modification("modules/polish_greeting.py", new_content)
    
    # Po zakończeniu pracy — zapisz kontekst do pliku
    manager.save_context_snapshot(project_id="default")
    
    # Przy starcie nowej sesji — odtwórz stan
    context = manager.load_context(project_id="default")
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any


class ContextManager:
    """Zarządza kontekstem modyfikacji plików między sesjami AI.

    Przechowuje:
        - Ślad wszystkich zmodyfikowanych plików (ścieżka → hash)
        - Aktualne wersje plików w `_system/contexts/`
        - Log zmian z timestampami
    """

    def __init__(self, context_dir: str | None = None) -> None:
        self.context_dir = context_dir or os.path.join("_projects", "_system", "contexts")
        os.makedirs(self.context_dir, exist_ok=True)

        # Śledzenie modyfikacji: {file_path: {"hash": ..., "content_hash": ...}}
        self._modified_files: dict[str, dict[str, Any]] = {}
        self._last_save_time: str | None = None

    # ------------------------------------------------------------------
    # Tracking API
    # ------------------------------------------------------------------

    def track_modification(
        self,
        file_path: str,
        new_content: str | None = None,
        operation: str = "modified",
    ) -> dict[str, Any]:
        """Zarejestruj modyfikację pliku.

        Args:
            file_path: Ścieżka do zmodyfikowanego pliku (względem projektu).
            new_content: Nowa zawartość pliku (opcjonalnie — zapisywana do snapshotu).
            operation: Typ operacji ("modified", "created", "deleted").

        Returns:
            Rejestr modyfikacji z metadanymi.
        """
        # Oblicz hash nowej treści (jeśli podano)
        content_hash = None
        if new_content is not None:
            content_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()

        modification_entry = {
            "file_path": file_path,
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": content_hash,
        }

        self._modified_files[file_path] = modification_entry

        # Zapisz zawartość do kontekstowego pliku (jeśli podano)
        if new_content is not None:
            self._save_file_snapshot(file_path, new_content)

        return modification_entry

    def get_modified_files(self) -> list[str]:
        """Zwrot listy ścieżek wszystkich zmodyfikowanych plików."""
        return list(self._modified_files.keys())

    def has_modifications(self) -> bool:
        """Sprawdź czy są niezapisane modyfikacje."""
        return len(self._modified_files) > 0

    # ------------------------------------------------------------------
    # Snapshot Persistence (Context State)
    # ------------------------------------------------------------------

    def save_context_snapshot(
        self,
        project_id: str = "default",
        include_contents: bool = True,
    ) -> str:
        """Zapisz pełny kontekst modyfikacji do pliku JSON.

        Args:
            project_id: ID projektu (np. "default").
            include_contents: Czy zapisać zawartość plików (True) czy tylko metadane (False).

        Returns:
            Ścieżka zapisanego pliku kontekstu.
        """
        filepath = os.path.join(self.context_dir, f"context_{project_id}.json")

        snapshot_data = {
            "project_id": project_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modified_files_count": len(self._modified_files),
            "files": {},
        }

        for file_path, meta in self._modified_files.items():
            snapshot_data["files"][file_path] = meta.copy()

            # Opcjonalnie zapisz zawartość pliku (dla pełnego kontekstu)
            if include_contents and os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        snapshot_data["files"][file_path]["content"] = f.read()
                except (IOError, UnicodeDecodeError):
                    snapshot_data["files"][file_path]["content"] = None

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)

        self._last_save_time = datetime.now(timezone.utc).isoformat()
        return filepath

    def load_context(
        self,
        project_id: str = "default",
        restore_contents: bool = False,
    ) -> dict[str, Any] | None:
        """Wczytaj kontekst modyfikacji z pliku JSON.

        Args:
            project_id: ID projektu do wczytania.
            restore_contents: Czy przywrócić zawartość plików (True) czy tylko metadane (False).

        Returns:
            Wczytany stan kontekstu lub None jeśli brak zapisu.
        """
        filepath = os.path.join(self.context_dir, f"context_{project_id}.json")

        if not os.path.exists(filepath):
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Wczytaj tylko metadane (bez treści plików — szybciej)
        loaded_data = {
            "project_id": data.get("project_id"),
            "timestamp": data.get("timestamp"),
            "modified_files_count": len(data.get("files", {})),
            "files": {},
        }

        for file_path, meta in data.get("files", {}).items():
            entry = {k: v for k, v in meta.items() if k != "content"}
            loaded_data["files"][file_path] = entry

        # Opcjonalnie przywróć zawartość plików na dysk
        if restore_contents and data.get("files"):
            self._restore_file_contents(data["files"])

        return loaded_data

    def get_context_summary(self, project_id: str = "default") -> dict[str, Any]:
        """Podsumowanie kontekstu modyfikacji (tylko metadane)."""
        context = self.load_context(project_id=project_id)
        if context is None:
            return {"status": "no_context", "message": f"Brak kontekstu dla projektu '{project_id}'"}

        file_ops = {}
        for meta in context.get("files", {}).values():
            op = meta.get("operation", "unknown")
            file_ops[op] = file_ops.get(op, 0) + 1

        return {
            "status": "loaded",
            "project_id": context["project_id"],
            "timestamp": context["timestamp"],
            "total_modifications": context["modified_files_count"],
            "operations_breakdown": file_ops,
        }

    # ------------------------------------------------------------------
    # File Snapshot Management
    # ------------------------------------------------------------------

    def _save_file_snapshot(self, file_path: str, content: str) -> None:
        """Zapisz zawartość pliku do kontekstowego katalogu."""
        snapshot_dir = os.path.join(self.context_dir, "snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)

        # Zamień separator ścieżki na underscore (bezpieczne dla nazw plików)
        safe_name = file_path.replace(os.sep, "_").replace("/", "_") + ".bak"
        snapshot_filepath = os.path.join(snapshot_dir, safe_name)

        with open(snapshot_filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def _restore_file_contents(self, files_data: dict[str, Any]) -> None:
        """Przywróć zawartość plików z danych kontekstu na dysk."""
        snapshot_dir = os.path.join(self.context_dir, "snapshots")

        for file_path, meta in files_data.items():
            if "content" not in meta or meta["content"] is None:
                continue

            safe_name = file_path.replace(os.sep, "_").replace("/", "_") + ".bak"
            snapshot_filepath = os.path.join(snapshot_dir, safe_name)

            if os.path.exists(snapshot_filepath):
                with open(snapshot_filepath, "r", encoding="utf-8") as f:
                    restored_content = f.read()

                # Zapisz przywróconą zawartość na oryginał
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(restored_content)

    # ------------------------------------------------------------------
    # Cleanup & Reset
    # ------------------------------------------------------------------

    def clear_modifications(self) -> None:
        """Wyczyść listę śledzonych modyfikacji (po zapisaniu)."""
        self._modified_files.clear()

    def get_all_snapshot_paths(self) -> list[str]:
        """Zwrot listy wszystkich plików snapshotów."""
        snapshot_dir = os.path.join(self.context_dir, "snapshots")
        if not os.path.isdir(snapshot_dir):
            return []

        return [
            os.path.join(snapshot_dir, f)
            for f in sorted(os.listdir(snapshot_dir))
            if f.endswith(".bak")
        ]


if __name__ == "__main__":
    manager = ContextManager()

    # Demo track modyfikacji
    manager.track_modification(
        file_path="modules/polish_greeting.py",
        new_content="# Hello World\nprint('test')",
        operation="modified",
    )

    manager.save_context_snapshot(project_id="default")

    print("=== Context Summary ===")
    summary = manager.get_context_summary()
    print(json.dumps(summary, indent=2))
