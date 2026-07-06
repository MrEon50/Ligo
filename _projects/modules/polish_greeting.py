"""Polish Greeting Module — Implementacja modułu powitań po polsku.

Stateless, zamknięty moduł. Nie importuje żadnych innych modułów z /modules.
Zgodny z kontraktem GreetingServiceProtocol.
"""

from __future__ import annotations

import datetime as dt
from typing_extensions import final

from contracts.greeting_protocol import GreetingServiceProtocol


@final
class PolishGreetingService(GreetingServiceProtocol):
    """Moduł generujący powitania w języku polskim.

    Stanless — nie przechowuje żadnego stanu wewnątrz instancji.
    Każdy wywołanie metody ``greet`` jest deterministyczne dla tego samego inputu.
    """

    _LANGUAGE = "pl"
    _VERSION = "1.0.0"

    def greet(self, name: str, context: dict | None = None) -> str:
        """Wygeneruj polskie powitanie z uwzględnieniem pory dnia.

        Args:
            name: Imię odbiorcy (np. "Ania", "Tomek").
            context: Opcjonalny słownik, np. {"hour": 14}.
                     Jeśli podany — dopasuj porę dnia do odpowiedniej formy.

        Returns:
            Tekst powitania w języku polskim.
        """
        hour = self._extract_hour(context)

        if hour < 6:
            prefix = "Dobranoc"
        elif hour < 12:
            prefix = "Dzień dobry"
        elif hour < 18:
            prefix = "Dobry wieczór"
        else:
            prefix = "Dobranoc"

        return f"{prefix}, {name}!"

    def get_service_info(self) -> dict[str, str]:
        """Zwróć metadane tego modułu."""
        return {
            "service_name": "PolishGreetingService",
            "language": self._LANGUAGE,
            "version": self._VERSION,
            "description": f"Moduł powitań w języku polskim (v{self._VERSION})",
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_hour(context: dict | None) -> int:
        """Wyciągnij godzinę z kontekstu lub użyj aktualnej godziny systemowej.

        Args:
            context: Słownik opcjonalnie zawierający klucz "hour".

        Returns:
            Godzina (0-23). Domyślnie godzina aktualna w strefie UTC+2.
        """
        if context and "hour" in context:
            return int(context["hour"]) % 24

        tz_info = dt.timezone(dt.timedelta(hours=2))
        now = dt.datetime.now(tz=tz_info)
        return now.hour