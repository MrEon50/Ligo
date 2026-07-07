"""English Greeting Module — Implementation of English greeting service.

Stateless, self-contained module implementing the GreetingServiceProtocol contract.
Does NOT import any other modules from /modules directly.
"""

from __future__ import annotations

import datetime as dt
from typing_extensions import final

from contracts.greeting_protocol import GreetingServiceProtocol


@final
class EnglishGreetingService(GreetingServiceProtocol):
    """Module generating greetings in English based on time of day.

    Stateless — holds no state within the instance.
    Every ``greet`` call is deterministic for the same input.
    """

    _LANGUAGE: str = "en"
    _VERSION: str = "1.0.0"

    def greet(self, name: str, context: dict | None = None) -> str:
        """Generate an English greeting considering time of day.

        Args:
            name: Recipient's name (e.g., "Alice", "World").
            context: Optional dictionary containing e.g. {"hour": 14}.
                     If provided, selects the appropriate greeting form.

        Returns:
            Greeting text in English.
        
        Granice godzinowe:
            - noc:   0-5,  22-23
            - rano:  6-11
            - popołudnie: 12-17
            - wieczór: 18-21
        """
        hour = self._extract_hour(context)

        if hour < 6:
            prefix = "Good night"
        elif hour < 12:
            prefix = "Good morning"
        elif hour < 18:
            prefix = "Good afternoon"
        elif hour < 22:
            prefix = "Good evening"
        else:
            prefix = "Good night"  # >= 22

        return f"{prefix}, {name}!"

    def get_service_info(self) -> dict[str, str]:
        """Return metadata about this module."""
        return {
            "service_name": "EnglishGreetingService",
            "language": self._LANGUAGE,
            "version": self._VERSION,
            "description": f"English greeting service (v{self._VERSION})",
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_hour(context: dict | None) -> int:
        """Extract hour from context or fall back to current system time.

        Args:
            context: Optional dictionary containing a "hour" key.

        Returns:
            Hour (0-23). Defaults to current UTC+2 time when no context provided.
        """
        if context and "hour" in context:
            return int(context["hour"]) % 24

        tz_info = dt.timezone(dt.timedelta(hours=2))
        now = dt.datetime.now(tz=tz_info)
        return now.hour