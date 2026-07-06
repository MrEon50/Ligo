# 🧩 LIGO 2.0 — The Safe-Zone + Meta-Cycling System

**Framework inżynierii modułowej do budowania gigantycznych systemów za pomocą agentów AI.**  
**Wersja:** 2.0 (Safe-Zone + Meta-Cycling)

---

## 🎯 Co to jest LIGO?

LIGO to **System Operacyjny dla Twojego Projektu**. To nie jest produkt domeny — to silnik, który pozwala Tobie (lub AI) budować złożone aplikacje w sposób stabilny i skalowalny.

### Jak to działa? Wyobraź sobie puzzle:

- Każdy element systemu to **osobna część puzzla** (moduł).
- Wszystkie części łączą się przez **centralny Klej** (Registry).
- Błąd w jednym elemencie **nie psuje reszty układu**.

### Co nowego w wersji 2.0?

LIGO 2.0 wprowadza **Meta-Cyklizm** — mechanizm zapisywania kontekstu modyfikacji między sesjami AI (Context Manager + Dependency Graph). Dzięki temu nowy agent AI widzi co zostało zrobione w poprzedniej sesji i nie zaczyna od zera.

---

## 🚀 Szybki Start — Jak Użyć LIGO?

### 1. Podaj pomysł AI za pomocą Master Promptu

Załóż nową sesję AI z plikiem `_hub/master_prompt_ligo_2.0.md` jako instrukcją startową, a potem podaj cel:

> "Dodaj moduł powitań w języku niemieckim"

AI **przeczyta** `PROJECT_ANCHOR.md` (w `_system/`) jako konstytucję projektu i zacznie działać zgodnie z protokołem Ligo 2.0.

### 2. AI działa autonomicznie w protokole Ligo 2.0 (4-krokowy + meta-cyklizm)

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│ KROK 1      │ →  │ KROK 2       │ →  │ KROK 3      │ →  │ KROK 4       │
│ Analiza     │    │ Propozycja   │ →  │ Implement. │ →  │ Weryfikacja  │
│ _system/ +  │    │ _hub/        │    │ Snapshot +   │    │ "Czy to    │
│ _hub/current│    │ current_task │    │ Testy        │    │ narusza?")  │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
```

**Po każdym cyklu AI:**

- ✅ Generuje **Snapshot techniczny** (pamięć robocza w `_projects/snapshots/`)
- ✅ Opisuje zmiany w `_hub/current_task.md`
- ✅ Odpowiada na 3 pytania weryfikacyjne (czy nie narusza `_system/`, czy moduł stateless, czy brak bezpośrednich importów)

### 3. Ty zatwierdzasz → nowy cykl

---

## 🏗️ Struktura Projektu (Safe-Zone + Meta-Cycling v2.0)

```
ligo/
├── _system/                    # 🔒 STREFA ZABRONIONA (Read-Only dla AI)
│   ├── project_anchor.md       # 📜 Konstytucja projektu — NIGDY nie modyfikuj!
│   └── tech_stack.md           # 🛠️ Stos technologiczny i standardy kodowania
│
├── _hub/                       # 💬 CENTRUM KOMEND (Planowanie)
│   ├── current_task.md         # 📝 Jedyne miejsce na opisywanie zamiarów
│   └── master_prompt_ligo_2.0.md  # 🎯 Master Prompt agenta AI (v2.0)
│
├── _projects/                  # 🔨 WARSZTAT (Kod aplikacji — tu AI pisze)
│   ├── contracts/              # 📋 "CO" moduł robi — definicje (interfejsy)
│   │   └── *_protocol.py       #     Nigdy nie zawiera logiki biznesowej
│   ├── registry/               # 🔗 "KLEJ" systemu — centralny rejestr usług
│   │   ├── service_registry.py #     Rejestruje i pobiera moduły
│   │   └── log_handler.py      #     Logowanie każdej operacji
│   ├── modules/                # ⚙️ "JAK" moduł działa — implementacje (@final, stateless)
│   │   └── *_service.py        #     Zakaz importów z innych modułów
│   ├── orchestrator/           # 🧠 "MÓZG" — logika biznesowa, przepływ
│   │   └── *.py                #     Pobiera usługi z Registry
│   ├── tests/                  # ✅ Testy jednostkowe i integracyjne
│   └── snapshots/              # 📸 Pamięć robocza (snapshoty po każdym cyklu)
│
├── snapshots/                  # 💾 PAMIĘĆ (Historyczne snapshoty)
└── scratchpad.md               # 🧪 Eksperymentalne myślenie AI
```

### Rola każdej strefy:

| Strefa       | Prawo dostępu AI              | Cel                                                               |
| ------------ | ----------------------------- | ----------------------------------------------------------------- |
| `_system/`   | **TYLKO DO ODCZYTU**          | Zasady projektu. Modyfikacja = błąd architektury.                 |
| `_hub/`      | Planowanie (tylko opisywanie) | Miejsce na propozycje zmian, plany, raporty problemów.            |
| `_projects/` | **Zapis + Odczyt**            | Tu powstaje kod aplikacji: kontrakty, moduły, rejestracja, testy. |

---

## 🧩 Architektura 4 Warstw (wewnątrz `_projects/`)

### Warstwa 1: `contracts/` — Definicje (CO)

Definiuje **interfejsy** (protokoły). Zawiera wyłącznie typy i sygnatury metod.

```python
# contracts/greeting_protocol.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class GreetingServiceProtocol(Protocol):
    def greet(self, name: str, context: dict | None = None) -> str: ...
```

### Warstwa 2: `modules/` — Implementacje (JAK)

Każdy moduł to zamknięta jednostka. **Stateless** + `@final`.

```python
# modules/polish_greeting.py
from typing import final, Protocol

@final
class PolishGreetingService:
    def greet(self, name: str, context: dict | None = None) -> str:
        return f"Dzień dobry, {name}!"
```

### Warstwa 3: `registry/` — Klej (KTO)

Centralny rejestr. **Jedyne** miejsce, gdzie moduły są "podpinane" do systemu.

```python
# registry/service_registry.py (uproszczone)
registry.register(key="greeting.pl", instance=polish_greeting)
service = registry.get_service("greeting.pl")
```

### Warstwa 4: `orchestrator/` — Mózg (KIEDY)

Zarządza przepływem danych i wywołuje usługi w odpowiedniej kolejności. Pobiera usługi z Registry.

---

## ⚡ Protokół Działania AI (Ligo 2.0)

Gdy podasz cel (np. "Dodaj moduł wysyłki SMS"), AI działa tak:

### Analiza → Propozycja → Implementacja → Weryfikacja + Meta-Cyklizm

**KROK 1 — Analiza:**

1. Czyta `_system/project_anchor.md` (zasady projektu) i `_hub/current_task.md` (bieżący kontekst)

**KROK 2 — Propozycja:** 2. Jeśli zadanie nie jest opisane w Hubie → wpisuje plan w `_hub/current_task.md` 3. Czekaj na akceptację (lub kontynuuj w trybie autonomicznym)

**KROK 3 — Implementacja (4 pod-kroki):** 4. Tworzy kontrakt w `/contracts/` z protokołem nowego modułu 5. Pisze kod w `/modules/` — stateless, `@final`, bez importów z innych modułów 6. Rejestruje w `/registry/service_registry.py` pod unikalnym kluczem 7. Walidacja kontraktu (type checking)

**KROK 4 — Weryfikacja + Snapshot:** 8. Aktualizuje `/orchestrator/` aby używał nowej usługi 9. Tworzy **LIGO Snapshot** techniczny w `_projects/snapshots/` 10. Odpowiada na pytania: "Czy narusza \_system/?", "Moduł stateless?", "Brak bezpośrednich importów?"

### ⏸ Zasada 3 Błędów

Jeśli ten sam problem wystąpi 3 razy — AI przestaje pisać kod i raportuje w `_hub/current_task.md`.

---

## 🔒 Twarde Granice (Anti-Chaos)

| Zasada                                    | Dlaczego?                                    |
| ----------------------------------------- | -------------------------------------------- |
| **Stateless moduły**                      | Błąd w jednym module nie wpływa na inne      |
| **Brak importów między modułami**         | Eliminacja efektu domina                     |
| **Walidacja kontraktów przy rejestracji** | Błąd rzucony natychmiast po `register()`     |
| **Logging każdej operacji**               | Pełna widoczność w razie awarii              |
| **Snapshot po każdym cyklu**              | AI "wie" co zrobiło — nawet po restart sesji |

---

## 🎮 Przykłady Użycia

### Dodanie nowego modułu (np. niemieckiego):

```bash
# Podaj AI: "Dodaj moduł powitań w języku niemieckim"
cd _projects && python orchestrator/main.py  # Uruchom aplikację — zobaczysz nowy moduł
python -m pytest tests/ -v  # Wszystkie testy przechodzą
```

### Symulacja awarii jednego modułu:

```bash
# Wymuszenie błędu w module angielskim
cd _projects && python orchestrator/main.py  # System nadal działa — polski moduł żyje!
```

---

## 📋 Dokumenty Kluczowe

| Dokument             | Ścieżka                          | Co zawiera                                             | Kiedy czytać              |
| -------------------- | -------------------------------- | ------------------------------------------------------ | ------------------------- |
| `README.md`          | `_projects/README.md`            | Jak korzystać z LIGO (ten plik)                        | Zawsze na początku        |
| `PROJECT_ANCHOR.md`  | `_system/project_anchor.md`      | Konstytucja, zasady, checkpointy — **NIE MODYFIKUJ!**  | Przed każdą decyzją       |
| `TECH_STACK.md`      | `_system/tech_stack.md`          | Standardy kodowania i technologie — **NIE MODYFIKUJ!** | Przy pisaniu kodu         |
| `MASTER PROMPT`      | `_hub/master_prompt_ligo_2.0.md` | Instrukcja startowa dla agenta AI (v2.0)               | Na początku sesji         |
| `current_task.md`    | `_hub/current_task.md`           | Bieżące zadania, propozycje, raporty problemów         | Podczas pracy             |
| `LIGO_SNAPSHOT_*.md` | `_projects/snapshots/`           | Techniczny stan po każdym cyklu                        | Aby zrozumieć co zrobiono |

---

## 🛠️ Wymagania Systemowe

- **Python** 3.10+ (z Type Hinting)
- **pip** lub **poetry** do zarządzania zależnościami
- **pytest** do testów (`pip install pytest`)

### Uruchomienie projektu:

```bash
cd _projects && python orchestrator/main.py
python -m pytest tests/ -v  # Uruchom wszystkie testy
```

---

## 📐 Zasady Dla Agentów AI (Ligo 2.0)

Jeśli Twój agent AI pracuje nad LIGO, musi:

1. **Czytać Master Prompt** (`_hub/master_prompt_ligo_2.0.md`) jako pierwszą rzecz w sesji
2. **Nigdy nie modyfikować `_system/`** — to strefa Read-Only (konstytucja projektu)
3. **Planować w Hubie** — wszystkie zamiary opisuje w `_hub/current_task.md`
4. **Generować Snapshot** po każdym ukończonym cyklu
5. **Szacunek do kontraktów** — modyfikacja wymaga wersji (`v2`, `v3`)
6. **Zatrzymać się po 3 powtórzeniach tego samego błędu** i zgłosić problem w Hubie

---

## 🗺️ Roadmapa Projektu

| Faza               | Cel                                                                           | Status            |
| ------------------ | ----------------------------------------------------------------------------- | ----------------- |
| 1 — MVG            | Minimum Viable Glue (Generator Powitań)                                       | ✅ UKOŃCZONA      |
| 2.0 — Meta-Cyklizm | Context Manager + Dependency Graph (zachowywanie kontekstu między sesjami AI) | ✅ UKOŃCZONA      |
| 3 — Rozszerzanie   | Dodatkowe moduły, testy izolacji awarii                                       | ⏳ Do rozpoczęcia |
| 4 — Skalowanie     | Złożone moduły biznesowe, optymalizacja                                       | 🔲 Zaplanowana    |

---

## 🤝 Jak Zacząć Nowy Projekt z LIGO?

1. **Skopiuj** całą strukturę (`_system/`, `_hub/`, `_projects/`) do nowego katalogu
2. **Zaktualizuj** `_system/project_anchor.md` — zmień IDEĘ na swój projekt (tylko jako właściciel, nie AI!)
3. **Podaj Master Prompt** agentowi AI z plikiem `_hub/master_prompt_ligo_2.0.md`
4. **Podaj cel** w stylu: "Stwórz moduł do [twoja domena]"
5. AI zacznie działać autonomicznie według protokołu LIGO 2.0 (w tym meta-cyklizm)

> **Uwaga:** Konfiguracja projektu wymaga czasu (1-2 godziny na setup). LIGO nie jest narzędziem "out of the box" — to framework architektoniczny który trzeba dostosować do swojego projektu.

---

## 🌟 Co Robi LIGO? — Zrównoważony Przegląd

LIGO to **framework architektoniczny** który pomaga budować modułowe systemy z udziałem AI. Nie jest to "gotowiec" — to struktura którą trzeba skonfigurować pod swój projekt.

### ✅ Co LIGO Działa Dobrze:

| Funkcjonalność             | Jak działa                                                            | Ograniczenia                                                                 |
| -------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Safe-Zone Architecture** | Blokuje AI przed modyfikacją fundamentów (`_system/`)                 | Wymaga disciplinednego przestrzegania zasad przez AI                         |
| **Meta-Cyklizm**           | Zapisuje kontekst między sesjami (Context Manager + Dependency Graph) | Działa tylko w ramach jednego projektu — nie synchronizuje między projektami |
| **Walidacja Kontraktów**   | Sprawdza czy moduły spełniają wymagane interfejsy                     | Nie wykrywa błędów logicznych w implementacji                                |
| **Struktura Projektu**     | Jasny podział na kontrakty, moduły, registry, orchestrator            | Wymaga disciplinednego przestrzegania warstw (brak importów między modułami) |

### ❌ Czego LIGO NIE Robi:

- **Nie jest gotowym frameworkiem biznesowym** — trzeba napisać własne kontrakty i moduły
- **Nie rozwiązuje wszystkich problemów AI** — to narzędzie do organizowania pracy z AI, nie magik który sam pisze kod
- **Nie zastępuje testów jednostkowych** — LIGO organizuje strukturę, ale testy musisz napisać sam
- **Nie działa "out of the box" z dowolnym agentem AI** — wymaga konfiguracji Master Promptu i zrozumienia protokołu

### 📍 Gdzie Tworzyć Projekt? (KLUCZOWE!)

```
📁 ligo/                          ← Korzeń projektu LIGO
├── _system/                      ← 🔒 NIGDY nie modyfikuj! (fundamenty frameworka)
├── _hub/                         ← Tylko planowanie (opisywanie zamiarów, nie kod!)
└── 📁 _projects/                 ← ✅ ✅ ✅ TU TWORZYSZ SWÓJ PROJEKT!
    ├── contracts/                ← Definicje interfejsów (CO moduł robi)
    ├── modules/                  ← Implementacje (JAK moduł działa) — stanless + @final
    ├── registry/                 ← Rejestracja usług (KLEJ systemu)
    ├── orchestrator/             ← Logika biznesowa (KIEDY wywołać usługi)
    └── tests/                    ← Testy jednostkowe i integracyjne
```

**Złota zasada:** Twój projekt znajduje się **wyłącznie w `_projects/`**! Reszta to fundamenty frameworka LIGO które są niedostępne do modyfikacji przez AI.

### 🎯 Kiedy Warto Użyć LIGO?

- ✅ Budujesz duży system z udziałem AI (50+ modułów)
- ✅ Chcesz mieć pewność że AI nie zepsuje fundamentów projektu
- ✅ Pracujesz nad projektem długoterminowo i chcesz zachować kontekst między sesjami
- ✅ Potrzebujesz jasnej architektury modułowej (kontrakty, izolacja)

### 🚫 Kiedy LIGO Może Nie Być Odpowiednie?

- ❌ Mały projekt (< 10 modułów) — nadmiarowa struktura może przeszkadzać
- ❌ Szybki prototyp — konfiguracja LIGO wymaga czasu (1-2 godziny na setup)
- ❌ Projekt bez AI — LIGO jest zaprojektowane dla pracy z agentami AI, nie dla tradycyjnej development

---

## 🚀 Jak Tworzyć Duży Projekt Z LIGO? — Praktyczny Przewodnik

### Gdzie AI Pracuje? (KLUCZOWE!)

```
📁 ligo/                          ← TYLKO TUTAJ PRACUJESZ!
├── _projects/                    ← ✅ TU JEST TWÓJ PROJEKT
│   ├── contracts/                ← Definicje interfejsów (CO moduł robi)
│   ├── modules/                  ← Implementacje (JAK moduł działa)
│   ├── registry/                 ← Rejestracja usług (KLEJ systemu)
│   ├── orchestrator/             ← Logika biznesowa (KIEDY wywołać usługi)
│   └── tests/                    ← Testy jednostkowe i integracyjne
├── _system/                      ← 🔒 NIGDY NIE Modyfikuj! (Read-Only)
└── _hub/                         ← Tylko planowanie (opisywanie zamiarów)
```

**Złota zasada:** AI pracuje **TYLKO w `_projects/`**! Reszta to fundamenty frameworka które są niedostępne do modyfikacji.

---

### Jak Zaczynać Od Małego Projektu? (Krok Po Kroku)

#### Krok 1: Stwórz prosty projekt testowy

```bash
# Skopiuj strukturę LIGO do nowego projektu
cp -r /ścieżka/do/Ligo/_system /mój/projekt/
cp -r /ścieżka/do/Ligo/_hub /mój/projekt/
cp -r /ścieżka/do/Ligo/_projects /mój/projekt/

# Edytuj tylko _system/project_anchor.md — zmień IDEĘ na swój projekt
```

#### Krok 2: Dodaj pierwszy moduł (np. "powitanie")

- Stwórz kontrakt w `/contracts/greeting_protocol.py`
- Dodaj implementację w `/modules/polish_greeting.py`
- Zarejestruj w `/registry/service_registry.py`

#### Krok 3: Rozwijaj projekt warstwowo

```
Mały projekt (1 moduł) → Średni (5-10 modułów) → Duży (50+ modułów)
         ↓                      ↓                    ↓
    Testuj każdy          Dodawaj nowe           Skup się na
    moduł osobno          moduły po kolei        architekturze
```

#### Krok 4: Skalowanie do dużego projektu

- **Nie dodawaj wszystkiego naraz!** — 1-3 moduły na sesję AI
- **Testuj po każdym cyklu** — `python -m pytest tests/`
- **Używaj Meta-Cyklizmu** — Context Manager zapisuje co zostało zmienione

---

### Zabezpieczenia Przed Zmianami W Frameworku (Jak AI Nie Zepsuje Ligo?)

LIGO ma **4-warstwową ochronę** która blokuje niebezpieczne zmiany:

#### 🔒 Warstwa 1: Safe-Zone Architecture (Read-Only)

```
_system/ → 🔒 NIGDY niedostępne do modyfikacji przez AI!
_hub/    → 💬 Tylko do planowania (opisywania zamiarów)
_projects/→ ✅ Jedyna strefa gdzie AI pisze kod
```

**Jak to działa?** Master Prompt mówi AI: _"Nigdy nie modyfikuj `_system/` — to jest konstytucja projektu!"_

#### 🔍 Warstwa 2: Dependency Graph (Wykrywanie Niebezpiecznych Zmian)

Dependency Graph analizuje deklarowane zależności między modułami i ostrzega przed modyfikacjami które mogą zepsuć inne części systemu. Wymaga to jednak **ręcznej deklaracji zależności** w plikach projektu — nie wykrywa ich automatycznie z kodu źródłowego.

```python
from _utils.ligo_meta_cycling import MetaCyclingManager

manager = MetaCyclingManager()
result = manager.check_safety_before_save()
# Jeśli result["safe"] == False → AI dostaje komunikat o problemie!
```

**Co Dependency Graph wykrywa (zadeklarowane zależności):**

- ✅ Modyfikacja kontraktu łamiąca zależne moduły (jeśli zależność jest zarejestrowana)
- ✅ Próba usunięcia usługi która jest wciąż używana przez inne moduły

**Czego Dependency Graph NIE wykrywa:**

- ❌ Ukrytych importów w kodzie (muszą być zadeklarowane ręcznie)
- ❌ Cykli importów — wymaga analizy statycznej poza zakresem LIGO

#### 🔄 Warstwa 3: Meta-Cyklizm (Context Manager + Snapshot)

Meta-Cyklizm zapisuje kontekst modyfikacji między sesjami — nowy agent AI widzi co zostało zrobione w poprzedniej sesji. **Nie jest to auto-healing** ani przywracanie do poprzedniego stanu kodu — to mechanizm zachowywania informacji o tym co zostało zmienione.

```python
# Przed zmianą kodu:
manager.track_file_modification("modules/stary_modul.py", new_content)

# Po zakończeniu pracy:
manager.save_full_session(project_id="default")

# Przy restartie sesji — ładuje kontekst poprzedniej sesji!
context = manager.load_context(project_id="default")
```

**Co Meta-Cyklizm realnie robi:**

- ✅ Zapisuje co zostało zmienione między sesjami (pliki, modyfikacje)
- ✅ Nowy agent AI wie co zrobił poprzedni — nie zaczyna od zera
- ✅ Pomaga w śledzeniu historii projektu

**Czego Meta-Cyklizm NIE robi:**

- ❌ Nie przywraca kodu do wcześniejszej wersji (to Snapshots robią)
- ❌ Nie naprawia błędów automatycznie

#### 🛡️ Warstwa 4: Walidacja Kontraktów (Type Checking)

Przed rejestracją modułu w registry, LIGO sprawdza czy spełnia wymagany protokół:

```python
# Jeśli moduł nie ma wymaganych metod — rzucony zostanie TypeError!
registry.register(key="moj_modul", instance=moja_instancja, contract_type=GreetingProtocol)
```

---

### Podsumowanie Bezpieczeństwa LIGO (Realistyczne):

| Ryzyko                              | Jak LIGO chroni przed tym?                  | Ograniczenie                                      |
| ----------------------------------- | ------------------------------------------- | ------------------------------------------------- |
| AI zepsuje fundamenty frameworka    | Safe-Zone (`_system/` Read-Only)            | Zależy od disciplinednego przestrzegania przez AI |
| Zmiana w module zepsuje inne moduły | Dependency Graph (zadeklarowane zależności) | Nie wykrywa ukrytych zależności w kodzie          |
| Trudno śledzić co zostało zmienione | Meta-Cyklizm (kontekst między sesjami)      | Nie przywraca kodu — tylko zapisuje kontekst      |
| Moduł nie spełnia wymagań           | Walidacja kontraktów przy rejestracji       | Tylko sprawdza protokół, nie logikę biznesową     |

**Dzięki tym 4 warstwom, AI może budować projekty z większą świadomością tego co już istnieje.** LIGO nie gwarantuje bezpieczeństwa — wymaga disciplinednego przestrzegania zasad przez wszystkich agentów AI które pracują nad projektem.

---

## 💡 Pomysł i Inspiracja — Dlaczego To Powstało?

LIGO powstało z praktycznej potrzeby: **jak sprawić, by agent AI mógł bezpiecznie pracować nad dużym projektem bez niszczenia tego, co już działa?**

Problem jest prosty: im większy projekt, tym trudniej dać AI instrukcje które nie psują istniejącego kodu. Większość rozwiązań polega na ręcznej weryfikacji lub zaawansowanych promptach systemowych. LIGO oferuje **konkretną architekturę** która rozwiązuje ten problem na poziomie struktury projektu:

- **Dla twórców AI-powered narzędzi**: LIGO może być inspiracją do budowania własnych "bezpiecznych stref" wokół projektów
- **Dla deweloperów single-player**: Architektura Safe-Zone działa niezależnie od tego czy pracujesz sam, czy z AI
- **Dla edukacji**: Projekt pokazuje jak łączyć kontrakty, izolację i snapshooting w praktyce

### 🎯 Cel LIGO:

> **Umożliwić budowanie złożonych systemów w sposób stabilny, skalowalny i odwracalny — bez ryzyka zepsucia tego co już działa.**

Jeśli ten projekt Cię zainspirował do ulepszenia własnych rozwiązań lub stworzenia czegoś nowego — to właśnie o to chodzi. LIGO jest open-source i zachęca do eksperymentów.

---

## 🧑‍💻 O Autorze — Dlaczego Local First?

> Ten projekt to mój pierwszy program stworzony **lokalnie** który umieszczam na GitHubie.  
> Wcześniej pisałem kod głównie za pomocą dużych modeli chmurowych ale nigdy nie płaciłem daniny za tokeny ponieważ jestem zwolennikiem rozwiązań lokalnych.  
> LIGO to wynik eksperymentu — jak zamienić pracę z AI w **kontrolowany proces**, a nie losowanie po ciemku.  
> Wszystko działa na lokalnym modelu, zero kosztów API, zero zależności od chmury.  
> Tylko Python, OpenCode i trocha paranoi architektonicznej.

---

## 📝 Licencja

Projekt LIGO jest open-source — użyj go dowolnie, modyfikuj, rozszerzaj.

**KONIEC README.md**
