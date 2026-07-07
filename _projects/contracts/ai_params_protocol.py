"""AI Parameters Protocol — interface dla modułu konfiguracji parametrów AI."""

from __future__ import annotations

import abc
from typing import Any


class AIParametersProtocol(abc.ABC):
    """Kontrakt dla modułu zarządzania parametrami AI.

    Każdy profil definiuje zestaw hiperparametrów (temperature, max_tokens, itp.),
    które wpływają na zachowanie modelu AI w zależności od kontekstu zadania.
    """

    @abc.abstractmethod
    def get_profile(self, name: str) -> dict[str, Any]:
        """Pobierz profil o podanej nazwie."""

    @abc.abstractmethod
    def list_profiles(self) -> list[str]:
        """Zwróć listę dostępnych profili."""

    @abc.abstractmethod
    def reset_to_default(self) -> dict[str, Any]:
        """Resetuj do domyślnego profilu ('default')."""
