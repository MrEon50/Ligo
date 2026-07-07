# Filozofia Projektu Ligo

**Wersja:** 2.0  
**Data:** 2026-07-08  
**Status:** 🚧 FAZA ALPHA — NIE DO WDRożENIA PRODUKCYJNEGO

---

## Czym jest Ligo?

Ligo to **infrastruktura rozwojowa** — framework modułowy oparty na kontraktach, przeznaczony do budowy dużych systemów Pythonowych (100+ plików).

### Filary projektu

| Filary | Opis |
|--------|------|
| **Contract-based** | Moduły łączą się przez protokoły (interfejsy), nie przez dziedziczenie |
| **Stateless modules** | Każdy moduł to czysta funkcja — ten sam input → ten sam output, bez side effects |
| **Self-healing** | Zepsute moduły są automatycznie wykrywane i zastępowane z backupu |
| **Self-documenting** | Moduły same opisują siebie przez `get_service_info()` |
| **Composable** | Moduły łączą się jak klocki LEGO — `format_greeting("pl", get_greeting_period(14), "Ania")` |
| **Self-verifying** | System sam sprawdza swoją kondycję przez `stability_score()` |
| **Meta-cycling** | System analizuje własną strukturę i wykrywa problemy (cykle, brakujące zależności) |

---

## Czego Ligo NIE jest?

| Nie jest | Dlaczego |
|----------|----------|
| **Framework do pakowania aplikacji** | Ligo nie generuje .exe ani statycznych plików |
| **Framework GUI** | Nie ma komponentów wizualnych — użyj PyQt, Tkinter lub Flet |
| **Framework do deployu** | Nie generuje Dockerów, ani konfiguracji serwerowych |
| **Framework do migracji bazy** | Nie ma ORM — użyj SQLAlchemy lub Django ORM |

---

## Kiedy Ligo ma sens?

✅ **Tak — użyj Ligo gdy:**

- Budujesz **duży system z wieloma modułami** (100+ plików)
- Potrzebujesz **dynamicznego ładowania/wyłączania** komponentów
- Chcesz **automatycznej weryfikacji** poprawności projektu
- Planujesz **wielu deweloperów** pracujących równolegle
- Potrzebujesz **self-healing** — automatyczne wykrywanie i naprawa błędów

❌ **Nie — użyj innego narzędzia gdy:**

- Budujesz **jednorazową aplikację GUI** → użyj PyQt, Tkinter, Flet
- Chcesz **gotowy produkt do wdrożenia** → Ligo to framework rozwojowy, nie produkcyjny
- Potrzebujesz **pakowania do .exe** → użyj PyInstaller, Nuitka
- Projekt ma **< 50 plików** → Ligo jest overengineerowane dla małych projektów

---

## Czy projekt stworzony z Ligo może działać samodzielnie?

**Krótka odpowiedź: Nie — projekt zawsze będzie zależał od Ligo.**

Ligo to **silnik w środku samochodu**, nie **karoseria**. Możesz sprzedać samochód bez silnika (kod źródłowy), ale klient nie będzie mógł jeździć bez silnika (Ligo na komputerze klienta).

### Dlaczego projekt zawsze wymaga Ligo?

| Mechanizm Ligo | Dlaczego nie da się odpiąć |
|----------------|---------------------------|
| **Service Registry** | Moduły rejestrują się dynamicznie — bez Ligo nie ma rejestru |
| **Contract-based** | Moduły implementują protokoły Ligo — wymagają interfejsów Ligo |
| **Dynamic loading** | `load_snapshot()` ładuje moduły z rejestru Ligo |
| **Meta-cycling** | Zależności modułów są zarządzane przez graph Ligo |
| **Self-verifying** | `stability_score()` i `project_analyzer()` to narzędzia Ligo |

### Porównanie do znanych frameworków

| Framework | Co robi | Czy odpiąć? |
|-----------|---------|:-----------:|
| **Django** | ORM + URL routing + templates | ✅ Tak |
| **React** | Component model + JSX | ✅ Tak |
| **Spring Boot** | DI Container + auto-config | ❌ Nie |
| **Ligo** | Module registry + contracts + meta-cycling | ❌ Nie |

Ligo jest bliższe **Spring Boot** niż Django/React. To **container modułów**, nie framework do generowania gotowych aplikacji.

---

## Scenariusz: Duży projekt GUI z Ligo

```
Twój projekt GUI (np. PyQt6):
├── gui/
│   ├── main_window.py       → używa Ligo do ładowania modułów
│   ├── panels/
│   │   ├── dashboard.py     → rejestruje się w ServiceRegistry
│   │   └── settings.py      → rejestruje się w ServiceRegistry
│   └── widgets/
│       ├── custom_button.py  → moduł Ligo
│       └── data_grid.py      → moduł Ligo
├── services/
│   ├── api_client.py         → moduł Ligo
│   └── database.py            → moduł Ligo
└── main.py                   → orchestrator Ligo
```

**Wydaj po Ligo:**
- ✅ Kod źródłowy (gotowy do dalszej edycji)
- ✅ Pełna funkcjonalność (jeśli Ligo jest zainstalowane na serwerze/komputerze klienta)
- ❌ Nie wydajesz "gotowego .exe" — klient **musi mieć Python + Ligo**

**Aby odpiąć Ligo:**
1. Zamień dynamiczne ładowanie na statyczne importy
2. Usuń ServiceRegistry — zamień na singletony/dependency injection
3. Usuń meta-cycling — zamień na konfigurację ręczną
4. Pchnij przez PyInstaller/Nuitka

To **de-Ligo-owanie** to praca równoważna refaktoryzacji całego projektu.

---

## Dystrybucja projektu Ligo

| Cel | Rozwiązanie |
|-----|-------------|
| **Rozwój** | Ligo w środowisku deweloperskim |
| **Testowanie** | `pytest` z konfiguracją Ligo |
| **Wdrożenie na serwer Python** | `pip install ligo` + Ligo w `requirements.txt` |
| **Dystrybucja .exe klientowi** | PyInstaller/Nuitka — **Ligo musi być w `--hidden-import`** |

---

## Struktura projektu

```
Ligo/
├── _hub/                    # Dokumentacja i master prompt
├── _projects/               # Główny kod projektu
│   ├── _config.py           # Konfiguracja ścieżek
│   ├── _utils/              # Narzędzia pomocnicze
│   ├── _system/             # System core
│   ├── contracts/           # Protokoły (interfejsy)
│   ├── modules/             # Moduły biznesowe
│   ├── orchestrator/        # Orkiestracja
│   ├── registry/            # Service Registry
│   ├── tests/               # Testy jednostkowe
│   └── audit/               # Raporty audytu
├── _system/                 # System Ligo
└── README.md
```

---

## Testy jednostkowe

Projekt zawiera **111 testów** w **5 plikach testowych**:

| Plik testów | Liczba | Co testuje |
|-------------|--------|------------|
| `test_time_greeting_helper.py` | 44 | Deterministyczność modułów — ten sam input = ten sam output |
| `test_service_registry.py` | 23 | Contract validation, unregister, None validation, instance tracking |
| `test_mvg.py` | 16 | End-to-end workflow modułów greeting |
| `test_self_verify.py` | 17 | Autoweryfikacja projektu (stability score, import checker) |
| `test_meta_cycling.py` | 11 | Wykrywanie cykli, context management, session management |

### Jak uruchomić testy?

```bash
cd _projects
python -m pytest tests/ -v
```

---

## Disclaimer

⚠️ **Ligo jest w fazie ALPHA.** Nie jest gotowe do wdrożeń produkcyjnych. Używaj na własne ryzyko.

---

## Licencja

[Do uzupełnienia]