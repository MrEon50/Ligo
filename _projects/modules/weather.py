"""Weather Service — stateless implementation of WeatherServiceProtocol.

Kontakty:
    Zawsze wymaga istnienia contracts/weather_protocol.py.
    Brak fallbacku — ImportError jest jawny i natychmiastowy.

Użycie:
    from registry.service_registry import ServiceRegistry
    
    registry = ServiceRegistry()
    registry.register(
        key="weather",
        instance=WeatherService(),
        contract_type=WeatherServiceProtocol,
    )
"""

from __future__ import annotations

import json
from typing import Any

# Jawny import — bez fallbacku! Jeśli contracts/weather_protocol.py nie istnieje,
# ImportError zostanie rzucony natychmiast (nie ukryty).
from contracts.weather_protocol import WeatherServiceProtocol  # noqa: F401


class WeatherService:
    """Stateless service for weather data.

    No instance attributes are stored between method calls.
    All operations are deterministic given the same input.
    """

    VERSION: str = "1.0.0"
    
    def get_service_info(self) -> dict[str, Any]:
        """Zwraca metadane usługi."""
        return {
            "service_name": "WeatherService",
            "language": "en",  # ISO 639-1: en (English), nie "we" (błędny kod)
            "version": self.VERSION,
            "description": "Weather service",
            "methods": ["get_info", "forecast"],
        }

    def forecast(self, *args: Any, **kwargs: Any) -> Any:
        """TODO — implementuj w module."""
        return None

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        """Wywołanie usługi — implementacja domyślna."""
        # f-string zamiast .format() dla lepszej czytelności
        return f"{self.__class__.__name__}: called with {len(args)} args, {len(kwargs)} kwargs"