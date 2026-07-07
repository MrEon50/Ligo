"""AI Parameters — stateless manager with built-in task profiles.

Stosowane profile:
    - default         : domyślne parametry (temperature 0.7)
    - coding          : precyzyjne generowanie kodu (temp 0.2)
    - planning        : strukturalne planowanie (temp 0.4)
    - brainstorming   : kreatywne generowanie pomysłów (temp 0.9)
    - debugging       : dokładna analiza błędów (temp 0.1)

Każdy profil zawiera:
    temperature     : losowość odpowiedzi (0.0 = precyzyjnie, 1.0 = kreatywnie)
    max_tokens      : maksymalna długość odpowiedzi
    top_p           : nucleus sampling threshold
    presence_penalty: kara za powtarzanie treści (0-2)

Użycie:
    >>> from modules.ai_params import AIParamsService
    >>> svc = AIParamsService()
    >>> svc.get_profile('coding')
    {'temperature': 0.2, 'max_tokens': 4096, ...}
"""

from __future__ import annotations

import abc
from typing import Any


class AIParametersProtocol(abc.ABC):
    """Abstrakcyjny interfejs — fallback gdy kontrakty nie są dostępne."""


try:
    from contracts.ai_params_protocol import AIParametersProtocol  # type: ignore[no-redef]
except ImportError:
    pass  # fallback ABC — pozwala na standalone execution bez pełnego projektu


class AIParamsService(AIParametersProtocol):
    """Stateless manager parametrów AI z wbudowanymi profilami."""

    _VERSION = "1.0.0"

    # Domyślne wartości globalne (niezmienne w ramach sesji — stateless!)
    DEFAULTS: dict[str, float] = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "top_p": 0.9,
        "presence_penalty": 0.5,
    }

    # Profil default (domyślny) — zbalansowany dla większości zadań
    PROFILES: dict[str, dict[str, Any]] = {
        "default": {
            **DEFAULTS,
            "description": "Domyślne parametry — uniwersalne zastosowanie",
        },
        "coding": {
            **DEFAULTS,
            "temperature": 0.15,  # bardzo precyzyjny kod
            "max_tokens": 8192,    # dłuższe odpowiedzi dla kompletnych funkcji
            "top_p": 0.75,         # skupiony na najbardziej prawdopodobnych tokenach
            "presence_penalty": 0.3,
            "description": "Precyzyjne generowanie kodu — niska temperatura i top_p",
        },
        "planning": {
            **DEFAULTS,
            "temperature": 0.45,   # umiarkowana kreatywność dla struktury
            "max_tokens": 6144,
            "top_p": 0.85,         # balans między precyzją a elastycznością
            "presence_penalty": 0.5,
            "description": "Strukturalne planowanie — umiarkowana temperatura",
        },
        "brainstorming": {
            **DEFAULTS,
            "temperature": 1.2,    # wysoka kreatywność (user's suggestion)
            "max_tokens": 4096,
            "top_p": 0.6,          # niższe top_p = bardziej spójne pomysły mimo wysokiej temp
            "presence_penalty": 0.8,
            "description": "Kreatywne generowanie pomysłów — wysoka temperatura",
        },
        "debugging": {
            **DEFAULTS,
            "temperature": 0.1,    # minimalna losowość dla dokładnej analizy
            "max_tokens": 4096,
            "top_p": 0.65,         # skupione na najdokładniejszych tokenach
            "presence_penalty": 0.2,
            "description": "Dokładna analiza błędów — minimalna temperatura",
        },
    }

    def get_profile(self, name: str) -> dict[str, Any]:
        """Pobierz profil o podanej nazwie.

        Args:
            name: Nazwa profilu (np. 'coding', 'planning').

        Returns:
            Słownik z parametrami AI.

        Raises:
            KeyError: Jeśli profil nie istnieje.
        """
        if name not in self.PROFILES:
            raise KeyError(
                f"Profil '{name}' nie istnieje. Dostępne: {', '.join(self.list_profiles())}"
            )
        return dict(self.PROFILES[name])  # zwracamy kopię — stateless!

    def list_profiles(self) -> list[str]:
        """Zwróć listę dostępnych profili."""
        return sorted(self.PROFILES.keys())

    def create_custom_profile(
        self, name: str, **overrides: float
    ) -> dict[str, Any]:
        """Utwórz własny profil na podstawie default z nadpisaniem parametrów.

        Args:
            name: Nazwa nowego profilu (np. 'my_favorite').
            overrides: Parametry do nadpisania (temperature, top_p, itp.)

        Returns:
            Słownik z nowym profilem.
        """
        new_profile = dict(self.PROFILES["default"])
        for key, value in overrides.items():
            if key not in self.DEFAULTS and key != "description":
                raise ValueError(f"Nieznany parametr: {key}")
            new_profile[key] = value

        self.PROFILES[name] = new_profile
        return dict(new_profile)  # zwracamy kopię — stateless!

    def save_custom_profile(
        self, name: str, filepath: str | Path
    ) -> None:
        """Zapisz własny profil do pliku JSON.

        Args:
            name: Nazwa profilu do zapisania.
            filepath: Ścieżka do pliku wyjściowego.
        """
        import json
        from pathlib import Path as _Path

        profile = self.get_profile(name)
        # Usuń description z JSON (to metadata, nie parametr AI)
        data = {k: v for k, v in profile.items() if k != "description"}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_custom_profile(self, filepath: str | Path) -> dict[str, Any]:
        """Załaduj profil z pliku JSON i dodaj do dostępnych.

        Args:
            filepath: Ścieżka do pliku wejściowego.

        Returns:
            Słownik załadowanego profilu.
        """
        import json
        from pathlib import Path as _Path

        path = _Path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Wygeneruj nazwę z nazwy pliku (bez rozszerzenia)
        name = path.stem.replace("-", "_").replace(" ", "_")
        if name in self.PROFILES:
            raise ValueError(f"Profil '{name}' już istnieje!")

        data["description"] = f"Wczytany profil: {path.name}"
        self.PROFILES[name] = data
        return dict(data)  # zwracamy kopię — stateless!

    def delete_custom_profile(self, name: str) -> bool:
        """Usuń własny profil.

        Args:
            name: Nazwa profilu do usunięcia.

        Returns:
            True jeśli usunięto, False jeśli nie znaleziono.
        """
        if name in self.PROFILES and name != "default":
            del self.PROFILES[name]
            return True
        return False

    def reset_to_default(self) -> dict[str, Any]:
        """Resetuj do domyślnego profilu ('default').

        Returns:
            Parametry domyślnego profilu.
        """
        return self.get_profile("default")

    def get_service_info(self) -> dict[str, str]:
        """Zwróć metadane tego modułu."""
        return {
            "service_name": "AIParamsService",
            "version": self._VERSION,
            "description": "Stateless manager parametrów AI z wbudowanymi profilami zadań i wsparciem dla ulubionych ustawień",
            "profiles_count": str(len(self.PROFILES)),
            "default_profile": "default",
        }


if __name__ == "__main__":
    """Demo — przetestuj dostępne profile."""
    svc = AIParamsService()

    print("=== AI Parameters Demo ===\n")
    print(f"Dostępne profile: {svc.list_profiles()}")
    print()

    for name in svc.list_profiles():
        params = svc.get_profile(name)
        desc = params.pop("description", "")
        temp = params["temperature"]
        tokens = params["max_tokens"]
        print(f"  {name:15s} → temperature={temp}, max_tokens={tokens}")
        print(f"                  {desc}")

    # Reset to default demo
    print("\nReset do domyślnego:")
    print(svc.reset_to_default())
