# 🏛️ PROJECT ANCHOR — Konstytucja LIGO 2.0 (Multi-Project Safe-Zone)

**Projekt:** LIGO v2.0 — Multi-Project Framework Inżynierii Modułowej  
**Wersja:** 2.0 (Safe-Zone + Multi-Project Support)  
**Ostatnia aktualizacja:** 2026-07-06T23:46:00+02:00

---

## §1. Cel Projektu

LIGO v2.0 to multi-project framework inżynierii modułowej, który wymusza **architektoniczną dyscyplinę** na każdym etapie rozwoju oprogramowania.  
Fundamentem jest podział na 5 warstw: Kontrakt → Rejestracja → Moduł → Orkiestrator + Utils (loop prevention, session persistence, architecture validation).

### Wersja 2.0 dodaje względem 1.1:
- **P0**: Loop prevention — CallDepthGuard blokuje rekurencję i infinite loops
- **P1**: Session state persistence — JSON snapshoty stanu rejestratora między sesjami AI
- **P1**: Runtime architecture validation — automatyczna walidacja cross-module imports + statefulness
- **P2**: Multi-project support — każdy podfolder w `projects/` to osobny, izolowany projekt

---

## §2. Zasady Absolutne (Niedyskutowalne)

1. **Stateless Modules** — każdy moduł w `/modules/` musi być bezstanowy
2. **No Cross-Module Imports** — moduły nie importują się bezpośrednio między sobą; komunikacja wyłącznie przez Registry lub Orchestrator
3. **Contract First** — przed implementacją każdego modułu musi istnieć kontrakt w `/contracts/`
4. **Registry as Glue** — rejestracja usług odbywa się TYLKO przez ServiceRegistry v2.0 w `/registry/`
5. **Loop Prevention** — CallDepthGuard blokuje rekurencję (max_depth=20)
6. **Session Persistence** — stan rejestratora zapisywany do JSON po każdym cyklu
7. **Architecture Validation** — automatyczna walidacja przed rejestracją nowych modułów

---

## §3. Zasady Dostępu do Plików (Safe-Zone v2.0)

| Kategoria | Ścieżka | Prawo dostępu AI |
|-----------|---------|-----------------|
| **STREFA ZABRONIONA** | `_system/*` | TYLKO DO ODCZYTU. Modyfikacja = natychmiastowe zakończenie sesji. |
| **CENTRUM KOMEND** | `_hub/current_task.md` | Jedyne miejsce do opisywania zamiarów, propozycji zmian, planów. |
| **WARSZTAT (zapis)** | `_projects/*` | Pełny dostęp do zapisu — tu powstaje kod frameworka LIGO. |
| **PROJEKTY** | `projects/<nazwa>/` | Pełny dostęp do zapisu — tu budujesz aplikacje domenowe. |
| **PAMIĘĆ** | `_projects/snapshots/` | Zapis po każdym cyklu (JSON format). |

---

## §4. Decision Log

| Data | Decyzja | Powód |
|------|---------|-------|
| 2026-07-04T16:00 | Migracja do architektury Ligo 1.1 Safe-Zone | Zapobieganie "nadgorliwości" AI — blokada modyfikacji `_system/` |
| 2026-07-06T23:46 | Migracja do Ligo v2.0 — Multi-Project + Loop Prevention | Ulepszenia P0-P2: zapobieganie loops, session persistence, runtime validation, multi-project support |

---

## §5. Checkpoint (Aktualny Stan)

**Faza:** 1 — Minimum Viable Glue  
**Status:** Zakończona ✅  
**Ostatnia zmiana:** Migracja do Ligo v2.0 Safe-Zone + Multi-Project Support. Wprowadzono CallDepthGuard, SessionManager, ArchitectureValidator, project_manager.py z LigoHub.

---

## §6. Workflow Protokół Ligo 2.0 (5-Krokowy)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ KROK 1      │ →   │ KROK 2       │ →   │ KROK 3      │ →   │ KROK 4        │ →   │ KROK 5        │
│ ANALIZA     │     │ PROPOZYCJA   │     │ IMPLEMENT.   │     │ REJESTRACJA    │     │ SNAPSHOT + VALID|
│ _system/ +  │     │ _hub/        │     │ /modules/    │     │ ServiceReg     │     │ IDE (JSON)      │
│ _hub/current│     │ current_task │     │ stateless,   │     │ z CallDepth    │     │守护者           │
│ _task.md    │     │ .md          │     │ no imports   │     │ Guard         │     │                 │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘     └──────────────┘
```

---

## §7. Zasada 3 Błędów v2.0

Jeśli ten sam problem (np. naruszenie stateless, bezpośredni import między modułami) wystąpi **3 razy** — natychmiast przestań pisać kod i zgłoś problem w `_hub/current_task.md` z counterem: `error_count:<typ>:3/3`.

### Nowe błędy blokujące v2.0:
- **LOOP_DETECTED** — CallDepthGuard wykrył rekurencję → zatrzymaj się natychmiast
- **MAX_DEPTH_EXCEEDED** — głębsze niż 20 wywołań w call chain → zmniejsz max_depth lub przeanalizuj architekturę

---

## §8. Multi-Project Architecture (v2.0)

### Dla użytkownika:
```
Ligo/
├── _system/                    # Konstytucja LIGO (read-only dla AI!)
├── _hub/                       # Centrum komend
│   └── current_task.md         # Bieżące zadania
├── _projects/                  # Framework LIGO (silnik)
│   ├── contracts/, modules/, registry/, orchestrator/, tests/, snapshots/
│   ├── _utils/                 # Narzędzia frameworkowe
│   └── bootstrap.py            # Auto-discovery projektów
└── projects/                   # 🚀 WSPÓLNY katalog projektów!
    ├── project_alpha/          ← podfolder = osobny projekt
    │   ├── contracts/, modules/, orchestrator/
    └── project_beta/           ← drugi projekt, pełna izolacja
```

### Dla AI:
- **Framework** (`_projects/`, `_system/`) — SILNIK. Nie modyfikuj!
- **Projekty** (`projects/<nazwa>/`) — KOD DOMENY. Tu piszesz aplikacje.

---

## §9. Wymagania Systemowe v2.0

- **Python** 3.10+ (z Type Hinting)
- **pip** lub **poetry** do zarządzania zależnościami
- **pytest** do testów (`pip install pytest`)

### Uruchomienie projektu:
```bash
# Domyślny projekt (bez podfolderów):
cd _projects && python orchestrator/main.py

# Bootstrapping konkretnego projektu z projects/:
python -m ligo bootstrap project_alpha     # uruchamia projekt "project_alpha"

# Lista dostępnych projektów:
python -c "from _utils.project_manager import list_projects; print(list_projects())"
```

---

**KONIEC PROJECT ANCHOR — LIGO v2.0 Multi-Project Safe-Zone Protocol**
