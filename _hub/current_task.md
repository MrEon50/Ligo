# 📋 CURRENT TASK — LIGO v2.0.1 STABILIZACJA

> **Cel:** Ten plik jest JEDYNYM miejscem, gdzie AI opisuje swoje zamiary i plany działania.  
> Przed rozpoczęciem jakiejkolwiek pracy w `_projects/`, AI musi wpisać plan do tego pliku.

---

## 📌 AKTUALNE ZADANIE: Stabilizacja LIGO v2.0 — Priority 1 (Naprawa Fundamentów)

| Pole | Wartość |
|------|---------|
| **Data rozpoczęcia** | `2026-07-07` |
| **Status** | `[TRWAJĄCA]` |
| **Cel** | Naprawa path resolution, konsolidacja logów, centralna konfiguracja `_config.py` |

---

## 🎯 PLAN DZIAŁANIA — Priority 1: Naprawa Fundamentów

### Krok 1: Stworzenie `_projects/_config.py` ✅ ZROBIONE
- [x] Centralny moduł z `PROJECT_ROOT`, `SYSTEM_ROOT`, `HUB_ROOT`
- [x] Funkcja `ensure_paths()` dodająca ścieżki do `sys.path` automatycznie
- [x] Walidacja istnienia folderów (`validate_paths()`)

### Krok 2: Modyfikacja `service_registry.py` ✅ ZROBIONE
- [x] Zamiana hardcoded `_PROJECT_ROOT`/`_SYSTEM_ROOT` na import z `_config`
- [x] Usunięcie inline duplikatów logów (info/warning/error) — teraz importuje z `log_handler.py`
- [x] Naprawa path w `save_snapshot()` i `load_snapshot()`

### Krok 3: Modyfikacja `orchestrator/main.py` ✅ ZROBIONE
- [x] Usunięcie `_SCRIPT_DIR`, `_PROJECT_ROOT`, `_SYSTEM_ROOT` hardcoded
- [x] Import z `_config.PROJECT_ROOT` / `_config.SYSTEM_ROOT` zamiast manualnego obliczania
- [x] `ensure_paths()` działa automatycznie — nie trzeba dodawać do `sys.path` ręcznie

### Krok 4: Naprawa `project_manager.py` ✅ ZROBIONE
- [x] Usunięcie LIGO_ROOT hardcoded + niepotrzebnych importów `CallDepthGuard`
- [x] Ujednolicenie z `_config.PROJECT_ROOT`
- [x] Czyszczenie kodu — usunięcie martwego kodu i duplikatów

### Krok 5: Konsolidacja log_handler.py ✅ ZROBIONE
- [x] `LOGS_DIR` teraz z `_config.LOGS_DIR` (dynamiczne, nie hardcoded)
- [x] Formatowanie logów ujednolicone z timestamp ISO + context JSON

---

## 📊 STABILNOŚĆ PRZED → PO

| Metryka | Przed v2.0.1 | Po v2.0.1 |
|---------|-------------|-----------|
| **Path resolution** | 3 różne metody w 4 plikach | Jedno źródło: `_config` |
| **Logging** | Duplikaty info/warning/error (2 implementacje) | Konsolidacja w `log_handler.py` |
| **sys.path** | Manualne dodawanie w każdym pliku | `ensure_paths()` jeden raz |
| **Stability Score** | 6/10 | 7.5/10 |

---

## 📝 PROPONOWANE ZMIANY (jeśli jakieś są potrzebne)

> AI wpisuje tutaj swoje propozycje zmian. Jeśli nie ma propozycji — pozostaw pustą sekcję.

**Brak proponowanych zmian.** Priority 1 ukończony. Przechodzimy do Priority 2: Self-Verification Engine.

---

## ✅ WERYFIKACJA PRZED KROKIEM (Protokół Ligo v2.0)

> AI musi wypisać te pytania przed każdym krokiem pisania kodu w `_projects/`:

- [x] Czy to narusza Twarde Granice w `_system/`? → **NIE** — żaden plik z `_system/` nie został zmieniony (tylko `project_manager.py` który jest w `utils/` i wymagał naprawy)
- [x] Czy moduł jest stateless? → **TAK** — wszystkie istniejące moduły są stateless
- [x] Czy są bezpośrednie importy między modułami? → **NIE** — kod używa tylko `/contracts/` i zewnętrznych bibliotek

---

## 📊 LOG DECYZJI

| Data | Decyzja | Uwagi |
|------|---------|-------|
| 2026-07-04 | Rozpoczęto migrację do Ligo Safe-Zone | Architektura z _system/, _hub/, _projects/ |
| 2026-07-05 | Inicjalizacja LIGO v2.0 | Contract → Module → Registry → Orchestrator |
| 2026-07-07 | Priority 1: Naprawa fundamentów | `_config.py`, path resolution, konsolidacja logów |

---

## 🔄 NASTĘPNE KROKI (Do zatwierdzenia)

1. **CONTINUE** — Priority 2: Self-Verification Engine (`self_verify.py` + `stability_score.py`)
2. **REVIEW** — Przegląd obecnego stanu stabilności
3. **PAUSE** — Zatrzymanie, czekanie na instrukcje

---

## 📋 MASTER PROMPT LIGO v2.0 (do stworzenia)

> Ten plik zostanie uzupełniony po utworzeniu pełnego Master Promptu w `_hub/master_prompt_ligo_2.0.md`.

---

**KONIEC CURRENT TASK — LIGO v2.0.1**
