# PhishGuard — System Wykrywania Phishingu

## What This Is

Zintegrowany system wykrywania ataków phishingowych, łączący cztery podejścia analityczne: uczenie maszynowe (7 klasyfikatorów), algorytmy ewolucyjne (optymalizacja hiperparametrów), system regułowy (wiedza ekspercka) oraz probabilistyczny system ekspertowy. System analizuje e-maile, SMS-y, komunikaty tekstowe oraz obrazy (OCR + cechy wizualne). Aplikacja webowa służy jako demonstrator akademicki z potencjałem produkcyjnym.

## Core Value

Integracja wielu paradygmatów analizy w jeden spójny system, gdzie rozbieżności między metodami dostarczają dodatkowego kontekstu i zwiększają wiarygodność decyzji klasyfikacyjnej.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] System analizy treści tekstowych (e-maile, SMS-y, komunikaty)
- [ ] System analizy obrazów (OCR + cechy wizualne)
- [ ] Pipeline ekstrakcji cech (długościowe, leksykalne, składniowe, stylometryczne, URL, sentyment)
- [ ] 7 klasyfikatorów ML (Random Forest, SVM, MLP, Gradient Boosting, Logistic Regression, Naive Bayes, Decision Tree)
- [ ] Algorytm genetyczny do optymalizacji hiperparametrów
- [ ] System regułowy kodujący wiedzę ekspercką
- [ ] System probabilistyczny (Naive Bayes + własny model bayesowski)
- [ ] Mechanizm agregacji wyników z wielu metod
- [ ] Wyjaśnienia decyzji (które reguły/cechy zadziałały)
- [ ] Aplikacja webowa — open demo
- [ ] Wizualizacja porównania metod
- [ ] Zapis i ponowne użycie wytrenowanych modeli
- [ ] Ewaluacja (accuracy, precision, recall, F1, AUC)
- [ ] Dokumentacja techniczna i teoretyczna

### Out of Scope

- Logowanie użytkowników / autoryzacja — open demo wystarczy
- Real-time monitoring strumienia wiadomości — batch analysis
- Integracja z klientami pocztowymi — standalone aplikacja
- Mobile app — web-first

## Context

**Kontekst akademicki:**
- Praca inżynierska na temat wykrywania phishingu
- Wymaga pełnej dokumentacji teoretycznej (opisy algorytmów, diagramy, analiza)
- Główny nacisk na pokazanie synergii 4 podejść analitycznych

**Dane:**
- Trzeba znaleźć publiczne datasety phishingowych wiadomości
- Potencjalne źródła: Kaggle, UCI ML Repository, APWG, Nazario phishing corpus

**Typy analizowanych treści:**
- E-maile (nagłówki, treść, linki)
- SMS-y (smishing)
- Komunikaty tekstowe (chat, social media)
- Obrazy (OCR do ekstrakcji tekstu + analiza wizualna)

## Constraints

- **Timeline**: 2-3 miesiące na pełną implementację
- **Tech stack**: Python (scikit-learn, DEAP/PyGAD dla GA), web framework do ustalenia
- **Dane**: Publiczne datasety — brak dostępu do danych komercyjnych
- **Cel**: Demonstrator akademicki — nie wymaga skalowalności produkcyjnej

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Open demo bez logowania | Uproszczenie architektury, łatwiejszy dostęp dla recenzentów | — Pending |
| OCR + cechy wizualne dla obrazów | Pełniejsza analiza phishingu w formie graficznej | — Pending |
| Wyjaśnienia decyzji w output | Interpretowalność kluczowa dla pracy akademickiej | — Pending |
| Integracja 4 metod jako core value | Główna teza pracy — synergia podejść | — Pending |

---
*Last updated: 2026-02-09 after initialization*
