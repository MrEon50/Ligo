"""Helper functions for time-based greetings.

Centralizes all logic for determining time-of-day periods and generating
greeting messages in supported languages.

Usage:
    from _utils.time_greeting_helper import get_greeting_period, format_greeting
    
    period = get_greeting_period(14)  # -> GreetingPeriod.AFTERNOON
    greeting = format_greeting("pl", period, "Ania")  # -> "Dobry dzień, Ania!"
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Dict

# StrEnum dostępny od Python 3.11, dla starszych wersji używamy fallbacku
if sys.version_info >= (3, 11):
    from enum import StrEnum as _BaseGreetingEnum
else:
    class _BaseGreetingEnum(str, Enum):
        """Polyfill for StrEnum (available from Python 3.11+)."""
        pass


class GreetingPeriod(_BaseGreetingEnum):
    """Okres dnia dla powitań."""

    NIGHT = "night"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


def get_greeting_period(hour: int) -> GreetingPeriod:
    """Zwraca okres dnia na podstawie godziny (0-23).

    Granice:
        - noc:   0-5,  22-23
        - rano:  6-11
        - popołudnie: 12-17
        - wieczór: 18-21

    Args:
        hour: Godzina (0-23).

    Returns:
        GreetingPeriod — jeden z: NIGHT, MORNING, AFTERNOON, EVENING.

    Raises:
        ValueError: Jeśli hour nie jest z zakresu 0-23.
    """
    if not isinstance(hour, int) or hour < 0 or hour > 23:
        raise ValueError(f"hour musi być liczbą całkowitą z zakresu 0-23, dostałem: {hour}")

    if 6 <= hour < 12:
        return GreetingPeriod.MORNING
    elif 12 <= hour < 18:
        return GreetingPeriod.AFTERNOON
    elif 18 <= hour < 22:
        return GreetingPeriod.EVENING
    else:
        return GreetingPeriod.NIGHT


# Słowniki powitań dla każdego języka
GREETING_TEMPLATES: Dict[str, Dict[GreetingPeriod, str]] = {
    "pl": {
        GreetingPeriod.NIGHT: "Dobranoc",
        GreetingPeriod.MORNING: "Dzień dobry",
        GreetingPeriod.AFTERNOON: "Dobry dzień",
        GreetingPeriod.EVENING: "Dobry wieczór",
    },
    "en": {
        GreetingPeriod.NIGHT: "Good night",
        GreetingPeriod.MORNING: "Good morning",
        GreetingPeriod.AFTERNOON: "Good afternoon",
        GreetingPeriod.EVENING: "Good evening",
    },
}


def format_greeting(
    language: str,
    period: GreetingPeriod,
    name: str,
) -> str:
    """Generuje sformułowane powitanie.

    Args:
        language: Kod języka (ISO 639-1), np. "pl", "en".
                  Nieznane języka mają fallback na angielski.
        period: Okres dnia (z GreetingPeriod).
        name: Imię odbiorcy powitania.

    Returns:
        Sformatowany tekst powitania, np. "Dzień dobry, Ania!".
    """
    templates = GREETING_TEMPLATES.get(language, GREETING_TEMPLATES["en"])
    prefix = templates.get(period, templates[GreetingPeriod.MORNING])
    return f"{prefix}, {name}!"