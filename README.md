# PhishGuard

Multi-paradigm phishing detection system — praca inżynierska.

Łączy 4 podejścia analityczne: uczenie maszynowe (7 klasyfikatorów), algorytmy genetyczne (optymalizacja hiperparametrów), system regułowy (wiedza ekspercka) i klasyfikator bayesowski. Rozbieżności między paradygmatami są same w sobie sygnałem diagnostycznym.

## Postęp implementacji

| Faza | Status | Opis |
|------|--------|------|
| 1 — Data Pipeline | ✅ | PhishTank, UCI ML, Nazario, SMOTE, temporal split |
| 2 — URL Detection MVP | ✅ | Random Forest + 30 cech URL + FastAPI |
| 3 — Ensemble 7 klasyfik. | ✅ | Soft/hard/stacking voting + disagreement detection |
| 4 — GA Optimization | ✅ | DEAP + MLflow + optymalizacja hiperparametrów i wag |
| 5 — Rule-based + Bayesian | ✅ | 16 reguł YAML + GaussianNB + aggregation layer |
| 6 — Email & SMS | ✅ | spaCy NLP + parser e-mail + SMS features + retrained models |
| 7 — OCR & Visual | ✅ | EasyOCR + cechy wizualne/podobieństwo marki dla obrazów |
| 8 — Web Interface | ✅ | Frontend (web UI) + batch CSV, serwowane przez `src/api` |
| 9 — Explainability | ✅ | SHAP TreeExplainer + dashboard wyjaśnień (`/explain`) |
| 10 — Dokumentacja | ⏳ | Dokumentacja akademicka (architektura, algorytmy, ewaluacja) — w toku |

## Wymagania

- Python 3.9+ (testowane na 3.13)
- pip

## Setup na nowym komputerze

```bash
# 1. Klonuj repo
git clone <url-repozytorium>
cd Inzynierka

# 2. Utwórz i aktywuj venv
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 3. Zainstaluj zależności
pip install -r requirements.txt
pip install -e .

# 4. Pobierz model spaCy (wymagany dla email/SMS)
python -m spacy download en_core_web_sm

# 5. Skonfiguruj środowisko
cp .env.example .env
# opcjonalnie edytuj .env (DATA_DIR, CACHE_DIR, PHISHTANK_API_KEY)
```

## Uruchomienie API

```bash
source .venv/bin/activate
uvicorn src.api.main:app --reload
# Web UI (formularz + dashboard wyjaśnień): http://localhost:8000/
# Swagger UI: http://localhost:8000/docs
```

`src.api.main` serwuje jednocześnie REST API, web UI (Faza 8) i dashboard
wyjaśnień SHAP (Faza 9) — jeden proces `uvicorn`, bez osobnego frontend
buildu. Zmienne środowiskowe OpenMP (`KMP_DUPLICATE_LIB_OK`,
`OMP_NUM_THREADS`) wymagane przez równoczesne działanie XGBoost i innych
bibliotek z własnym runtime'em OpenMP są ustawiane programowo na początku
`src/api/main.py` — nie trzeba ich eksportować ręcznie przed uruchomieniem.

## Endpointy API

| Endpoint | Opis |
|----------|------|
| `GET /` | Web UI — formularz predykcji + dashboard wyjaśnień (Faza 8) |
| `GET /health` | Status załadowanych modeli |
| `GET /api/info` | Metadane API (wersja, dostępne modele) |
| `POST /predict` | Szybka analiza URL (Random Forest) |
| `POST /predict/ensemble` | 7 klasyfik. + disagreement score |
| `POST /predict/multi-paradigm` | Pełny system: ML + reguły + Bayesian |
| `POST /predict/email` | Analiza tekstu e-maila |
| `POST /predict/email/file` | Upload pliku .eml (max 5MB) |
| `POST /predict/sms` | Analiza wiadomości SMS |
| `POST /predict/image` | Analiza obrazu (OCR + cechy wizualne, Faza 7) |
| `POST /explain` | Wyjaśnienie decyzji (SHAP TreeExplainer, Faza 9) |
| `POST /batch` | Predykcja wsadowa (CSV upload, Faza 8) |
| `GET /batch/{job_id}` | Status/wynik zadania wsadowego |

## Testy

```bash
source .venv/bin/activate
pytest tests/ -v
# Oczekiwane: ~452 testy (1 pominięty)
```

## Struktura projektu

```
src/
├── api/            — FastAPI endpoints (predict/explain/batch) + web.py (UI) + Pydantic models
├── config/         — settings.py (dotenv, paths)
├── data/           — downloaders, validators, preprocessors, pipeline
├── features/       — url_features, email_features, text_features, sms_features,
│                     image_features + ocr/ (EasyOCR), extractors
├── models/         — classifiers, ensemble, disagreement, train, predict, evaluate
├── optimization/   — GA (DEAP), MLflow, model registry, feature selection
├── paradigms/      — rules/ (engine + YAML), bayesian/, aggregation/
├── explainability/ — SHAP TreeExplainer wrapper (Faza 9)
└── utils/          — cache, logging

models/             — wytrenowane modele (.joblib) — w repo, gotowe do użycia
reports/            — raporty ewaluacji (PDF/CSV) generowane przez scripts/generate_eval_report.py
docs/               — dokumentacja architektury, przepływu danych, API i teorii algorytmów
scripts/            — skrypty do retreningu modeli i generowania raportów
tests/              — ~452 testy (pytest)
.planning/          — GSD roadmap, state, fazy
```

## Modele w repozytorium

Wszystkie modele są commitowane (`models/`):
- `models/optimized/` — 7 klasyfik. zoptymalizowanych przez GA (avg F1 ~0.96)
- `models/ensemble/` — soft voting (97.47%), hard voting, stacking
- `models/email_sms/` — modele dla e-mail (65 cech, 98.4% acc.) i SMS (70 cech)
- `models/bayesian/` — klasyfikator bayesowski

Po klonowaniu modele są gotowe — nie trzeba retrenować.

## Cache i dane

Katalogi `data/` i `cache/` są w `.gitignore`. Regenerują się automatycznie przy pierwszym uruchomieniu pipeline lub uruchomieniu testów integracyjnych.

## Dokumentacja

- [docs/architecture.md](docs/architecture.md) — statyczna struktura systemu (diagram komponentów)
- [docs/data-flow.md](docs/data-flow.md) — przepływ żądania w czasie działania
- [docs/api.md](docs/api.md) — pełny opis endpointów REST API
- [docs/algorithms/](docs/algorithms/README.md) — teoria algorytmów na poziomie pracy inżynierskiej (pipeline danych, 7 klasyfikatorów, zespoły, i kolejno: GA, system regułowy, Bayes, agregacja, OCR/wizja, wyjaśnialność)

## Kontekst akademicki

Praca inżynierska na temat wykrywania phishingu. Główna teza: integracja 4 paradygmatów analitycznych, gdzie rozbieżności między metodami są sygnałem diagnostycznym zwiększającym interpretowalność decyzji klasyfikacyjnej.
