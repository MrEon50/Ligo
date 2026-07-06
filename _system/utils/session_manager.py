"""Session Manager — trwale przechowywanie stanu między sesjami AI.

Zamiast trzymać stan w pamięci (singleton), SessionManager zapisuje stan
rejestratora do plików JSON w `_system/sessions/` i pozwala na odtworzenie
go po restarcie sesji AI.

Format snapshotu:
    {
      "project_id": "mvg",
      "created_at": "...",
      "services": {"greeting.pl": {"class_name": ..., "module_path": ...}},
      "contracts": {"greeting.pl": "GreetingServiceProtocol"},
      "last_updated": "..."
    }

Używa struktury folderów:
    _projects/
        sessions/              # pliki JSON z stanem rejestratorów
            <project_id>.json  # jeden plik na projekt (opcjonalnie)
"""

from __future__ import annotations

import json
import os
import datetime as dt
from typing import Any


class SessionManager:
    """Zarządza trwałą pamięcią stanu między sesjami AI.

    Przechowuje:
        - Stan rejestratora usług (klucze, klasy modułów)
        - Metadane kontraktów
        - Log błędów z historyj
    """

    def __init__(self, session_dir: str | None = None) -> None:
        self.session_dir = session_dir or "_system/sessions"
        os.makedirs(self.session_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save_registry_state(
        self,
        project_id: str,
        services: dict[str, Any],
        contracts: dict[str, str | None],
    ) -> str:
        """Zapisz stan rejestratora do pliku JSON.

        Args:
            project_id: ID projektu (np. "mvg").
            services: słownik {key: {"class_name": ..., "module_path": ...}}.
            contracts: słownik {key: "ContractClassName"}.

        Returns:
            Ścieżka zapisanego pliku.
        """
        filepath = self._get_filepath(project_id)
        state = {
            "project_id": project_id,
            "services": services,
            "contracts": contracts,
            "timestamp": dt.datetime.now().isoformat(),
            "version": "1.0",
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        return filepath

    def load_registry_state(self, project_id: str | None = None) -> dict[str, Any] | None:
        """Wczytaj stan rejestratora z pliku JSON.

        Args:
            project_id: ID projektu (opcjonalnie). Jeśli None — wczytuje globalny stan.

        Returns:
            Stan rejestratora lub None jeśli nie ma zapisanego stanu.
        """
        if project_id is not None:
            filepath = self._get_filepath(project_id)
        else:
            filepath = os.path.join(self.session_dir, "global.json")

        if not os.path.exists(filepath):
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "project_id": data.get("project_id"),
            "services": data.get("services", {}),
            "contracts": data.get("contracts", {}),
        }

    def save_session_log(
        self,
        project_id: str,
        log_entry: dict[str, Any],
    ) -> None:
        """Dodaj wpis do sesji projektu."""
        filepath = os.path.join(self.session_dir, f"{project_id}_log.json")
        logs = [] if not os.path.exists(filepath) else json.load(open(filepath))

        entry_with_ts = {
            "timestamp": dt.datetime.now().isoformat(),
            **log_entry,
        }

        logs.append(entry_with_ts)

        # Ogranicz do ostatnich 100 wpisów
        if len(logs) > 100:
            logs = logs[-100:]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    def get_session_log(self, project_id: str | None = None) -> list[dict[str, Any]]:
        """Pobierz log sesji."""
        if project_id is not None:
            filepath = os.path.join(self.session_dir, f"{project_id}_log.json")
        else:
            filepath = os.path.join(self.session_dir, "global_log.json")

        if not os.path.exists(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [dict(item) for item in data]

    # ------------------------------------------------------------------
    # Auto-Save on Modification (Meta-Cycling Feature A)
    # ------------------------------------------------------------------

    def auto_save_on_modification(
        self,
        project_id: str,
        services: dict[str, Any],
        contracts: dict[str, str | None],
        modification_log: list[dict[str, Any]] | None = None,
    ) -> tuple[str, int]:
        """Automatycznie zapisz stan po każdej modyfikacji.

        Zapisuje aktualny stan rejestratora ORAZ log modyfikacji do osobnego pliku.
        Umożliwia przywrócenie stanu z dowolnego momentu w sesji AI.

        Args:
            project_id: ID projektu.
            services: Aktualny stan usług.
            contracts: Aktualne kontrakty.
            modification_log: Opcjonalna lista modyfikacji do zapisania.

        Returns:
            Tuple (saved_filepath, total_modifications).
        """
        # Zapisz główny stan rejestratora
        state_path = self.save_registry_state(project_id, services, contracts)

        # Jeśli podano log modyfikacji — zapisz go osobno
        if modification_log is not None and len(modification_log) > 0:
            mod_log_path = os.path.join(self.session_dir, f"{project_id}_modifications.json")
            with open(mod_log_path, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {**entry, "timestamp": dt.datetime.now().isoformat()}
                        for entry in modification_log[-50:]  # Ostatnie 50 modyfikacji
                    ],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            return mod_log_path, len(modification_log)

        return state_path, 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_filepath(self, project_id: str) -> str:
        """Generuj ścieżkę do pliku sesji projektu."""
        return os.path.join(self.session_dir, f"{project_id}.json")
