# 🛠️ TECH_STACK — Stos Technologiczny i Standardy LIGO 1.1

**Projekt:** LIGO  
**Wersja:** 1.1 (Safe-Zone)  
**Ostatnia aktualizacja:** 2026-07-04T16:16:00+02:00

---

## §1. Stos Technologiczny

| Komponent | Technologie | Uwagi |
|-----------|-------------|-------|
| Język | Python 3.10+ | Typ hinting, Protocol (typing_extensions) |
| Architektura | 4-warstwowa (Contract → Registry → Module → Orchestrator) | Bezpośrednie importy między modułami zabronione |
| Testy | pytest | Wymagane testy jednostkowe dla każdego nowego modułu |
| Logi | logging z FileHandler | Format: `TIMESTAMP | LEVEL | MODULE | MESSAGE | CONTEXT_JSON` |
| Kontrakty | typing.Protocol + @runtime_checkable | Walidacja przy rejestracji w ServiceRegistry |

---

## §2. Standardy Kodowania

1. **Type Hints** — wszystkie funkcje muszą mieć pełne type hints (parametry i返回值)
2. **Docstrings** — każda publiczna klasa i funkcja musi zawierać docstring z opisem `Args:`, `Returns:`
3. **Stateless Modules** — żaden stan wewnątrz instancji modułu; dane wejściowe przez parametry metody
4. **Final Classes** — moduły oznaczane jako `@final` (zakaz dziedziczenia modyfikacji)
5. **No Direct Imports Between Modules** — komunikacja wyłącznie przez Registry lub Orchestrator

---

## §3. Struktura Folderów (Safe-Zone)

```text
Ligo/
├── _system/                    # STREFA ZABRONIONA (Read-Only dla AI)
│   ├── project_anchor.md       # Konstytucja — nie modyfikuj!
│   └── tech_stack.md           # Standardy technologiczne — nie modyfikuj!
│
├── _hub/                       # CENTRUM KOMEND (Planowanie)
│   ├── current_task.md         # Jedyne miejsce na opisywanie zamiarów
│   └── master_prompt_ligo_1.1.md  # Master Prompt agenta
│
├── _projects/                  # WARSZTAT (Kod aplikacji)
│   ├── contracts/              # Kontrakty (protokoły) — definicje interfejsów
│   ├── registry/               # Klej — rejestracja i logowanie usług
│   ├── modules/                # Implementacje — stanless moduły
│   ├── orchestrator/           # Logika biznesowa i integracja
│   ├── tests/                  # Testy jednostkowe
│   └── snapshots/              # Pamięć robocza (snapshoty)
│
├── snapshots/                  # PAMIĘĆ (Historyczne snapshoty)
└── scratchpad.md               # Eksperymentalne myślenie AI
```

---

## §4. Zasady Bezpieczeństwa

### Importy wewnątrz `_projects/`
- `from contracts.greeting_protocol import GreetingServiceProtocol` ✅
- `from registry.service_registry import ServiceRegistry` ✅
- `from modules.polish_greeting import PolishGreetingService` ✅ (tylko z orchestratora)
- `from modules.polish_greeting import EnglishGreetingService` ❌ NIE!

### Ścieżki do plików konfiguracyjnych
Wszystkie ścieżki relative do `_projects/`:
```python
import os, sys
_PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")  # _projects/
sys.path.insert(0, _PROJECT_ROOT)
```

---

## §5. Workflow (Protokół Ligo 1.1)

### Krok 1: Analiza
- Przeczytaj `_system/project_anchor.md` i `_hub/current_task.md`
- Zidentyfikuj bieżący Checkpoint z `project_anchor.md`

### Krok 2: Propozycja
- Jeśli zadanie nie jest opisane w Hubie → wpisz plan w `_hub/current_task.md`
- Czekaj na akceptację (w wersji autonomicznej — samoczynna walidacja)

### Krok 3: Implementacja + Snapshot
- Stwórz kontrakt w `/contracts/`
- Zaimplementuj moduł w `/modules/` (stateless, @final)
- Zarejestruj w `/registry/service_registry.py`
- Napisz testy w `/tests/`

### Krok 4: Weryfikacja Architektoniczna
Przed każdym commitem kodu AI musi odpowiedzieć:
1. "Czy to narusza Twarde Granice w `_system/`?" → NIE
2. "Czy moduł jest stateless?" → TAK
3. "Czy są bezpośrednie importy między modułami?" → NIE

---

## §6. Zasada 3 Błędów

Jeśli ten sam problem (np. naruszenie stateless, bezpośredni import) wystąpi **3 razy** — natychmiast przestań pisać kod i zgłoś w `_hub/current_task.md`:
- Opis problemu źródłowego
- Propozycja zmiany architektonicznej
- Alternatywne podejście