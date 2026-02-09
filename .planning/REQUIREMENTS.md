# Requirements: PhishGuard

**Defined:** 2026-02-09
**Core Value:** Integracja wielu paradygmatów analizy w jeden spójny system, gdzie rozbieżności między metodami dostarczają dodatkowego kontekstu i zwiększają wiarygodność decyzji klasyfikacyjnej.

## v1 Requirements

### Data Input (INPUT)

- [ ] **INPUT-01**: System przyjmuje URL do analizy przez formularz webowy
- [ ] **INPUT-02**: System przyjmuje surowy tekst wiadomości (e-mail/SMS/chat)
- [ ] **INPUT-03**: System przyjmuje plik e-mail w formacie .eml
- [ ] **INPUT-04**: System przyjmuje obraz do analizy (PNG, JPG, screenshot)
- [ ] **INPUT-05**: System przyjmuje plik CSV do analizy batch wielu próbek
- [ ] **INPUT-06**: System ekstrahuje tekst z obrazów poprzez OCR (EasyOCR)
- [ ] **INPUT-07**: System analizuje cechy wizualne obrazów (układ, logo, elementy graficzne)

### Feature Extraction (FEAT)

- [ ] **FEAT-01**: System ekstrahuje cechy długościowe (długość tekstu, liczba słów, średnia długość słowa)
- [ ] **FEAT-02**: System ekstrahuje cechy leksykalne (słowa kluczowe, n-gramy, częstość słów)
- [ ] **FEAT-03**: System ekstrahuje cechy składniowe (struktura zdań, interpunkcja)
- [ ] **FEAT-04**: System ekstrahuje cechy stylometryczne (formalność, ton, złożoność)
- [ ] **FEAT-05**: System ekstrahuje cechy URL (domena, długość, obecność IP, skrócone linki)
- [ ] **FEAT-06**: System ekstrahuje cechy sentymentu (pilność, strach, presja czasowa)
- [ ] **FEAT-07**: System ekstrahuje cechy nagłówków e-mail (SPF, DKIM, nadawca)
- [ ] **FEAT-08**: System normalizuje i skaluje wszystkie cechy przed klasyfikacją

### ML Classifiers (ML)

- [ ] **ML-01**: System trenuje i używa klasyfikatora Random Forest
- [ ] **ML-02**: System trenuje i używa klasyfikatora Support Vector Machine (SVM)
- [ ] **ML-03**: System trenuje i używa sieci neuronowej MLP
- [ ] **ML-04**: System trenuje i używa klasyfikatora Gradient Boosting (XGBoost)
- [ ] **ML-05**: System trenuje i używa klasyfikatora Logistic Regression
- [ ] **ML-06**: System trenuje i używa klasyfikatora Naive Bayes
- [ ] **ML-07**: System trenuje i używa klasyfikatora Decision Tree
- [ ] **ML-08**: Każdy klasyfikator zwraca prawdopodobieństwo klasy phishing

### Ensemble Methods (ENS)

- [ ] **ENS-01**: System agreguje wyniki klasyfikatorów metodą soft voting (średnia prawdopodobieństw)
- [ ] **ENS-02**: System agreguje wyniki klasyfikatorów metodą hard voting (głosowanie większościowe)
- [ ] **ENS-03**: System agreguje wyniki klasyfikatorów metodą stacking (meta-model)
- [ ] **ENS-04**: System porównuje skuteczność różnych metod agregacji
- [ ] **ENS-05**: System wykrywa i raportuje rozbieżności między klasyfikatorami

### Genetic Algorithm (GA)

- [ ] **GA-01**: System optymalizuje hiperparametry klasyfikatorów algorytmem genetycznym (DEAP)
- [ ] **GA-02**: System optymalizuje wybór cech (feature selection) algorytmem genetycznym
- [ ] **GA-03**: System optymalizuje wagi klasyfikatorów w ensemble algorytmem genetycznym
- [ ] **GA-04**: System używa selekcji turniejowej, krzyżowania jednopunktowego i mutacji
- [ ] **GA-05**: System maksymalizuje miarę F1 w 5-krotnej walidacji krzyżowej jako funkcję celu
- [ ] **GA-06**: System zapisuje historię ewolucji (fitness przez generacje)

### Rule-Based System (RULE)

- [ ] **RULE-01**: System definiuje reguły dla słów kluczowych phishingu (urgent, verify, click here)
- [ ] **RULE-02**: System definiuje reguły dla podejrzanych URL (skrócone, IP, homoglyph)
- [ ] **RULE-03**: System definiuje reguły dla cech strukturalnych (za dużo linków, brak personalizacji)
- [ ] **RULE-04**: System definiuje reguły dla języka pilności i presji czasowej
- [ ] **RULE-05**: Każda reguła ma przypisaną wagę
- [ ] **RULE-06**: System agreguje aktywne reguły do wyniku końcowego
- [ ] **RULE-07**: System zwraca listę aktywnych reguł z uzasadnieniem

### Probabilistic System (PROB)

- [ ] **PROB-01**: System implementuje klasyfikator Naive Bayes dla estymacji prawdopodobieństwa
- [ ] **PROB-02**: System implementuje własny prosty model bayesowski
- [ ] **PROB-03**: System zwraca prawdopodobieństwo posterior przynależności do klasy phishing
- [ ] **PROB-04**: System dostarcza kontekst wiarygodności dla wyników ML

### Decision Aggregation (AGG)

- [ ] **AGG-01**: System łączy wyniki z ML ensemble, systemu regułowego i probabilistycznego
- [ ] **AGG-02**: System wykrywa rozbieżności między paradygmatami i flaguje edge cases
- [ ] **AGG-03**: System generuje końcową decyzję (phishing/bezpieczny) z poziomem pewności
- [ ] **AGG-04**: System przypisuje wagi do każdego paradygmatu w końcowej decyzji

### Explainability (EXPL)

- [ ] **EXPL-01**: System wyświetla które reguły eksperckie zadziałały z wagami
- [ ] **EXPL-02**: System wyświetla SHAP/LIME feature importance dla decyzji ML
- [ ] **EXPL-03**: System wyświetla porównanie predykcji wszystkich klasyfikatorów
- [ ] **EXPL-04**: System wyjaśnia rozbieżności między metodami gdy występują
- [ ] **EXPL-05**: System generuje raport wyjaśniający decyzję w formie tekstowej

### Web Application (WEB)

- [ ] **WEB-01**: Aplikacja wyświetla formularz do wklejenia tekstu/URL
- [ ] **WEB-02**: Aplikacja obsługuje upload plików (eml, obrazy, CSV)
- [ ] **WEB-03**: Aplikacja wyświetla wynik analizy z poziomem pewności
- [ ] **WEB-04**: Aplikacja wyświetla dashboard z wizualizacjami (wykresy, porównania)
- [ ] **WEB-05**: Aplikacja wyświetla porównanie wyników wszystkich modeli
- [ ] **WEB-06**: Aplikacja wyświetla szczegółowe wyjaśnienie decyzji
- [ ] **WEB-07**: Aplikacja pozwala na batch processing wielu próbek
- [ ] **WEB-08**: Aplikacja jest responsywna i działa na urządzeniach mobilnych

### Model Management (MODEL)

- [ ] **MODEL-01**: System zapisuje wytrenowane modele do pliku (pickle/joblib)
- [ ] **MODEL-02**: System wczytuje zapisane modele przy starcie
- [ ] **MODEL-03**: System pozwala na porównanie różnych wersji modeli
- [ ] **MODEL-04**: System loguje metryki każdej wersji modelu
- [ ] **MODEL-05**: System pozwala na wybór aktywnej wersji modelu

### Evaluation (EVAL)

- [ ] **EVAL-01**: System oblicza accuracy, precision, recall, F1-score
- [ ] **EVAL-02**: System oblicza AUC-ROC dla każdego klasyfikatora
- [ ] **EVAL-03**: System generuje macierz pomyłek (confusion matrix)
- [ ] **EVAL-04**: System porównuje modele bazowe vs zoptymalizowane GA
- [ ] **EVAL-05**: System analizuje wpływ grup cech na wynik klasyfikacji
- [ ] **EVAL-06**: System generuje raporty ewaluacyjne w formacie eksportowalnym

### Documentation (DOC)

- [ ] **DOC-01**: Kod zawiera docstringi dla wszystkich funkcji i klas
- [ ] **DOC-02**: README zawiera instrukcje instalacji i uruchomienia
- [ ] **DOC-03**: API jest udokumentowane w formacie OpenAPI/Swagger
- [ ] **DOC-04**: Dokumentacja zawiera diagramy architektury systemu
- [ ] **DOC-05**: Dokumentacja zawiera diagramy przepływu danych
- [ ] **DOC-06**: Dokumentacja zawiera opis teoretyczny algorytmów
- [ ] **DOC-07**: Dokumentacja spełnia wymagania pracy inżynierskiej

### Data Pipeline (DATA)

- [ ] **DATA-01**: System pobiera i przetwarza publiczne datasety phishingowe
- [ ] **DATA-02**: System implementuje temporal split (nie random) dla train/test
- [ ] **DATA-03**: System obsługuje class imbalance (SMOTE, undersampling, class weights)
- [ ] **DATA-04**: System waliduje jakość danych wejściowych
- [ ] **DATA-05**: System cachuje przetworzone cechy dla szybszego retreningu

## v2 Requirements

### Advanced Features

- **ADV-01**: Real-time API endpoint dla integracji z innymi systemami
- **ADV-02**: Monitoring concept drift i automatyczne alerty
- **ADV-03**: Active learning z feedbackiem użytkownika
- **ADV-04**: Browser extension do analizy w czasie rzeczywistym
- **ADV-05**: Integracja z bazami reputacji domen (VirusTotal, PhishTank)

### Infrastructure

- **INFRA-01**: Konteneryzacja Docker z docker-compose
- **INFRA-02**: CI/CD pipeline z automatycznymi testami
- **INFRA-03**: Monitoring i alerting (Prometheus/Grafana)
- **INFRA-04**: Load balancing dla wysokiej dostępności

## Out of Scope

| Feature | Reason |
|---------|--------|
| Logowanie użytkowników / autoryzacja | Open demo wystarczy dla demonstratora akademickiego |
| Real-time monitoring strumienia wiadomości | Batch analysis wystarcza dla pracy inżynierskiej |
| Integracja z klientami pocztowymi | Standalone aplikacja, poza zakresem pracy |
| Aplikacja mobilna natywna | Web-first, responsywny interfejs wystarczy |
| GPU training / deep learning transformers | Klasyczne ML wystarczy, ograniczenia sprzętowe |
| Komercyjna baza reputacji (płatna) | Publiczne źródła wystarczą |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INPUT-01 | Phase 2 | Pending |
| INPUT-02 | Phase 6 | Pending |
| INPUT-03 | Phase 6 | Pending |
| INPUT-04 | Phase 7 | Pending |
| INPUT-05 | Phase 8 | Pending |
| INPUT-06 | Phase 7 | Pending |
| INPUT-07 | Phase 7 | Pending |
| FEAT-01 | Phase 2 | Pending |
| FEAT-02 | Phase 6 | Pending |
| FEAT-03 | Phase 6 | Pending |
| FEAT-04 | Phase 6 | Pending |
| FEAT-05 | Phase 2 | Pending |
| FEAT-06 | Phase 6 | Pending |
| FEAT-07 | Phase 6 | Pending |
| FEAT-08 | Phase 2 | Pending |
| ML-01 | Phase 2 | Pending |
| ML-02 | Phase 3 | Pending |
| ML-03 | Phase 3 | Pending |
| ML-04 | Phase 3 | Pending |
| ML-05 | Phase 3 | Pending |
| ML-06 | Phase 3 | Pending |
| ML-07 | Phase 3 | Pending |
| ML-08 | Phase 2 | Pending |
| ENS-01 | Phase 3 | Pending |
| ENS-02 | Phase 3 | Pending |
| ENS-03 | Phase 3 | Pending |
| ENS-04 | Phase 3 | Pending |
| ENS-05 | Phase 3 | Pending |
| GA-01 | Phase 4 | Pending |
| GA-02 | Phase 4 | Pending |
| GA-03 | Phase 4 | Pending |
| GA-04 | Phase 4 | Pending |
| GA-05 | Phase 4 | Pending |
| GA-06 | Phase 4 | Pending |
| RULE-01 | Phase 5 | Pending |
| RULE-02 | Phase 5 | Pending |
| RULE-03 | Phase 5 | Pending |
| RULE-04 | Phase 5 | Pending |
| RULE-05 | Phase 5 | Pending |
| RULE-06 | Phase 5 | Pending |
| RULE-07 | Phase 5 | Pending |
| PROB-01 | Phase 5 | Pending |
| PROB-02 | Phase 5 | Pending |
| PROB-03 | Phase 5 | Pending |
| PROB-04 | Phase 5 | Pending |
| AGG-01 | Phase 5 | Pending |
| AGG-02 | Phase 5 | Pending |
| AGG-03 | Phase 5 | Pending |
| AGG-04 | Phase 5 | Pending |
| EXPL-01 | Phase 9 | Pending |
| EXPL-02 | Phase 9 | Pending |
| EXPL-03 | Phase 9 | Pending |
| EXPL-04 | Phase 9 | Pending |
| EXPL-05 | Phase 9 | Pending |
| WEB-01 | Phase 8 | Pending |
| WEB-02 | Phase 8 | Pending |
| WEB-03 | Phase 8 | Pending |
| WEB-04 | Phase 9 | Pending |
| WEB-05 | Phase 3 | Pending |
| WEB-06 | Phase 9 | Pending |
| WEB-07 | Phase 8 | Pending |
| WEB-08 | Phase 8 | Pending |
| MODEL-01 | Phase 2 | Pending |
| MODEL-02 | Phase 2 | Pending |
| MODEL-03 | Phase 4 | Pending |
| MODEL-04 | Phase 4 | Pending |
| MODEL-05 | Phase 4 | Pending |
| EVAL-01 | Phase 2 | Pending |
| EVAL-02 | Phase 2 | Pending |
| EVAL-03 | Phase 2 | Pending |
| EVAL-04 | Phase 4 | Pending |
| EVAL-05 | Phase 10 | Pending |
| EVAL-06 | Phase 10 | Pending |
| DOC-01 | Phase 1 | Pending |
| DOC-02 | Phase 1 | Pending |
| DOC-03 | Phase 10 | Pending |
| DOC-04 | Phase 10 | Pending |
| DOC-05 | Phase 10 | Pending |
| DOC-06 | Phase 10 | Pending |
| DOC-07 | Phase 10 | Pending |
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 68 total
- Mapped to phases: 68
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-09*
*Last updated: 2026-02-09 after roadmap creation*
