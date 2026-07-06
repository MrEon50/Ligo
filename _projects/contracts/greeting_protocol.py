"""Greeting Service Contract — Definicja interfejsu modułu powitań.

Ten plik definiuje TYLKO kontrakt (abstrakcyjną klasę / typ).
Zawiera ZERO logiki biznesowej. Jest to "Co" moduł robi, nie "Jak".
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class GreetingServiceProtocol(ABC):
    """Kontrakt dla każdego modułu generującego powitania.

    Każdy implementujący ten kontrakt musi:
      - być stateless (nie trzymać stanu wewnątrz instancji)
      - nie importować innych modułów bezpośrednio
      - przyjmować parametr 'name' i opcjonalny 'context'
    """

    @abstractmethod
    def greet(self, name: str, context: dict | None = None) -> str:
        """Wygeneruj powitanie dla podanej osoby.

        Args:
            name: Imię lub nazwa odbiorcy powitania (np. "Alice", "World").
            context: Opcjonalny słownik z dodatkowym kontekstem, np. {"hour": 14}
                     dla dopasowania pory dnia.

        Returns:
            Wygenerowany tekst powitania jako string.
        """
        ...

    @abstractmethod
    def get_service_info(self) -> dict[str, str]:
        """Zwróć metadane modułu (np. nazwę, wersję, język).

        Returns:
            Słownik z kluczami takimi jak "service_name", "language", "version".
        """
        ...