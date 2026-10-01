# Recenzja robocza poprawionej pracy inżynierskiej

**Data analizy:** 1 października 2026 r.  
**Charakter:** materiał dla promotora i autora; bez formalnej decyzji o dopuszczeniu i bez oceny liczbowej.

## 1. Metryka analizy i kalibracja

**Praca oceniana:** [praca-inzynierska-poprawiona.docx](/Users/lukaszdrazek/Inzynierka/praca-inzynierska-poprawiona.docx), Łukasz Drążek, „Wykrywanie ataków typu phishing poprzez analizę treści wiadomości z wykorzystaniem metod uczenia maszynowego”, system PhishGuard. Rolę potwierdzają karta tytułowa wewnątrz DOCX oraz opis celu i implementacji. Przyjmuję etap **przed obroną** i brak dalszych ustaleń promotora.

**Kryteria:** dostępny [Standard pisania pracy dyplomowej WSZiB–ANS](</Users/lukaszdrazek/Inzynierka/Standard_pisania_pracy dyplomowej_WSZiB-ANS.pdf>), 9 stron, zwłaszcza s. 2–7; wcześniej omówiona jednostronicowa instrukcja „WSZiB-praca-inżynierska-i-obrona.pdf” (jej plik źródłowy jest obecnie niedostępny); [wzorzec 1](/Users/lukaszdrazek/Inzynierka/praca-inz-1.pdf), Gabriel Źrebiec, 44 strony; [wzorzec 2](/Users/lukaszdrazek/Inzynierka/praca-inz-2.pdf), Natalia Aleksandra Derwecka, 48 stron. Role wzorców potwierdzają strony tytułowe. Wzorce służą tylko kalibracji jakości opisu. Standard jest dostarczoną kopią, ale nie udało się potwierdzić w SUSZI, czy jest najnowszą obowiązującą wersją; [odnośnik wskazany wcześniej w instrukcji](https://suszi.wszib.edu.pl/suszi-web/noticeboard/92) był niedostępny.

**Zakres:** przeczytano cały tekst DOCX, wszystkie trzy jego rzeczywiste tabele, zawartość bibliografii, przypisów, wykazów, wstawionych czterech obrazów i dwóch listingów w aneksie. Zbadano standard w całości i wskazane fragmenty wzorców. Sprawdzono dołączone skrypty oraz raporty istotne dla głównych twierdzeń. Uruchomiono 17 testów modułu rozbieżności (wszystkie przeszły), skrypt oceny e-mail/SMS oraz ponownie skrypt pomiaru czasu i wkładu warstw. **Nie udało się wyrenderować DOCX do PDF**, a dokument nie ma zapisanych granic renderowanych stron. Dlatego lokalizacje w nowej pracy podaję jako rozdział i **numer akapitu DOCX** (licząc od zera według kolejności dokumentu); odziedziczone numery stron starego PDF widoczne w treści nie są numerami tej wersji. Nie przypisuję nowej pracy fikcyjnych stron.

**Moduły tematyczne:** ML/NLP i optymalizacja. Ocena obrazów, systemów agentowych, IoT i generowania treści — nie dotyczy deklarowanego zakresu tej wersji. Kierunki metodologiczne przekazane przez promotora stosuję jako **zalecenia jakościowe**. Oficjalne wymogi oznaczam jako **wymóg uczelni**; dodatkowe badania, które nie są niezbędne dla zachowanych twierdzeń, jako **opcjonalne rozszerzenie**.

## 2. Werdykt roboczy

**Wymaga istotnych poprawek.** Autor ma rozpoznawalny produkt i wkład własny: ekstrakcję cech, klasyfikatory, strojenie GA, reguły, Bayesa, agregację, API i demonstrator (rozdz. 4, akapity 220–434). Poprawiono główny błąd matematyczny flagi rozbieżności. Nowe wyniki URL mają wspólny test, a autor uczciwie przyznaje, że zespół modeli i agregator nie poprawiły wyników w przedstawionych porównaniach (nowa sekcja wyników, akapity 14–24).

Przekazany DOCX **nie jest jednak jednolitą poprawioną pracą**. Przed kartą tytułową zawiera erratę i nową wersję wyników, potem polecenie redakcyjne do zastąpienia starego rozdziału, a następnie cały stary rozdział 5 i stare podsumowanie z przeciwnymi wnioskami (akapity 0–27, 112–125, 435–556). Zmiany nie zostały scalone. Dodatkowo jedna nowa interpretacja metadanych e-mail/SMS jest sprzeczna z kodem treningowym, a demonstracyjne 50 adresów częściowo pokrywa się z danymi użytymi do treningu URL. To uniemożliwia rzetelną rekomendację dopuszczenia **tego egzemplarza**, mimo realnej poprawy analizy.

## 3. Mocne strony

1. **Problem i wkład są konkretne:** cel, odbiorca, rodzaje wejścia i komponenty są rozpoznawalne we wstępie (ak. 123–128), wymaganiach (rozdz. 3) i opisie realizacji (rozdz. 4).
2. **Naprawiono flagę rozbieżności:** nowa sekcja wyników, ak. 23, podaje właściwą normalizację entropii binarnej. Kod obu modułów używa maksimum 1 bit; 17 ukierunkowanych testów przeszło.
3. **Nowy test URL jest porównywalny wewnętrznie:** ak. 14–18 oraz [raport CSV](/Users/lukaszdrazek/Inzynierka/reports/url_eval_honest.csv) rozdzielają F1 odłożonego testu od pięciokrotnego CV. Dla MLP: 0,9167 wobec 0,9583, czyli +0,0417 na tych samych 50 próbkach.
4. **Wynik niekorzystny nie został ukryty w nowej sekcji:** ak. 18 mówi, że zespół (F1 około 0,92) nie pobił pojedynczego MLP-GA (0,9583); ak. 22 mówi, że agregator miał 46/50 poprawnych decyzji wobec 48/50 dla samego ML.
5. **Podano granice pomiarów:** ak. 14 wskazuje losowy, a nie temporalny podział, ak. 20 ogranicza wyniki e-mail/SMS do danych syntetycznych, ak. 24 precyzuje pomiar czasu „in-process”. Te zastrzeżenia należy przenieść do jedynej końcowej wersji pracy.

## 4. Zgodność z instrukcją i dostarczonym standardem

| Wymaganie | Podstawa kryterium | Lokalizacja w DOCX | Status | Konieczna poprawka |
|---|---|---|---|---|
| Strona tytułowa jako pierwszy element, spis treści, wstęp, tekst, zakończenie, bibliografia, wykazy | **Wymóg uczelni**, standard s. 2–4 | Ak. 0–27: errata i nowe wyniki; karta tytułowa dopiero ak. 112–114 | **Niespełnione** | Złożyć jedną pracę w kolejności standardu; erratę przekazać osobno promotorowi. |
| Wstęp: motywacja, cel, zakres, metoda, opis rozdziałów | **Wymóg uczelni**, standard s. 2; poprzednia instrukcja: około 1–2 strony | Wstęp ak. 122–128 | **Częściowo** | Dodać jawny zakres danych i zastosowanej ewaluacji; usunąć zdanie po automatycznej podmianie, które miesza trzy warstwy z czterema technikami. Objętości nie da się ocenić bez składu. |
| Problem, przegląd, wizja, wykonalność i ryzyka | **Wymóg poprzedniej instrukcji** | Rozdz. 2, ak. 129–192 | **Częściowo** | Utrzymać treść, doprecyzować kryteria porównania istniejących narzędzi i źródła liczb; nie powielać teorii kosztem projektu. |
| Aktorzy, współpracujące systemy, funkcje i wymagania jakościowe | **Wymóg poprzedniej instrukcji** | Rozdz. 3, ak. 193–219 | **Częściowo** | Powiązać kluczowe wymagania z wynikami i warunkami akceptacji, szczególnie dla e-mail/SMS oraz czasu odpowiedzi. |
| Realizacja i własne decyzje | **Wymóg poprzedniej instrukcji**; część metodyczna w standardzie s. 2 | Rozdz. 4, ak. 220–434 | **Częściowo** | Zachować opis mechanizmów, poprawić diagram i spłaszczenia tabel/listingów; jednoznacznie oddzielić optymalizację podczas treningu od trzech głosów podczas predykcji. |
| Wyniki, weryfikacja, ograniczenia | **Wymóg uczelni**, standard s. 2–3 i poprzednia instrukcja | Nowe wyniki ak. 13–24; stare wyniki ak. 435–523 | **Niespełnione w tej wersji** | Włączyć zweryfikowane dane do rozdz. 5, usunąć stare tabele i sprzeczne wnioski; opisać pochodzenie próbek oraz zależność między próbami. |
| Zakończenie powiązane z celem i wynikami | **Wymóg uczelni**, standard s. 3 | Ak. 534–556 | **Niespełnione w tej wersji** | Napisać jedno zakończenie na podstawie końcowego rozdz. 5; usunąć niepotwierdzoną przewagę zespołów, modeli klasycznych nad głębokimi i brak kosztu skuteczności. |
| Literatura i odwołania | **Wymóg uczelni**, standard s. 2–3 i 7–9 | Bibliografia ak. 557–600 (43 pozycje); w DOCX brak merytorycznych przypisów dolnych | **Częściowo** | Dopasować rzeczywiście użyte źródła, uporządkować je według standardu, wprowadzić automatyczne przypisy dolne i odwołania; minimum 20 pozycji jest liczbowo spełnione, ale samo wyliczenie 43 pozycji nie dowodzi ich wykorzystania. |
| Czytelne, automatycznie numerowane obiekty, podpis i źródło | **Wymóg uczelni**, standard s. 3 i 6–7 | Tylko 3 rzeczywiste tabele w DOCX; dawne Tabele 4–7 jako akapity 446–493; rysunki w aneksie ak. 608–621 | **Częściowo** | Odbudować tabele, numerację, podpisy, źródła i spisy; wymienić nieczytelny diagram. |
| Forma bezosobowa tekstu właściwego | **Wymóg uczelni**, standard s. 2 | Np. rozdz. 4.3 „Do projektu wybrałem”, rozdz. 4.4 „Optymalizację zrealizowałem” | **Częściowo** | Zmienić odpowiednie zdania na formę bezosobową, zachowując informację o decyzjach autora. |
| Plik DOCX do procedury antyplagiatowej | **Wymóg poprzedniej instrukcji** | Plik DOCX dostarczono | **Spełnione co do formatu pliku** | Po scaleniu dostarczyć egzemplarz finalny; samo rozszerzenie nie potwierdza gotowości formalnej. |

W [standardzie, s. 3–7](</Users/lukaszdrazek/Inzynierka/Standard_pisania_pracy dyplomowej_WSZiB-ANS.pdf>) są też konkretne parametry składu: Times New Roman, marginesy 2,5 cm, tekst 12 pkt i interlinia 1,5, nagłówki 16/14 pkt, numeracja stron w stopce. W metadanych DOCX style „Normal” i „Heading 1/2” oraz marginesy są ustawione zgodnie z tymi wartościami. **Wygląd po renderowaniu, ciągłość numeracji stron i zgodność wszystkich akapitów są nieweryfikowalne** bez końcowego PDF lub widoku Worda. Standard używa formuły „PRACA DYPLOMOWA” dla studiów I stopnia (s. 3), podczas gdy karta DOCX i wzorzec 1 używają „PRACA DYPLOMOWA INŻYNIERSKA”; tę rozbieżność formalną należy uzgodnić z promotorem lub kartą wygenerowaną przez SAKE, bez traktowania wzorca jako nadrzędnego.

## 5. Macierz spójności projektu

Identyfikatory **R1–R6 są robocze**; nie są numeracją autora.

| Cel / wymaganie | Decyzja i realizacja | Dowód weryfikacji | Luka |
|---|---|---|---|
| R1: sklasyfikować URL | 30 cech, 7 modeli, API; rozdz. 4.2–4.8 | Nowa tabela, ak. 14–18; raport CSV, 50 próbek testowych | Wynik dotyczy małego, losowo podzielonego zbioru; stary rozdz. 5 nadal nazywa test temporalnym. |
| R2: sklasyfikować treść e-mail/SMS | Ekstraktory i zespoły; rozdz. 4.2, 4.8 | Ak. 19–20; pięciokrotne CV na 200 próbkach syntetycznych każdego typu | Te same szablony występują po obu stronach podziałów CV; brak dowodu skuteczności na rzeczywistych wiadomościach. |
| R3: poprawić modele przez GA | Rozdz. 4.4, zoptymalizowane artefakty | Ak. 15–16; F1 na wspólnym teście; zysk 0–0,0417 | Jeden podział nie dowodzi stabilnej poprawy; koszt wyszukiwania nie jest zestawiony z wielkością zysku. |
| R4: zespół poprawia decyzję | Voting/stacking; rozdz. 4.3.8 | Ak. 17–18: F1 0,9200–0,9231 wobec 0,9583 MLP-GA | Teza o przewadze jest obalona na przedstawionym teście, lecz pozostała w starym rozdz. 5 i podsumowaniu. |
| R5: trzy warstwy i flaga rozbieżności | Agregacja ML/reguły/Bayes; rozdz. 4.7 | Ak. 22–23; 48/50 ML wobec 46/50 agregator, dwie błędne zmiany; testy entropii | Flaga działa jako wskaźnik niezgody, ale próba do oceny wkładu warstw częściowo pokrywa się z wejściami treningowymi; nie dowiedziono poprawy klasyfikacji. |
| R6: odpowiedź poniżej 500 ms | Ładowanie modeli, endpoint | Ak. 24: 50 żądań, mediana ok. 15 ms, p95 ok. 16 ms; ponowne uruchomienie: 15,8/17,7 ms | Dowód dotyczy lokalnego TestClient po rozgrzaniu, a nie opóźnienia klient–serwer ani obciążenia równoległego. To wystarcza wyłącznie dla tak zawężonego twierdzenia. |

Łańcuch **problem → cel → wymagania → decyzje → implementacja** jest rozpoznawalny. Przerwanie następuje przy **scaleniu weryfikacji i wniosków** w jednym dokumencie.

## 6. Audyt najważniejszych twierdzeń

| Twierdzenie | Dowód | Ograniczenie | Status | Potrzebne działanie |
|---|---|---|---|---|
| „Próg 0,7 flaguje niezgodę” (ak. 23) | Kod i 17 testów; entropia 2:1 wynosi ok. 0,918, a 4:3 ok. 0,985 | Miara opisuje rozkład głosów, nie poprawność decyzji | **Potwierdzone w podanym zakresie** | Zostawić opis mechanizmu, ale nie nazywać każdej flagi trafnym wykryciem błędu. |
| „GA poprawił F1 na teście” (ak. 15–16) | Wspólny test 50 URL, F1 lepszy dla 6 modeli, remis dla NB | Różnice wynoszą 0–0,0417; pojedynczy losowy podział | **Potwierdzone w podanym zakresie** | Zachować opisowe liczby i warunki; nie uogólniać na inne zbiory ani na typowy bieg GA bez powtórzeń. |
| „Zespoły są lepsze od pojedynczych modeli” (stary rozdz. 5.4, ak. 484) | Nowa sekcja ak. 18 pokazuje przeciwny wynik | Brak spójnej wersji wniosku | **Niepotwierdzone** | Usunąć stare zdanie; zachować negatywny wynik nowej sekcji. |
| „E-mail 0,985 acc / 0,984 F1; SMS 1,0” (ak. 19–20) | Ponowne uruchomienie skryptu dało te same średnie 5-fold CV | Dane syntetyczne, powtarzane szablony; nie jest to test na niezależnych kampaniach | **Częściowo potwierdzone** | Wyraźnie określić jednostkę podziału i zakres wniosku; oddzielny test według szablonu lub rzeczywistych wiadomości dla twierdzenia o generalizacji. |
| „test_accuracy=1,0 to wynik na danych treningowych” (ak. 20) | Kod treningowy tworzy podział 80/20 i zapisuje wynik obliczony na X_test | Skrypt pomocniczy dodatkowo daje 1,0 na całym zbiorze, lecz to inny pomiar | **Niepotwierdzone; potwierdzony błąd interpretacji** | Zmienić zdanie: metadane pochodzą z syntetycznego odłożonego testu 20%, a nowe CV jest osobnym oszacowaniem. |
| „Agregator nie poprawił decyzji na 50 URL” (ak. 22) | Ponownie uzyskano 48/50 wobec 46/50; dwie zmiany obu decyzji były błędne | 13 z pierwszych 40 phishingowych URL należy do 200 próbek treningowych po odtworzeniu doboru danych; 4 do testowych. Próba nie jest niezależnym zbiorem | **Potwierdzone tylko jako obserwacja na tej próbie** | Oznaczyć ją jako test ilustracyjny z pokrywaniem danych; do wniosku o skuteczności zebrać niezależne adresy lub wyłączyć nakładające się próbki i przeliczyć. |
| „p95 poniżej 500 ms” (ak. 24) | Powtórzenie skryptu: 50 odpowiedzi 200, mediana 15,8 ms, p95 17,7 ms | Pomiar lokalny, po rozgrzaniu, jednym klientem in-process | **Potwierdzone w podanym zakresie** | Przepisać dokładny zakres twierdzenia; szerszy pomiar tylko przy deklaracji czasu sieciowego/produkcyjnego. |
| „System łączy cztery podejścia, nie traci skuteczności i konkuruje z sieciami głębokimi” (ak. 535, 540, 542) | Brak odpowiednich porównań; ak. 22 podaje spadek 48/50 → 46/50 | Stare podsumowanie sprzeczne z nową sekcją | **Niepotwierdzone** | Napisać nowe podsumowanie zgodne z wynikami; porównanie z modelem głębokim pozostaje opcjonalne po usunięciu tej tezy. |

## 7. Uwagi szczegółowe

**P1** — przeszkoda dla rzetelnej rekomendacji tej wersji; **P2** — istotna poprawka przed finalną wersją; **P3** — redakcja lub opcjonalne ulepszenie. Priorytety są propozycją dla promotora.

| ID | Priorytet i typ | Lokalizacja i dowód | Problem i skutek | Konkretna poprawka | Kryterium zamknięcia |
|---|---|---|---|---|---|
| K1 | **P1, potwierdzony błąd; wymóg uczelni** | Ak. 0–27 zawierają erratę, rozdz. 5 i polecenie „Tabele i wyniki Rozdziału 5 zastąp”; karta tytułowa jest dopiero w ak. 112–114. Standard s. 2–4. | DOCX jest pakietem roboczym, nie ciągłą pracą w wymaganej kolejności. | Przenieść nowe wyniki do właściwego rozdz. 5, usunąć erratę i polecenia z egzemplarza, ułożyć stronę tytułową na początku. | Jeden spis treści prowadzi do jednej wersji każdego rozdziału i jednej bibliografii. |
| K2 | **P1, potwierdzona sprzeczność; wymóg uczelni i zalecenie jakościowe** | Ak. 14: test URL losowy; ak. 438 i 453: „temporalny”. Ak. 18: zespół nie przewyższa MLP; ak. 484: „wyraźnie lepszą skuteczność”. Ak. 22: agregator 46/50; ak. 542: transparentność „nie wymaga rezygnacji ze skuteczności”. | Dwa zestawy wyników i wniosków mogą prowadzić do przeciwnych ocen celu. | Usunąć stare liczby, podpisy i interpretacje w rozdz. 5 oraz napisać zakończenie na nowo. | Wszystkie liczby, nazwy podziałów i wnioski w całej pracy zgadzają się z jednym wskazanym raportem. |
| K3 | **P2, potwierdzony błąd interpretacji; zalecenie jakościowe** | Ak. 20 nazywa metadane test_accuracy=1,0 „wynikiem na danych treningowych”. [Skrypt treningowy](/Users/lukaszdrazek/Inzynierka/scripts/train_email_sms_models.py) dzieli dane 80/20 i zapisuje accuracy z X_test. | Praca błędnie opisuje własne artefakty. Wniosek o generalizacji nadal jest ograniczony, lecz z innej przyczyny: dane są syntetyczne. | Wyjaśnić trzy różne wielkości: wynik na treningu, odłożonym syntetycznym 20% i nowe CV; wskazać pliki/model. | Terminologia odpowiada kodowi i liczby są przypisane do właściwych prób. |
| K4 | **P2, brak niezależnego dowodu; zalecenie jakościowe związane z celem** | Ak. 19–20; [generator](/Users/lukaszdrazek/Inzynierka/scripts/create_email_sms_dataset.py): po 20 szablonów na klasę e-mail/SMS. W 5 foldach e-mail 38–40 z 40 wiadomości testowych ma temat obecny w treningu. | CV sprawdza głównie nowe warianty znanych szablonów; nie mierzy rozpoznawania nowych kampanii ani rzeczywistych wiadomości. | Dla wąskiego wniosku zachować opis „na wariantach tych szablonów”. Dla tezy o wykrywaniu nowych wiadomości: podział według szablonu lub mały niezależny, ręcznie oznaczony zbiór rzeczywistych wiadomości, z opisem etykiet i błędów. | Raport podaje jednostkę podziału, liczbę wiadomości i szablonów, macierz błędów oraz zakres uogólnienia. |
| K5 | **P2, niejasność zakresu dowodu; zalecenie jakościowe** | Ak. 22 i [skrypt warstw](/Users/lukaszdrazek/Inzynierka/scripts/evaluate_latency_and_layers.py). Pierwsze 40 adresów pochodzi z tego samego pliku OpenPhish co trening; po odtworzeniu losowania 13/40 trafia do train, 4/40 do test. | Wynik 48/50 wobec 46/50 jest poprawną obserwacją zachowania komponentów na tych wejściach, ale nie niezależną oceną dokładności. | Oznaczyć zestaw jako ilustracyjny; dla oceny skuteczności użyć niezależnej próby lub wyłączyć pokrycie i raportować zmianę decyzji oraz FN/FP. | Jawna lista identyfikatorów/deduplicacja potwierdza brak nakładania w zbiorze użytym do uogólnienia. |
| K6 | **P2, potwierdzony brak formalny; wymóg uczelni** | Standard s. 2–3, 7–9 wymaga przypisów dolnych, bibliografii wyłącznie wykorzystanych pozycji, podziału i porządku alfabetycznego. DOCX ma 43 pozycje (ak. 558–600), lecz brak merytorycznych przypisów dolnych; używa odwołań w nawiasach kwadratowych. | Cytowania nie spełniają dostarczonego standardu; część liczb i porównań nie ma łatwego do sprawdzenia pochodzenia. | Wprowadzić automatyczne przypisy dolne, dodać strony/URL i daty odczytu zgodnie ze standardem, uporządkować tylko wykorzystane źródła według kategorii. | Każde ważne twierdzenie ma właściwy przypis, a każda pozycja bibliografii odpowiada odwołaniu. |
| K7 | **P2, potwierdzony problem prezentacji; wymóg uczelni** | Standard s. 6–7; DOCX ma tylko 3 rzeczywiste tabele. W starym rozdz. 5 Tabele 4–7 są spłaszczonym tekstem (ak. 446–493), a diagram w aneksie A (ak. 608–612) ma rozstrzelone litery i rozdzielone strzałki. | Trudno czytać mechanizm i sprawdzać wyniki; podpisy i źródła nie są konsekwentnie powiązane z obiektami. | Odtworzyć tabele jako tabele, narysować czytelny schemat danych i etapów, wprowadzić podpisy nad obiektami, źródła pod nimi, automatyczne wykazy. | Końcowy PDF ma czytelne obiekty i zgodne odwołania. |
| K8 | **P2, potwierdzona niespójność zakresu produktu; zalecenie jakościowe** | Rozdz. 4.9 i stary rozdz. 5.7 odsyłają do praca/smoke-tests, a katalogu nie ma w przekazanym folderze. Ak. 27 sam mówi, że rysunki trzeba ręcznie wstawić; aneks A dodaje rendery starego PDF. | Zrzuty pokazują wybrane stany, ale nie pozwalają prześledzić wszystkich deklarowanych przypadków ani uruchomić osobnego demo. | Dostarczyć odpowiedzi JSON/demo lub w pracy ograniczyć opis do repozytorium i rzeczywiście dostępnych testów. | Każdej przypisanej demonstratorowi funkcji odpowiada dostępny artefakt lub jasno opisane ograniczenie. |
| K9 | **P2, potwierdzony problem redakcyjny; wymóg uczelni** | Rozdz. 4.3 i 4.4: „Do projektu wybrałem”, „Optymalizację zrealizowałem”; standard s. 2 wymaga bezosobowej formy tekstu właściwego. Ak. 125 zawiera niegramatyczną podmianę „na połączonej analizie trzech warstwach ...: uczenia maszynowego, algorytmu ewolucyjnego...”. | Korekta automatyczna stworzyła nowe błędy i zaciera rolę GA. | Przejrzeć cały tekst po scaleniu, stosować formę bezosobową i konsekwentnie mówić o trzech warstwach predykcji oraz GA jako strojenia. | Nie ma automatycznych artefaktów podmiany ani sprzecznych definicji systemu. |
| K10 | **P3, zalecane ulepszenie; zalecenie jakościowe** | Ak. 15–16 podają pojedynczy podział i najlepsze konfiguracje; rozdz. 4.4 opisuje 50 osobników i 30 generacji, bez zestawienia czasu obliczeń. | Liczby wskazują zysk w tym biegu, nie typowy zysk przy losowości ani opłacalność złożoności. | Dodać czas i sprzęt z logów, liczbę ocen fitness oraz uczciwie nazwać brak testu stabilności. Powtórzenia lub prostszy algorytm odniesienia są potrzebne tylko dla zachowanego twierdzenia o stabilnej przewadze GA. | Zakres wniosku i koszt odpowiadają raportowanym danym. |

## 8. Porównanie ze wzorcami

| Aspekt | Wzorzec i lokalizacja | Poprawiona praca i znaczenie |
|---|---|---|
| Przejście od problemu do wymagań | Wzorzec 2, s. 5–9: dwa konkretne serwisy, obserwacje z ich użycia, wymagania i diagram przypadków użycia. | PhishGuard, rozdz. 2–3 (ak. 129–219), opisuje problem i wymagania, ale obecny dokument nie prowadzi ich konsekwentnie do jednego rozdziału wyników. Poprawka dotyczy powiązania, nie identycznego spisu treści. |
| Uzasadnienie mechanizmu | Wzorzec 2, s. 19–21: porównanie Stempel/Morfologik na tych samych słowach; s. 24–35: powiązanie analizatora z architekturą i zapytaniami. | PhishGuard, rozdz. 4.4 i nowa tabela ak. 15–16, ma teraz analogicznie wspólny test bazowego modelu i GA. Zysk jest mały i powinien zostać zinterpretowany razem z kosztem. |
| Całość komponentów | Wzorzec 1, s. 14–15, pokazuje połączenia układu, telefonu, BLE i zaplecza. | PhishGuard, rozdz. 4.1 i aneks A, ma opis modułów, lecz wstawiony diagram jest nadal trudny do odczytania; nie oddziela wizualnie treningu GA od inferencji trzech warstw. |
| Wynik i ograniczenie | Wzorzec 1, s. 39–43: dziesięciu użytkowników, określone zadanie i skala, komentarz do słabszych ocen; to ocena użytkowników, nie obiektywny pomiar dokładności. | PhishGuard, ak. 22, wreszcie podaje niekorzystny wynik agregatora, ale małą próbę trzeba nazwać ilustracyjną z uwagi na pokrycie z treningiem. Badanie użytkowników jest tu opcjonalne; centralne są etykiety i błędy klasyfikacji. |
| Spójność prezentacji rezultatów | Wzorzec 2, s. 36–44: wyniki są w jednej części i odpowiadają konkretnym funkcjom, a podsumowanie oddziela wykonane funkcje od planów. | PhishGuard ma dwa rozdziały wyników i stary wniosek obok nowego wyniku. Najważniejsza poprawka to jeden końcowy opis produktu i ograniczeń, a nie dodatkowy eksperyment. |

## 9. Plan poprawek

### Konieczne przed ponowną rekomendacją tej wersji

1. **Scalić pracę (K1–K2).** Wynik: jedna karta tytułowa na początku, jeden wstęp, jeden rozdz. 5 i jedno zakończenie. Sprawdzenie: wyszukanie wszystkich twierdzeń o podziale temporalnym, przewadze zespołu, GA, czasie i agregatorze; każde ma odpowiadać końcowej tabeli oraz wskazanemu raportowi.
2. **Poprawić interpretację e-mail/SMS (K3–K4).** Badane twierdzenie: skuteczność na wariantach syntetycznych. Dane: 200 wiadomości/typ, po 20 szablonów na klasę. Procedura: opisać obecne CV jako test wariantów znanych szablonów; jeśli ma pozostać wniosek o nowych wiadomościach, wykonać podział grupowy po szablonie lub użyć niezależnych realnych wiadomości. Miary: precision, recall, F1, FN/FP; raportować liczby wiadomości, grup i błędów. Kryterium akceptacji dla praktycznego użycia pozostawić do decyzji promotora.
3. **Uczciwie oznaczyć próbę agregatora (K5).** Najmniejsza poprawka: dopisać pokrycie danych i ograniczyć wniosek do obserwacji na 50 wejściach. Jeśli ma być oszacowaniem skuteczności, zastąpić ją niezależną próbą i podać każdą zmianę decyzji, etykietę, FN/FP i flagę. Wynik negatywny jest wartościowy; nie należy go ukrywać.
4. **Doprowadzić dokument do wymogów dostarczonego standardu (K6–K9).** Wynik: przypisy dolne, uporządkowana bibliografia, czytelne obiekty, poprawne spisy, bezosobowy tekst właściwy i działające odwołania. Sprawdzenie: końcowy DOCX oraz wyrenderowany PDF, porównane ze standardem s. 2–7.

### Zalecane

5. Podać koszt GA: czas, sprzęt, liczba ocen i wybrany budżet; ograniczyć wniosek o stabilności do dowodu. Weryfikacja: raport uruchomienia, bez obowiązku kosztownego ponawiania wszystkich treningów, jeśli autor usuwa silniejszą tezę.
6. Przypisać każdej funkcji demo dostępny artefakt lub ograniczyć opis do sprawdzonej wersji. Weryfikacja: komenda uruchomienia, pliki odpowiedzi i lista aktywnych endpointów.

### Opcjonalne

Porównanie z modelem głębokim, eksperyment z Optuną, rozbudowany test obciążeniowy, badanie użytkowników, OCR i SHAP/LIME. Nie stanowią warunku pozytywnej rekomendacji po uczciwym zawężeniu wniosków.

## 10. Przykłady redakcji

| Oryginał i lokalizacja | Propozycja | Powód |
|---|---|---|
| Ak. 20: „Zapisane w modelach test_accuracy=1,0 to wynik na danych treningowych (memoryzacja)” | „Pole test_accuracy=1,0 w zapisanym modelu pochodzi z odłożonego 20% zbioru syntetycznego. Osobne pięciokrotne CV dało [wynik z raportu]. Oba wyniki dotyczą danych wygenerowanych według znanych szablonów.” | Poprawne źródło liczby i granica wniosku. |
| Stary rozdz. 5.4, ak. 484: „Zespoły siedmiu klasyfikatorów uzyskują wyraźnie lepszą skuteczność niż pojedyncze modele” | „Na wspólnym teście 50 URL najlepszy zespół osiągnął F1=0,9231, a pojedynczy MLP-GA F1=0,9583. W tym eksperymencie zespół nie uzyskał przewagi.” | Zgodność z nową tabelą. |
| Stary rozdz. 5.1, ak. 438: „Temporalny rozdział train/test” | „W przedstawionym eksperymencie URL zastosowano losowy podział stratyfikowany (random_state=42). Ocena odporności na zmianę kampanii w czasie nie była przedmiotem tego testu.” | Opisuje użyty protokół. |
| Stare podsumowanie, ak. 542: „transparentność systemu ... nie wymaga rezygnacji ze skuteczności” | „System pokazuje wyniki trzech warstw i aktywne reguły. Na badanych 50 adresach agregator uzyskał 46/50 poprawnych decyzji wobec 48/50 dla samego ML; nie wykazano wzrostu skuteczności.” | Oddziela cechę interfejsu od zmierzonej skuteczności. |
| Rozdz. 4.4, ak. 299: „Optymalizację zrealizowałem w bibliotece DEAP” | „Optymalizację zrealizowano z użyciem biblioteki DEAP. Reprezentację osobnika i ograniczenia parametrów dobrano następująco: [do uzupełnienia przez autora].” | Spełnia wymóg formy bezosobowej bez ukrywania decyzji projektowej. |

## 11. Pytania do autora i na obronę

To propozycje dotyczące tej pracy, nie oficjalna lista egzaminacyjna.

| Pytanie | Dobra odpowiedź powinna wykazać |
|---|---|
| 1. Co dzieje się podczas strojenia GA, a co podczas pojedynczej predykcji? | Przepływ danych; trzy warstwy predykcji i osobny etap strojenia. |
| 2. Dlaczego 0,7 stało się osiągalne po zmianie mianownika entropii? | Wyprowadzenie maksimum dla dwóch klas głosów i przykłady 2:1 oraz 4:3. |
| 3. Który test dał +0,0417 F1 dla MLP i czym różni się od CV-fitness? | Wspólny odłożony test, liczności, brak użycia testu do strojenia. |
| 4. Co wynika z tego, że zespół uzyskał niższy F1 niż pojedynczy MLP-GA? | Uczciwa interpretacja wyniku negatywnego i możliwe przyczyny, bez dopisywania przewagi. |
| 5. Skąd dokładnie pochodzi test_accuracy=1,0 w modelu e-mail? | Odtworzenie podziału 80/20, rozróżnienie testu syntetycznego, pełnego zbioru i CV. |
| 6. Co mierzy CV, jeśli ten sam szablon wiadomości pojawia się w treningu i teście? | Rozumienie zależnych próbek i potrzeby podziału grupowego lub niezależnego zbioru. |
| 7. Jak sprawdzono, czy 50 URL do oceny agregatora nie występowało w treningu? | Konkretna procedura deduplikacji, identyfikacja 13 nakładających się adresów. |
| 8. Czy flaga rozbieżności oznacza automatycznie, że decyzja jest błędna? | Rozróżnienie wskaźnika niezgody od trafności; interpretacja dwóch błędnych zmian. |
| 9. Dlaczego ustalono wagi 0,5/0,3/0,2 i co robi źle skalibrowany Bayes? | Wpływ wag i skali posterioru na próg 0,5; analiza fałszywie negatywnych decyzji. |
| 10. Jak mierzono p95 czasu odpowiedzi i czego ten pomiar nie obejmuje? | 50 lokalnych żądań po rozgrzaniu, brak sieci i konkurencji. |
| 11. Jaki jest koszt strojenia GA wobec uzyskanego zysku na tym teście? | Liczba ocen, czas, sprzęt i praktyczna wartość małych różnic. |
| 12. Która część demonstratora jest naprawdę dostarczona i jak odtworzyć studium przypadków? | Repozytorium, artefakty, komendy oraz uczciwe ograniczenia. |

Instrukcja przekazana wcześniej przewidywała prezentację **do 12 minut** i opcjonalny film **2–3 minuty**. W prezentacji wystarczy schemat działania, jedna porównywalna tabela, jeden przypadek zmiany decyzji przez agregator i granice dowodu. Film może pokazać interfejs, lecz nie zastępuje testu.

## 12. Granice oceny i decyzje promotora

Nie sprawdzono pełnej zgodności składu w widoku stron, ponieważ lokalny renderer nie wytworzył PDF z DOCX. Nie przeprowadzono niezależnego audytu wszystkich 43 pozycji bibliografii ani kosztownego ponownego treningu GA. Nie oceniono plików smoke-testów osobnego demonstratora, gdyż wskazany katalog nie jest obecny. Nie weryfikowano aktualności standardu bez dostępu do SUSZI. Nie badano plagiatu ani użycia AI. Obecność kodu nie oznacza tu potwierdzenia jakości całego systemu w produkcyjnym wdrożeniu.

Do decyzji promotora należy ustalenie, jaki wąski zakres skuteczności — URL, syntetyczne wiadomości czy rzeczywiste wiadomości — musi zostać wykazany dla zatwierdzonego tytułu, oraz czy formalny tytuł karty powinien odpowiadać dokładnie standardowi czy szablonowi SAKE. **Sama korekta składu nie wystarczy**, dopóki w jednym dokumencie pozostają sprzeczne wyniki i wnioski. Po ich scaleniu i ograniczeniu twierdzeń praca może być oceniona ponownie na podstawie realnie wykazanego wkładu inżynierskiego.

**Zewnętrzna weryfikacja techniczna:** nowy opis domyślnego samplera Optuny w rozdz. 4.4 odpowiada [dokumentacji Optuna 4.4.0](https://optuna.readthedocs.io/en/v4.4.0/tutorial/10_key_features/003_efficient_optimization_algorithms.html): domyślny jest TPE, a sampler oparty na procesie Gaussa jest osobną opcją. Zakres sprawdzenia ograniczono do tego twierdzenia; nie oceniano przewagi GA nad Optuną.
