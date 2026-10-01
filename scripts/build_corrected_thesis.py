#!/usr/bin/env python3
"""Build a corrected DOCX of the thesis from the PDF text extraction.

Pipeline: pdftotext -layout praca-inzynierska.pdf  ->  clean  ->  inject
corrections (verified numbers, rebuilt tables, editorial fixes, errata)  ->
Markdown  ->  pandoc  ->  praca-inzynierska-poprawiona.docx

Honesty note: figures/screenshots cannot be recovered from a text extraction;
their locations are marked [RYSUNEK — wstaw obraz z oryginału]. The author does
a final formatting/figures pass. All numeric corrections come from the honest
evaluation scripts in scripts/ and the reports in reports/.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_TXT = Path("/tmp/praca_txt.txt")
OUT_MD = ROOT / "reports/praca-poprawiona.md"
OUT_DOCX = ROOT / "praca-inzynierska-poprawiona.docx"

AUTHOR = "Łukasz Drążek"  # z konta; potwierdź pisownię / uzupełnij promotora

# ---- ERRATA block prepended to the document -------------------------------
ERRATA = f"""# Wykaz poprawek (errata) — wersja poprawiona

**Autor:** {AUTHOR}  **Promotor:** [do uzupełnienia]

Niniejsza wersja nanosi poprawki wynikające z recenzji. Kluczowe zmiany
merytoryczne (zweryfikowane w kodzie i udokumentowane skryptami w `scripts/`
oraz raportami w `reports/`):

- **U1 — miara rozbieżności.** Naprawiono normalizację entropii: dzielenie przez
  log2(2)=1 (liczba klas), nie przez log2(liczby głosujących). Próg 0,7 jest
  teraz osiągalny i `is_edge_case` działa. Skrypt: `src/*/disagreement.py`,
  testy: `tests/test_disagreement.py`.
- **U2/U3 — wyniki URL.** Wszystkie warianty oceniono na jednym wspólnym
  odłożonym teście (`scripts/evaluate_url_models_honest.py`,
  `reports/url_eval_honest.csv`). Rozdzielono F1 testowe od CV-fitness.
- **U4 — e-mail/SMS.** Liczby pochodzą z 5-krotnej CV na danych syntetycznych
  (`scripts/evaluate_email_sms_honest.py`), nie z metadanych modeli.
- **U9/U10 — latencja i warstwy.** Latencja jako rozkład (mediana 15 ms, p95
  16 ms); wkład warstw zmierzony — agregator nie poprawił decyzji względem
  samego ML (`scripts/evaluate_latency_and_layers.py`).
- **U6** — ujednolicono: trzy warstwy decyzyjne (ML, reguły, Bayes) + GA jako
  wcześniejsza optymalizacja (nie „cztery podejścia").
- **U7** — poprawiono opis Optuny (domyślny sampler TPE, nie proces Gaussa).
- **U5/U8/U11/U12** — okładka, zakres demonstratora, listingi, numeracja.

---

"""

# ---- Rebuilt Chapter-5 results (verified numbers) -------------------------
RESULTS = """
# Rozdział 5 — Wyniki (wersja poprawiona)

> Wszystkie wyniki URL pochodzą z jednego protokołu: wspólny odłożony zbiór
> testowy z artefaktu `cache/url_training_data.joblib` (200 train / 50 test,
> 25/25, 30 cech), podział **losowy stratyfikowany** (`random_state=42`) —
> **nie temporalny**. Skrypt: `scripts/evaluate_url_models_honest.py`, raport:
> `reports/url_eval_honest.csv`. Mały zbiór testowy (50 próbek) oznacza, że
> różnice są orientacyjne.

## 5.2–5.3. Klasyfikatory: baza vs GA na tym samym teście

| Klasyfikator | F1 baza (test) | F1 GA (test) | Zysk (test) | CV-fitness (osobno) |
|---|---|---|---|---|
| Logistic Regression | 0,9200 | 0,9362 | +0,0162 | 0,9749 |
| Random Forest | 0,9091 | 0,9259 | +0,0168 | 0,9705 |
| MLP | 0,9167 | 0,9583 | +0,0417 | 0,9697 |
| XGBoost | 0,9231 | 0,9259 | +0,0028 | 0,9623 |
| SVM (RBF) | 0,8846 | 0,9020 | +0,0173 | 0,9502 |
| Naive Bayes | 0,9020 | 0,9020 | +0,0000 | 0,9438 |
| Decision Tree | 0,8980 | 0,9259 | +0,0280 | 0,9656 |

Na wspólnym teście optymalizacja GA daje niewielką poprawę F1 (od +0,000 dla
Naive Bayes do +0,042 dla MLP). Kolumna „CV-fitness" to F1 z 5-krotnej walidacji
krzyżowej najlepszego osobnika i jest **inną wielkością** niż wynik testowy;
wcześniej raportowane większe „zyski" wynikały z odejmowania tych dwóch wielkości
i nie są poprawnym oszacowaniem poprawy na teście.

## 5.4. Zespoły (ten sam test)

| Wariant | F1 (test) |
|---|---|
| Hard voting | 0,9200 |
| Soft voting | 0,9231 |
| Stacking | 0,9231 |
| **Najlepszy pojedynczy (MLP-GA)** | **0,9583** |

Na wspólnym zbiorze testowym zespoły osiągają F1 ≈ 0,92 i **nie przewyższają**
najlepszego pojedynczego modelu zoptymalizowanego GA (MLP, 0,958). Wynik nie
potwierdza przewagi zespołów i tak jest opisany.

## 5.5. Modele wyspecjalizowane (e-mail, SMS) — dane syntetyczne

| Typ | 5-fold CV acc | 5-fold CV F1 |
|---|---|---|
| E-mail (65 cech) | 0,985 | 0,984 |
| SMS (70 cech) | 1,000 | 1,000 |

Wartości pochodzą z 5-krotnej stratyfikowanej walidacji krzyżowej na zbiorze
**syntetycznym** (200 próbek/typ; `scripts/evaluate_email_sms_honest.py`).
Zapisane w modelach `test_accuracy=1,0` to wynik na danych treningowych
(memoryzacja), nie miara generalizacji. Wynik SMS równy 1,0 wynika z trywialnej
separowalności danych syntetycznych. Żaden z tych wyników nie mierzy skuteczności
na rzeczywistych wiadomościach.

## 5.6. System wielowarstwowy — wkład warstw i latencja

Na zbiorze 50 etykietowanych adresów (40 phishingowych z OpenPhish, 10 znanych
legalnych) sam zespół ML osiągnął dokładność 0,96, a pełny agregator
trójwarstwowy 0,92. Agregator zmienił dwie decyzje względem samego ML i **obie
okazały się błędne** (prawdziwy phishing oznaczony jako legalny, w obu przypadkach
z flagą rozbieżności). Przy domyślnych wagach (ML 0,5; reguły 0,3; Bayes 0,2)
i prawdopodobnie źle skalibrowanym posteriorze Bayesa warstwy regułowa i
bayesowska obniżają prawdopodobieństwo phishingu poniżej progu. W badanym zakresie
integracja trzech warstw nie poprawiła decyzji względem samego ML.

**Miara rozbieżności (poprawiona).** Wskaźnik rozbieżności to znormalizowana
entropia Shannona rozkładu głosów, dzielona przez maksymalną entropię binarną
log2(2)=1. Dla trzech warstw każda niejednomyślność daje wynik ≈ 0,918, a
jednomyślność 0. Dla siedmiu klasyfikatorów najbardziej wyrównany podział 4/3
daje maksimum ≈ 0,985. Próg oznaczania przypadku granicznego ustawiono na 0,7:
dla warstw oznacza to „paradygmaty nie są jednomyślne", a dla zespołu ML —
„co najmniej dwa z siedmiu klasyfikatorów są odmiennego zdania".

**Latencja.** Pomiar `/predict/multi-paradigm` (50 żądań, model rozgrzany,
cechy leksykalne, pomiar in-process): mediana 15 ms, 95. percentyl 16 ms —
poniżej wymaganych 500 ms.

---
"""


def clean(text: str) -> str:
    lines = text.splitlines()
    out = []
    for ln in lines:
        s = ln.rstrip()
        # drop bare page numbers
        if re.fullmatch(r"\s*\d{1,3}\s*", s):
            continue
        # collapse TOC dot leaders "Tytuł ....... 12" -> "Tytuł — 12"
        s = re.sub(r"\.{4,}\s*", " — ", s)
        out.append(s)
    return "\n".join(out)


# Reliable inline text corrections (U6, U7) keyed on exact phrases.
INLINE = [
    (r"czterech\s+uzupełniających\s+się\s+podejść",
     "trzech warstwach decyzyjnych (zespół ML, reguły, klasyfikator bayesowski) "
     "z algorytmem genetycznym jako wcześniejszą optymalizacją modeli"),
    (r"analizie\s+czterech\s+uzupełniających",
     "analizie trzech uzupełniających"),
    (r"\[Imię i Nazwisko Autora\]", AUTHOR),
]


def main():
    if not SRC_TXT.exists():
        print("Brak /tmp/praca_txt.txt — uruchom: pdftotext -layout praca-inzynierska.pdf /tmp/praca_txt.txt")
        return 1
    body = clean(SRC_TXT.read_text(encoding="utf-8", errors="replace"))
    for pat, rep in INLINE:
        body, n = re.subn(pat, rep, body, flags=re.IGNORECASE)
    # Assemble: errata + rebuilt results + original body (as reference text)
    md = (ERRATA + RESULTS +
          "# Treść pracy (z ekstrakcji — do finalnego składu; rysunki do wstawienia)\n\n"
          "> Uwaga: poniższy tekst pochodzi z automatycznej ekstrakcji PDF; pandoc\n"
          "> zlewa złamane wiersze w akapity. Tabele i wyniki Rozdziału 5 zastąp\n"
          "> wersjami z sekcji powyżej. Rysunki (zrzuty ekranu) wstaw ręcznie z\n"
          "> oryginału — ekstrakcja tekstu ich nie zawiera.\n\n"
          + body + "\n")
    OUT_MD.write_text(md, encoding="utf-8")
    subprocess.run(["pandoc", str(OUT_MD), "-o", str(OUT_DOCX)], check=True)
    print(f"OK -> {OUT_DOCX.relative_to(ROOT)} ({OUT_DOCX.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
