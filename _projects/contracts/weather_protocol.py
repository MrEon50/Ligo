"""Weather Protocol — ABC kontrakt dla WeatherService.

Ten plik definiuje interfejs (ABSTRACT BASE CLASS), który implementacje muszą spełnić.
Moduły w _projects/modules/ implementują ten protokół jako stanless usługi.

Użycie:
    from contracts.weather_protocol import WeatherServiceProtocol
    
    @dataclass
    class MyService(WeatherServiceProtocol):
        def get_info(self, *args, **kwargs) -> Any:
            return {...}
"""

from __future__ import annotations

import abc
from typing import Any


class WeatherServiceProtocol(abc.ABC):
    """Abstract base class defining the interface for WeatherService.

    All methods must be implemented by concrete service classes.
    The protocol ensures type-safety and architecture compliance.
    """
    @abc.abstractmethod
    def get_info(self, *args: Any, **kwargs: Any) -> Any:
        """get_info — implementacja w module."""
        ...
    @abc.abstractmethod
    def forecast(self, *args: Any, **kwargs: Any) -> Any:
        """forecast — implementacja w module."""
        ...
