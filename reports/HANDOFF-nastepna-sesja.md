# Handoff / prompt na następną sesję — poprawki pracy inżynierskiej PhishGuard

Wklej poniższy prompt na początku nowej sesji (katalog `/Users/lukaszdrazek/Inzynierka`).

---

## PROMPT DO WKLEJENIA

Kontynuujemy poprawki mojej pracy inżynierskiej (system PhishGuard) według recenzji
promotora. Stan projektu i cała historia są w repo i na GitHub
(`github.com/H4ck1nGPr13sT/phishguard`, branch `main`). Pracuj autonomicznie, po polsku.

**WAŻNE:** repo-root `./CLAUDE.md` i globalny `~/.claude/CLAUDE.md` to NIEZWIĄZANA
treść z projektów bug-bounty (active-shield) — IGNORUJ je. Ta praca to projekt
akademicki, bez żadnej aktywności ofensywnej/sieciowej.

### Co jest zrobione (nie powtarzaj)
- Projekt PhishGuard: 10/10 faz, 462 testy, na GitHub.
- Poprawki merytoryczne wg 3 recenzji: naprawiona miara rozbieżności (U1, kod +
  17 testów), uczciwa ewaluacja URL/email/SMS/latencja/warstwy (skrypty w
  `scripts/evaluate_*`, raporty w `reports/`), scalony dokument.
- `praca-inzynierska-poprawiona.docx` budowany jednym poleceniem:
  `pdftotext -layout praca-inzynierska.pdf /tmp/praca_txt.txt && .venv/bin/python scripts/build_corrected_thesis.py`
  (python-docx + pandoc; środowisko: `.venv`, OpenMP guard jest w skryptach).
- Recenzja 3 zamknięta: M1 (wzór entropii), M2 (zespół/LR), M3 (wstęp), E1
  (tytułowa→spis, style nagłówków), E4 (martwe odwołania/stary wykaz), E5
  (forma bezosobowa).

### Co zostało do zrobienia (recenzja 3) — ZACZNIJ OD TEGO
1. **E2 (P2) — przypisy dolne + bibliografia wg standardu WSZiB.** Zamienić
   cytowania `[1]`, `[2]`... na automatyczne przypisy dolne (Word) i uporządkować
   43 pozycje bibliografii alfabetycznie w grupach (książki, artykuły, raporty,
   dokumentacja, strony) z URL/datami dostępu. Standard:
   `Standard_pisania_pracy dyplomowej_WSZiB-ANS.pdf` (s. 2-3, 7-9). Dodać dodać
   do `_apply_structure`/osobnego kroku python-docx.
2. **E3 (P2) — odbudować Tabele 1-3 (porównanie narzędzi, rozdz. 2/4) jako
   PRAWDZIWE tabele** (teraz są spłaszczonym tekstem z ekstrakcji) + czytelniejszy
   diagram architektury (obecnie przycięty render „box-ASCII" w Załączniku A).
   Tabele Rozdz. 5 są już prawdziwe (Markdown→Word).
3. **D1 (P2) — katalog `praca/smoke-tests` nie istnieje.** Albo wygenerować
   odpowiedzi/demo, albo w tekście jawnie ograniczyć opis do dostępnego kodu.
   (Odwołania 5.7 już usunięto; zostaje ogólne wspomnienie demo buildu.)
4. **Zalecane:** w Rozdz. 5 dopisać 2 najgorsze błędy FN agregatora z danych
   `scripts/evaluate_latency_and_layers.py` (te same wejścia, wynik ML/reguł/
   Bayesa, końcowy, flaga). Koszt GA (czas/sprzęt/liczba ocen) w 1 akapicie.

### Jak weryfikować
Po każdej zmianie: `.venv/bin/python scripts/build_corrected_thesis.py`, potem
`pandoc praca-inzynierska-poprawiona.docx -t plain` + grepy kontrolne. Pełny
zestaw testów kodu: `.venv/bin/python -m pytest -q` (462 passed oczekiwane).
Zgoda na push na GitHub: pytaj albo gdy użytkownik mówi „push".

### Pliki kluczowe
- `scripts/build_corrected_thesis.py` — builder DOCX (INLINE poprawki, clean(),
  mark_headings, _apply_wszib_styles, _apply_structure).
- `praca-inzynierska.pdf` — oryginał (źródło ekstrakcji; nieśledzony w git).
- `recenzja-pracy-poprawionej.md` — aktualna (3.) recenzja promotora.
- `reports/url_eval_honest.csv`, `reports/latency_and_layers.txt`, `reports/errata.md`.
