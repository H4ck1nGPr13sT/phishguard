                WYŻSZA SZKOŁA ZARZĄDZANIA I BANKOWOŚCI

                                                       W KRAKOWIE


                                               Wydział Nauk Stosowanych

                                     KIERUNEK: Informatyka (Niestacjonarne)

                                       ZAKRES KSZTAŁCENIA: Bazy danych




                         PRACA DYPLOMOWA INŻYNIERSKA




                                                Łukasz Drążek




                                     Wykrywanie ataków typu phishing

                                       poprzez analizę treści wiadomości

                          z wykorzystaniem metod uczenia maszynowego




                                                            PROMOTOR:



dr hab. inż. Rafał Dreżewski




        KRAKÓW 2026








# 1. Wstęp


Phishing   pozostaje   jednym    z   najczęściej    raportowanych   incydentów   bezpieczeństwa
teleinformatycznego. Według raportów Anti-Phishing Working Group [1] oraz krajowych
zespołów reagowania na incydenty (CERT Polska [17], CSIRT KNF [26]) liczba kampanii rośnie
z roku na rok, a próbki coraz częściej wykorzystują niestandardowe domeny najwyższego
poziomu, skrócone linki i manipulację emocjonalną. Skuteczność klasycznych mechanizmów
reputacyjnych, takich jak czarne listy i filtry DNS, jest mocno ograniczona przez krótki czas
życia kampanii i dynamiczną podmianę domen.

Pomysł na temat tej pracy wziął się z obserwacji własnego otoczenia. W ostatnich latach w
polskich gospodarstwach domowych masowo pojawiają się SMS-y w stylu "twoja paczka czeka
na dopłatę 2,99 zł", e-maile rzekomo od banku z prośbą o ponowne logowanie i fałszywe
powiadomienia o nieopłaconych fakturach. Łatwo te wiadomości rozpoznać, gdy się je przeczyta
uważnie, ale w praktyce wiele osób reaguje odruchowo, w pośpiechu i w godzinach, gdy uwaga
jest słabsza. W rozmowach rodzinnych i zawodowych kilkukrotnie spotkałem się z sytuacją, w
której ktoś kliknął podejrzany link albo dopiero po fakcie zaczął zastanawiać się, czy wiadomość
była prawdziwa. Stąd pytanie, które stało za projektem: czy da się zbudować narzędzie, które
oceni taki komunikat samodzielnie, w sposób na tyle przejrzysty, by zwykły użytkownik widział,
dlaczego system się niepokoi.

Zaprojektowano i wykonano system wykrywania phishingu, w którym wynik klasyfikacji opiera się nie na jednym modelu, lecz na trzech warstwach decyzyjnych działających podczas predykcji: zespole uczenia maszynowego, systemie regułowym i klasyfikatorze bayesowskim. Algorytm genetyczny pełni rolę wcześniejszej optymalizacji modeli, a nie czwartej warstwy głosującej. Trzy warstwy predykcji łączą: uczenie maszynowe, system regułowy i podejście
probabilistycznego modelu bayesowskiego. Hipoteza pracy brzmi tak: rozbieżność wskazań
między tymi metodami sama w sobie jest sygnałem diagnostycznym. Pozwala wychwycić
próbki do ręcznej kontroli; związek flagi z częstością błędów wymaga osobnej oceny.

Praca ma część teoretyczną i inżynierską. Część teoretyczna omawia problem phishingu,
motywację projektu, przegląd istniejących rozwiązań, zakres funkcjonalności oraz wybrane
aspekty realizacji. Nacisk położyłem na uzasadnienie konkretnych decyzji algorytmicznych i
architektonicznych, bo właśnie ten poziom rozważań odróżnia pracę inżynierską od
demonstratora złożonego z gotowych klocków. Część inżynierska to kompletny system

PhishGuard. Obejmuje pipeline danych (PhishTank, UCI ML Repository, korpus Nazario),
ekstrakcję cech (URL, e-mail, SMS, miary stylometryczne i sentymentu), siedem klasyfikatorów
uczenia maszynowego, zespoły typu voting i stacking, algorytm genetyczny do optymalizacji
hiperparametrów, system regułowy oparty na szesnastu regułach YAML, klasyfikator
bayesowski oraz warstwę agregacji i REST API zbudowane na FastAPI. W końcowej fazie
dodałem też prosty frontend webowy, aby wyniki systemu można było pokazać bez korzystania
wyłącznie ze Swagger UI.

Dalsza część pracy ma układ stopniowy: od opisu problemu i przeglądu rozwiązań (rozdział 2),
przez specyfikację wymagań (rozdział 3) i architekturę z wybranymi aspektami realizacji
(rozdział 4), po wyniki, studia przypadków i ograniczenia (rozdział 5) oraz podsumowanie z
kierunkami rozwoju (rozdział 6).






# 2. Cel prac i wizja produktu



## 2.1. Charakterystyka problemu i motywacja


Phishing to forma inżynierii społecznej. Napastnik podszywa się pod zaufaną stronę lub
instytucję, by wyłudzić dane uwierzytelniające, środki finansowe albo skłonić ofiarę do
zainstalowania złośliwego oprogramowania. Powierzchnia ataku obejmuje wszystkie kanały
tekstowe (poczta e-mail, SMS, komunikatory, portale społecznościowe). Wektorem nośnym
może być odnośnik URL, tekst samej wiadomości albo załączony obraz. W ostatnich latach
atakujący chętnie łączą te kanały. Wiadomość SMS przekierowuje na stronę, na której formularz
prosi o zalogowanie do banku, a w międzyczasie ofiara dostaje pozornie potwierdzający e-mail z
fałszywej skrzynki obsługi klienta.

Systematyczne ujęcie taksonomii phishingu, jego wektorów oraz przeciwdziałania można znaleźć
w pracy przeglądowej Aleroud i Zhou [2] oraz w nowszych publikacjach na ten temat [3, 11].
Specyfikę polskiego rynku omawia raport CERT Polska [17] oraz materiały edukacyjne NASK
[27].

Dlaczego wykrywanie phishingu jest trudne? Główna przyczyna sprowadza się do tempa zmian.
Treść kampanii ewoluuje miesiąc w miesiąc, a modele wytrenowane na danych sprzed pół roku
tracą skuteczność, bo atakujący stale modyfikują szablony. Zjawisko to nosi w literaturze nazwę
concept drift i jest dla projektantów systemów obrony stałym źródłem frustracji. Drugi powód
jest dla mnie subtelniejszy. Próbki phishingowe celowo naśladują komunikaty zaufanych
instytucji, czyli banków, kurierów, portali zakupowych czy dostawców usług w chmurze. Dobry
przeciwnik ich nie odróżni po jednym przeczytaniu, a tym bardziej nie zrobi tego model
statystyczny operujący wyłącznie na słowniku. Ostatnia trudność wydaje się najpoważniejsza w
obronie codziennej. Klasyczne modele uczenia maszynowego są tak zwaną czarną skrzynką.
Zespół drzew albo sieć neuronowa zwracają liczbę między zerem a jedynką, ale nie wyjaśniają,
skąd ta liczba się wzięła. Próby zaadresowania tego problemu metodami post-hoc takimi jak
SHAP czy LIME są tematem aktywnych badań [12, 13]. W praktyce jednak analityk centrum
bezpieczeństwa potrzebuje wyjaśnienia teraz, w trakcie analizy alarmu. Bez niego nie potrafi
alarmu ani zatwierdzić, ani zignorować, bo w obu przypadkach bierze na siebie ryzyko.


Motywacja stojąca za projektem jest zatem dość prosta. Chciałem zbudować system, który łączy
dobrą skuteczność statystyczną z interpretowalnością decyzji i odpornością na zmienność danych.
Wymaga to rezygnacji z pojedynczego modelu na rzecz architektury złożonej z kilku
niezależnych warstw, gdzie każda z nich daje nie tylko własną predykcję, ale i informację, na ile
jest pewna swojej odpowiedzi. W rozdziale czwartym opisuję, jak ten zamysł został zrealizowany
technicznie, a w piątym - jak wyglądają konkretne predykcje na próbkach phishingowych i
legalnych.



## 2.2. Przegląd istniejących rozwiązań


Narzędzia do wykrywania phishingu istnieją od dwóch dekad, ale różnią się znacznie pod
względem zakresu funkcjonalnego, metody analizy oraz miejsca wdrożenia: część działa w
kliencie pocztowym, część w przeglądarce, jeszcze inne w bramie sieciowej. Dla potrzeb
porównania w pracy akademickiej można je podzielić na cztery grupy.


### 2.2.1. Mechanizmy reputacyjne


Mechanizmy reputacyjne są historycznie najstarszą warstwą ochrony przed phishingiem. Działają
w oparciu o listy znanych złośliwych domen, adresów IP i sygnatur URL. Do najpowszechniej
używanych należą Google Safe Browsing (zintegrowane z Chrome, Firefox i większością
nowoczesnych przeglądarek), Microsoft SmartScreen (Edge oraz Windows Defender),
PhishTank (społecznościowa baza zgłoszeń), Spamhaus DBL oraz OpenPhish. Lista odświeżana
jest w cyklu godzinowym lub szybciej, a zapytania klientów wykonywane są zazwyczaj przez
API z dodatkowym mechanizmem hashowania, by chronić prywatność. Skuteczność tych
mechanizmów dla próbek o ustalonej historii jest bardzo wysoka (powyżej 99 procent), ale dla
próbek pierwszego dnia (zero-day), które nie zdążyły jeszcze trafić na listę, spada do
kilkudziesięciu procent. Czas reakcji wynosi od kilku godzin do kilku dni.


### 2.2.2. Komercyjne filtry treści


Drugą grupę stanowią rozbudowane filtry treści dostarczane wraz z platformami pocztowymi i
bezpieczeństwa biznesowego. Najważniejsi gracze na tym rynku to Microsoft Defender for
Office 365 (dawniej Advanced Threat Protection), ProofPoint Email Protection, Cisco Secure
Email (dawniej IronPort), Mimecast Secure Email Gateway oraz Barracuda Email Security

Gateway. Wszystkie łączą trzy techniki: analizę reputacji domen i adresów IP, statystyczną
analizę nagłówków SMTP (SPF, DKIM, DMARC, zgodność trasy z deklaracjami) oraz analizę
treści przez kombinację reguł heurystycznych i klasyfikatorów uczenia maszynowego.
Producenci raportują wysoką skuteczność, szczególnie dla phishingu masowego, lecz
szczegółowe metody pomiaru nie są publiczne. Ogólny obraz zagrożeń przedstawiają cykliczne
raporty agencji ENISA [33] oraz ich polskie odpowiedniki [28]. Wadą rozwiązań komercyjnych
dla badań akademickich jest pełne zamknięcie szczegółów technicznych. Architektura, dobór
cech, modele i progi decyzyjne są tajemnicą handlową, a publikacje producentów zawierają
jedynie ogólne deklaracje.


### 2.2.3. Wtyczki przeglądarek i specjalistyczne dodatki


Trzecią grupę tworzą wtyczki przeglądarek i specjalistyczne narzędzia działające po stronie
klienta. Należą do nich między innymi Netcraft Anti-Phishing, Bitdefender TrafficLight, Avast
Online Security, Norton Safe Web oraz Web of Trust. Wykorzystują głównie listy reputacyjne i
lekkie modele heurystyczne, dla zachowania niskiego narzutu wydajnościowego. W praktyce ich
rola jest pomocnicza, ponieważ większość użytkowników kieruje się ostrzeżeniami z głównej
przeglądarki lub klienta pocztowego.


### 2.2.4. Akademickie projekty open-source


Czwartą i najbardziej różnorodną grupę stanowią publikacje naukowe oraz projekty open-source.
Wśród tych ostatnich na uwagę zasługują między innymi PhishStorm [42], URLNet [43] z
architekturą głębokiej sieci konwolucyjnej, prace Sahingoza i in. [3] dla klasyfikatorów na
cechach URL, PhishTank API client oraz różne implementacje na GitHubie oparte na lasach
losowych i XGBoost. Systematyczne ujęcie cech URL znaleźć można w klasycznej pracy
Mohammada i in. [4], a obraz dorobku ostatniej dekady w przeglądzie Pourrezy i in. [11].
Większość projektów akademickich operuje na jednym z trzech publicznych zbiorów: UCI
Phishing Websites Dataset (11055 próbek, 30 cech, klasyfikacja binarna), PhishTank API (próbki
phishingu zgłoszone społecznościowo) oraz korpus Nazario (archiwum próbek phishingowych
zebrane przez Jose Nazario od 2005 roku). Najczęściej spotykane podejścia opierają się na lasach
losowych, gradient boostingu, maszynach wektorów nośnych, regresji logistycznej oraz sieciach




MLP. Część prac używa prostych zespołów (głównie soft voting) lub wprowadza dedykowane
reprezentacje sieciowe URL, na przykład osadzenia znakowe wektorowane przez CNN.


### 2.2.5. Tabela porównawcza


Tabela poniżej zestawia wybrane cechy charakterystyczne porównanych podejść, z
uwzględnieniem trzech wymiarów istotnych dla projektu PhishGuard: użycia uczenia
maszynowego, transparentności decyzji oraz dostępności do badań.

Rozwiązanie           Typ                   ML            Transparentność         Dostęp

Google         Safe reputacyjne              nie         niska (czarna lista)      API
Browsing                                                                         publiczne

Microsoft             reputacyjne        częściowo                 niska        wbudowane
SmartScreen

PhishTank             reputacyjne            nie        wysoka (głosowanie      otwarte API
                      (społeczność)                         społeczności)

Defender        for filtr treści             tak            niska (czarna          tylko
O365                                                          skrzynka)         abonament

ProofPoint Email filtr treści                tak                   niska        komercyjne
Protection

Cisco        Secure filtr treści             tak                   niska        komercyjne
Email

Mimecast SEG          filtr treści           tak                   niska        komercyjne

URLNet                akademickie        tak (CNN)       niska (głęboka sieć)   kod GitHub
(publikacja)

PhishStorm            akademickie         tak (RF,             średnia          brak kodu
(publikacja)                               SVM)

PhishGuard      (ta akademickie        tak (7 klasyf.     wysoka (reguły,        GitHub
praca)                                     + GA)             agregator)





Tabela 1. Porównanie wybranych rozwiązań do wykrywania phishingu pod kątem typu, użycia
uczenia maszynowego, transparentności decyzji oraz dostępności do badań.


### 2.2.6. Luka, którą wypełnia praca


W każdej z czterech grup brakuje czegoś istotnego dla pracy akademickiej. Mechanizmy
reputacyjne są potrzebne, ale działają z opóźnieniem i łatwo je ominąć przez świeżą domenę.
Komercyjne filtry treści są skuteczne, lecz zamknięte, więc nie można odtworzyć ich wyników
ani porównać własnego rozwiązania w sposób kontrolowany. Większość akademickich
projektów open-source koncentruje się natomiast na jednym klasyfikatorze albo jednym zbiorze
danych i nie pokazuje obok siebie wyniku różnych metod analizy dla tej samej próbki.

Stąd kierunek projektu PhishGuard: zestawić w jednym systemie siedem klasyfikatorów ML,
optymalizację hiperparametrów przez algorytm genetyczny, system regułowy oparty na szesnastu
zważonych regułach YAML, klasyfikator probabilistyczny oraz agregator wykrywający
rozbieżności między metodami. Kod jest dostępny w repozytorium, a kolejne eksperymenty
można odtworzyć na podstawie zapisanych modeli i metadanych.



## 2.3. Wizja systemu PhishGuard


Projektowany system PhishGuard ma być kompletnym demonstratorem analitycznym
wykrywającym phishing w trzech rodzajach treści: adresach URL, wiadomościach e-mail (w tym
plikach .eml) oraz wiadomościach SMS. Centralna idea systemu jest następująca:

       Decyzja klasyfikacyjna nie jest wynikiem jednego modelu, lecz syntezą wyników kilku
       niezależnych metod. Rozbieżności między nimi są sygnałem diagnostycznym, a system
       samodzielnie identyfikuje przypadki graniczne i przekazuje je do dalszej analizy.

Kluczowymi cechami wizji są:

   •     Modularność - każdy z czterech komponentów (ML, reguły, Bayes, GA) jest
         zaimplementowany w osobnym module i może być rozwijany niezależnie.
   •     Interpretowalność - system zwraca nie tylko prawdopodobieństwo phishingu, lecz
         również listę aktywnych reguł, wkład każdej z trzech warstw decyzyjnych oraz tekstowe
         wyjaśnienie decyzji.


   •   Stabilność wyników - algorytm genetyczny optymalizuje hiperparametry klasyfikatorów
       minimalizując ryzyko przypadkowych konfiguracji o słabej generalizacji.
   •   Replikowalność - wszystkie modele są zapisywane w plikach .joblib i wersjonowane
       wraz z metadanymi treningu; pełne przebiegi optymalizacji genetycznej są rejestrowane
       w MLflow w pełnym repozytorium projektu.
   •   Łatwa rozszerzalność - architektura API pozwala dodać kolejne typy wejścia (obrazy,
       OCR, dashboard wizualizacyjny) bez naruszania warstwy modeli.



## 2.4. Studium wykonalności i analiza zagrożeń



### 2.4.1. Wykonalność techniczna


Pod względem technicznym projekt nie wymaga niczego, czego nie dałoby się znaleźć w
standardowych pakietach Pythona. Klasyfikatory ML pochodzą z scikit-learn, gradient
boosting z xgboost, optymalizator ewolucyjny z DEAP. REST API stoi na FastAPI, walidacja
schematów na Pydantic, przetwarzanie języka naturalnego na spaCy, parsowanie plików .eml na
eml-parser. Wszystkie te biblioteki są aktywnie utrzymywane i pokrywają zakres funkcjonalny

projektu bez konieczności pisania własnych implementacji algorytmów.


### 2.4.2. Wykonalność czasowa


Czas potrzebny na realizację projektu szacowano dzieląc go na fazy. Wstępna faza zbierania i
czyszczenia danych zajmuje przy publicznych zbiorach około tygodnia (pobranie, walidacja,
łączenie, balansowanie). Implementacja siedmiu klasyfikatorów z scikit-learn zajmuje kolejne
dwa, trzy dni, ze względu na gotowy interfejs biblioteki. Trening klasyfikatorów bazowych na
typowym sprzęcie konsumenckim trwa od kilkudziesięciu sekund (Naive Bayes, regresja
logistyczna) do kilku minut (SVM z jądrem RBF, MLP). Najdroższy czasowo jest etap
optymalizacji genetycznej. Dla siedmiu klasyfikatorów, populacji pięćdziesięciu osobników i
trzydziestu generacji, przy pięciokrotnej walidacji krzyżowej dla każdego osobnika, łączna liczba
treningów wynosi około 10500 (po uwzględnieniu elitarnego przenoszenia liczba jest nieco
niższa). Na maszynie z procesorem klasy desktop ten etap zajmuje od kilkunastu do
kilkudziesięciu godzin. System regułowy, klasyfikator bayesowski i agregator są tanie



obliczeniowo. Frontend można dodać w ciągu jednego dnia. Łącznie projekt mieści się w ramach
pracy semestralnej pojedynczej osoby.


### 2.4.3. Analiza zagrożeń


Zagrożenia projektowe można podzielić na trzy kategorie. Pierwszą stanowią zagrożenia
dotyczące danych. Publiczne zbiory phishingowe (PhishTank [15], UCI [14], Nazario [16]) są
ograniczone wielkością i pochodzeniem geograficznym. Większość próbek pochodzi ze Stanów
Zjednoczonych i Europy Zachodniej, a znaczna część jest anglojęzyczna. Phishing na rynku
polskim ma swoje specyficzne wzorce, na przykład podszywanie się pod firmy kurierskie, Pocztę
Polską albo instytucje publiczne. Nie są one dobrze reprezentowane w globalnych zbiorach, co
może obniżać skuteczność systemu na próbkach polskich. Raporty instytucji publicznych
dotyczące cyberbezpieczeństwa jednostek administracji wskazują, że świadomość i procedury
bezpieczeństwa wciąż są nierówne [29]. Druga kategoria to concept drift. Phishing ewoluuje w
czasie i model wytrenowany na próbkach sprzed roku może działać gorzej na obecnych
kampaniach. Rozwiązaniem jest regularny retrening i monitorowanie metryk. Trzecia kategoria
to ataki adwersaryjne. Atakujący znający strukturę systemu może projektować adresy URL
omijające konkretne reguły lub wpadające w punkty niskiej pewności klasyfikatorów. Ochroną
jest połączenie wielu metod analizy oraz okresowy retrening z dodawaniem przykładów
adwersaryjnych.


### 2.4.4. Wykonalność ekonomiczna


Projekt nie wymaga inwestycji w komercyjne licencje (wszystkie biblioteki na licencjach BSD,
MIT, Apache 2.0) ani specjalistycznego sprzętu (cały trening i wnioskowanie odbywa się na
typowym procesorze konsumenckim, bez konieczności GPU). Koszt operacyjny ogranicza się do
prądu i ewentualnie kosztu pobierania danych z PhishTank dla większych limitów (klucz API
publiczny ma ograniczenie pobrań dziennych). Dla wdrożenia produkcyjnego doszedłby koszt
serwera, ale dla pracy akademickiej i demonstracji koszt jest pomijalny.


### 2.4.5. Bilans


Projekt można zrealizować w ramach pracy jednej osoby, jednego semestru i bez inwestycji
finansowej. Główne ryzyko techniczne dotyczy concept drift oraz odporności na ataki


adwersaryjne, a oba ograniczane są przez architekturę łączącą kilka niezależnych metod analizy.
Zbiory danych wykorzystywane w pracy (PhishTank, UCI ML Phishing Websites, Nazario
corpus) są publicznie dostępne, a trening klasyfikatora bazowego trwa od sekund do minut na
typowym komputerze. Tylko optymalizacja algorytmem genetycznym jest wyraźnie droższa - tu
czas zależy od klasyfikatora i wielkości populacji.

Główne zidentyfikowane zagrożenia projektu:

Ryzyko                        Wpływ                      Środki zaradcze

Brak          temporalnego Optymistyczne                 Dedykowany        moduł    temporal_split.py,

rozdziału             danych metryki, ryzyko data walidacja kolejności znaczników czasu
train/test                    leakage

Niezbalansowanie klas w Bias            modelu     w imbalanced-learn (SMOTE, SMOTETomek)
zbiorze treningowym           stronę             klasy +     parametr      class_weight='balanced'     w
                              większościowej             klasyfikatorach

Brak interpretowalności Trudność                         Równoległy system regułowy zwracający listę
klasyfikatorów          typu uzasadnienia decyzji        dopasowanych reguł
black-box

Concept drift                 Spadek skuteczności Trening          na      danych   z     temporal_split,

                              po wdrożeniu               możliwość           retreningu         skryptem
                                                         retrain_with_urls.py

Krótki       termin    pracy Ryzyko                      Plan wykonany w 6 z 10 zaplanowanych faz;
inżynierskiej                 niedokończenia             pozostałe fazy (OCR, dashboard, SHAP,
                                                         dokumentacja) są oznaczone jako dalsze prace

Po przeanalizowaniu tych ryzyk uznałem, że cele projektu są osiągalne w założonych ramach
czasowych i sprzętowych, jeśli świadomie ograniczę zakres: OCR, dashboard eksplanacyjny oraz
integracja SHAP/LIME zostały odłożone do dalszego rozwoju, na rzecz dokończenia
wcześniejszych faz.






# 3. Zakres funkcjonalności



## 3.1. Aktorzy i konteksty użycia


System przewiduje trzech głównych aktorów:

   •   Użytkownik końcowy (UE) - osoba odpowiedzialna za analizę pojedynczych
       wiadomości lub adresów URL. Korzysta z API REST przez interfejs Swagger UI, klienta
       HTTP (Postman, curl) albo dedykowanego frontendu webowego dostępnego pod /app.
   •   Analityk      bezpieczeństwa    (AB)    -    specjalista,   który   wykorzystuje   endpoint
       /predict/multi-paradigm do analizy próbek o niejasnej charakterystyce; szczegółowo

       studiuje rozbieżności między warstwami oraz listę aktywnych reguł.
   •   Administrator systemu (AS) - osoba odpowiedzialna za instalację, retrening modeli,
       zarządzanie      rejestrem     modeli       (src/optimization/model_registry.py )      oraz
       monitorowanie eksperymentów w MLflow.

Konteksty użycia obejmują:

   •   Single sample inference - klasyfikacja pojedynczej próbki w czasie odpowiedzi poniżej
       500 ms.
   •   Batch analysis - analiza wielu próbek (planowane w Fazie 8).
   •   Retrening i optymalizacja - okresowe odświeżanie modeli na nowszych danych poprzez
       skrypty pomocnicze.
   •   Monitorowanie eksperymentów - przegląd historii optymalizacji w MLflow.



## 3.2. Wymagania funkcjonalne


Wymagania funkcjonalne projektu zostały zdefiniowane na podstawie założeń pracy oraz analizy
literatury dotyczącej wykrywania phishingu. W repozytorium projektu znajduje się ich pełna lista
(plik .planning/REQUIREMENTS.md) wraz z mapowaniem na fazy implementacji. Poniżej
przedstawiono syntezę najważniejszych pozycji w obszarze ośmiu grup tematycznych.




Wejścia (INPUT)

  •   INPUT-01: System przyjmuje URL przez formularz/endpoint REST.
  •   INPUT-02: System przyjmuje surowy tekst wiadomości (e-mail, SMS, czat).
  •   INPUT-03: System przyjmuje plik wiadomości e-mail w formacie .eml.
  •   INPUT-04..07: Obsługa obrazów, OCR oraz batch CSV - przewidziane w Fazach 7-8
      jako kierunki dalszego rozwoju.

Ekstrakcja cech (FEAT)

  •   FEAT-01..04: Cechy długościowe, leksykalne, składniowe, stylometryczne.
  •   FEAT-05: Cechy URL (długość, obecność IP, skrócone linki, podejrzane TLD).
  •   FEAT-06: Cechy sentymentu (pilność, presja czasowa, manipulacja emocjonalna).
  •   FEAT-07: Cechy nagłówków e-mail (SPF, DKIM, domena nadawcy).
  •   FEAT-08: Normalizacja i skalowanie cech przed klasyfikacją.

Klasyfikatory ML (ML)

  •   ML-01..07: Siedem klasyfikatorów - Random Forest, Support Vector Machine, MLP,
      Gradient Boosting (XGBoost), Logistic Regression, Naive Bayes, Decision Tree.
  •   ML-08: Każdy klasyfikator zwraca prawdopodobieństwo przynależności do klasy
      phishing.

Zespoły (ENS)

  •   ENS-01: Soft voting (uśrednienie prawdopodobieństw).
  •   ENS-02: Hard voting (głosowanie większościowe).
  •   ENS-03: Stacking z meta-modelem (Logistic Regression, 5-krotne CV chroniące przed
      wyciekiem danych).
  •   ENS-04: Porównanie skuteczności metod agregacji.
  •   ENS-05: Wykrywanie i raportowanie rozbieżności pomiędzy klasyfikatorami (entropia
      rozkładu predykcji).





Algorytm genetyczny (GA)

  •   GA-01: Optymalizacja hiperparametrów wszystkich siedmiu klasyfikatorów.
  •   GA-02: Selekcja cech (feature selection) za pomocą GA.
  •   GA-03: Optymalizacja wag w zespole z ważonym głosowaniem.
  •   GA-04: Selekcja turniejowa, krzyżowanie, mutacja kontrolowana.
  •   GA-05: F1-score w 5-krotnej walidacji krzyżowej jako funkcja celu.
  •   GA-06: Logowanie historii ewolucji w MLflow.

System regułowy (RULE)

  •   RULE-01..05: 16 reguł zdefiniowanych w pliku YAML, kategorie: struktura URL, słowa
      kluczowe, struktura tekstu, domena.
  •   RULE-06: Agregacja aktywnych reguł do zważonego wyniku końcowego.
  •   RULE-07: Zwracanie listy aktywnych reguł z uzasadnieniem (dopasowane wartości cech
      lub słów).

System probabilistyczny (PROB)

  •   PROB-01..04: Klasyfikator bayesowski (Gaussian Naive Bayes) opakowany w potok
      scikit-learn ze standardowym skalerem, zwracający posterior dla obu klas oraz priory.

Agregacja (AGG)

  •   AGG-01..04: Połączenie wyników ML, reguł i Bayesa z konfigurowalnymi wagami,
      wykrywanie rozbieżności między warstwami, decyzja końcowa z poziomem pewności.



## 3.3. Wymagania niefunkcjonalne


  •   Wydajność: czas odpowiedzi pojedynczego endpointu poniżej 500 ms (osiągnięte dzięki
      załadowaniu modeli przy starcie serwera, w mechanizmie lifespan FastAPI).
  •   Skalowalność wewnętrzna: ASGI (Uvicorn + FastAPI), automatyczna obsługa
      synchronicznych funkcji w threadpool.





   •   Bezpieczeństwo: limit rozmiaru pliku .eml (5 MB), walidacja typu MIME, walidacja
       Pydantic dla wszystkich żądań.
   •   Konfigurowalność: warstwa src/config/settings.py (zmienne DATA_DIR, CACHE_DIR,
       PHISHTANK_API_KEY) z domyślnymi wartościami w .env.example.

   •   Testowalność: zestaw testów pytest obejmujący najważniejsze moduły jednostkowo i
       integracyjnie.
   •   Replikowalność: wszystkie modele w repozytorium (models/), eksperymenty GA w
       MLflow, kontrolowane ziarna losowe (random_state=42).



## 3.4. Komponenty współpracujące


System integruje się z następującymi komponentami zewnętrznymi:

   •   PhishTank        -   pobieranie       świeżych       próbek    phishingowych       URL    (moduł
       src/data/downloaders/phishtank.py).

   •   UCI     ML       Repository       -    dataset      Phishing   Websites     Data    Set   (moduł
       src/data/downloaders/uci_ml.py).

   •   Nazario      phishing         corpus       -        korpus     wiadomości      e-mail     (moduł
       src/data/downloaders/nazario.py).

   •   MLflow - lokalna instancja serwera śledzenia eksperymentów GA.
   •   spaCy + model en_core_web_sm - tokenizacja, lematyzacja i NER dla cech tekstowych w
       wiadomościach e-mail i SMS.






# 4. Wybrane aspekty realizacji



## 4.1. Architektura systemu


PhishGuard zaprojektowano w architekturze trójwarstwowej z modularnym podziałem warstwy
logiki:


Rysunek 1. Architektura logiczna systemu PhishGuard.

Warstwa prezentacji obejmuje dwa elementy: automatycznie generowane Swagger UI dostępne
pod /docs oraz dedykowany frontend webowy /app opisany w rozdziale 4.9. Warstwa logiki
została podzielona na cztery moduły funkcjonalne:


      •    Ekstrakcja cech (src/features/) - osobne moduły dla URL (url_features.py), e-mail
           (email_features.py), SMS (sms_features.py) oraz uniwersalnych cech tekstowych
           (text_features.py); jednolity orkiestrator extractors.py rozpoznaje typ wejścia.
      •    Modele i zespoły (src/models/) - definicje klasyfikatorów (classifiers.py), trening
           (train.py, train_ensemble.py), zespoły (ensemble.py), wykrywanie rozbieżności
           (disagreement.py), predykcja i ewaluacja (predict.py, evaluate.py).
      •    Optymalizacja       (src/optimization/)      -   definicje       przestrzeni     przeszukiwań
           (search_spaces.py), funkcja celu (fitness.py), optymalizator GA (ga_optimizer.py),
           zapis modeli i rejestr aktywnych modeli (model_registry.py), integracja MLflow
           (mlflow_tracker.py).
      •    Warstwy alternatywne (src/paradigms/) - silnik regułowy z plikiem YAML (rules/),
           klasyfikator    bayesowski   (bayesian/),    agregator     z    wykrywaniem      rozbieżności
           (aggregation/).

Warstwa danych obejmuje pliki modeli .joblib, katalog data/ (surowe i przetworzone zbiory),
katalog cache/ (zapisane macierze cech), katalog mlruns/ (eksperymenty MLflow) oraz plik
YAML z regułami eksperckimi. Granica między warstwami jest egzekwowana - moduły logiki
nie       operują   na    ścieżkach   plików   bezpośrednio,   lecz       przez   warstwę    konfiguracji
(src/config/settings.py).



## 4.2. Pipeline danych i ekstrakcja cech


Pipeline danych (src/data/pipeline.py) realizuje sekwencję czterech kroków:

      1. Pobieranie - moduły downloaders/ pobierają zbiory z PhishTank [15], UCI ML
           Repository [14] oraz korpusu Nazario [16]. Dostęp do PhishTank jest opcjonalny i
           wymaga klucza API (PHISHTANK_API_KEY); pozostałe źródła są publiczne. Klasyfikacja
           typowych ataków phishingowych wobec klientów polskich banków opisana jest w
           komunikatach Departamentu Cyberbezpieczeństwa KNF [30] oraz w analizach Związku
           Banków Polskich [31].
      2. Walidacja - pakiet validators/ (schemat pandera) odrzuca rekordy niepełne, niespójne
           lub zduplikowane.




# 3. Łączenie - merger.py ujednolica formaty i etykiety.

   4. Rozdział temporalny i balansowanie - temporal_split.py zapewnia, że wszystkie
        próbki treningowe pochodzą sprzed daty granicznej, a wszystkie testowe - po niej;
        balancer.py             stosuje konfigurowalne strategie balansowania, m.in. SMOTE [8],
        SMOTETomek (z biblioteki imbalanced-learn [24]) oraz parametr class_weight.

W efekcie powstają wektory cech zapisane w katalogu cache, gotowe do wielokrotnego użycia w
treningu.

Cechy URL

Moduł src/features/url_features.py ekstrahuje 30 cech URL podzielonych na cztery kategorie:

Kategoria           Cechy                                                                                                                Liczba

Długościowe url_length,                      domain_length,                path_length,                 hostname_length,                 7
                    subdomain_length, tld_length, query_length

Znakowe             dot_count,               hyphen_count,                underscore_count,                 slash_count,                 10
                    question_count, equal_count, at_count, ampersand_count, digit_count,
                    special_char_count

Binarne             has_https, has_ip, has_port, has_subdomain, has_query, has_fragment,                                                 8
                    is_valid, has_suspicious_tld

Strukturalne        path_depth,             subdomain_count,              param_count,          entropy         (Shannon), 5
                    digit_ratio


Tabela 1. Grupy cech URL ekstrahowanych przez PhishGuard.

Entropia Shannona obliczana jest dla całej dziedziny URL i jest skutecznym detektorem
zaciemniania adresu losowymi ciągami znaków (typowymi dla automatycznie generowanych
adresów phishingowych):




    probs       =   [count      /   length          for    count        in   counts.values()]
    return -sum(p * math.log2(p) for p in probs if p > 0)

Listing    1.       Implementacja       entropii      Shannona         dla   ciągu       znaków   URL
(src/features/url_features.py).

Cechy e-mail i SMS

Dla e-maili (moduł src/features/email_features.py) ekstrahowane są cechy nagłówków SMTP
(SPF, DKIM, sender domain), cechy struktury MIME (liczba załączników, liczba osadzonych
obrazów, obecność wieloczęściowego ciała), liczba i charakter linków (skrócone, IP, podejrzane
TLD) oraz cechy z analizy tekstu. Dla SMS w module src/features/sms_features.py zestaw
jest węższy: długość wiadomości, częstość znaków specjalnych, cechy URL znalezionych w
treści oraz cechy NLP z modułu tekstowego. SMS nie ma nagłówków SMTP, więc strukturalna
część odpada.

Cechy tekstowe

Moduł src/features/text_features.py używa biblioteki spaCy (Honnibal i in. [9], model
en_core_web_sm)       oraz   textstat     do       obliczania   cech     leksykalnych,    składniowych,
stylometrycznych oraz heurystyk sentymentu (np. liczba słów wyrażających pilność: urgent,
immediately, now; liczba zwrotów imperatywnych; ocena czytelności tekstu - Flesch Reading
Ease).

Łącznie modele wyspecjalizowane dla e-mail wykorzystują 65 cech, a dla SMS - 70 cech
(informacje o liczbie cech są zapisywane wraz z modelami w plikach joblib i logowane przy
starcie API).



## 4.3. Warstwa uczenia maszynowego


Do projektu wybrano siedem klasyfikatorów z różnych rodzin algorytmów uczenia
nadzorowanego. Każdy z nich przyjmuje inne założenia o rozkładzie danych i inaczej reaguje na
zależności między cechami. To nie jest przypadek - różnorodność modeli uzasadnia sprawdzenie zespołu; na przeprowadzonym teście zespół nie uzyskał przewagi nad najlepszym modelem pojedynczym, co dobrze tłumaczy klasyczna analiza bias-
variance decomposition.


Implementacja siedmiu klasyfikatorów znajduje się w pliku src/models/classifiers.py. Każdy
model siedzi w potoku scikit-learn (Pedregosa i in. [5], klasa Pipeline) ze StandardScaler przed
właściwym estymatorem. Po co skalowanie? Dla SVM i MLP jest po prostu niezbędne - oba
modele liczą odległości albo gradienty wrażliwe na skalę. Klasyfikator bayesowski z rozkładem
Gaussa też daje lepsze wyniki przy ustandaryzowanych danych, bo założenie o gaussowskim
rozkładzie warunkowym łatwiej spełnić, gdy cechy mają porównywalny zakres. Modelom
drzewiastym - RF, DT, XGBoost - skalowanie nie jest potrzebne, ale jednolity potok ułatwia
trening, ewaluację i serializację.

Trening realizowany jest przez moduł src/models/train.py. Wszystkie modele zapisywane są
jako pliki .joblib z opcjami compress=3, protocol=5. Kompresja redukuje rozmiar plików o
około 60 procent, a piąty protokół pickle przyspiesza deserializację dużych macierzy numpy i
zachowuje zgodność z Pythonem 3.8 i nowszymi.


### 4.3.1. Random Forest


Las losowy jest zespołem drzew decyzyjnych, w którym każde drzewo trenowane jest na próbie
bootstrapowej zbioru treningowego oraz na losowym podzbiorze cech [20]. Ostateczna decyzja
powstaje przez głosowanie większościowe (klasyfikacja) lub uśrednienie (regresja). Idea
wprowadzenia podwójnej losowości (próbki i cechy) wynika z chęci dekorelowania
pojedynczych drzew. Pojedyncze drzewo decyzyjne, jeśli dopuścić mu pełną głębokość, niemal
idealnie dopasowuje się do danych treningowych i wykazuje bardzo wysoką wariancję predykcji.
Uśrednienie odpowiedzi wielu zdekorelowanych drzew obniża wariancję bez zwiększania
obciążenia, co jest formalnym wyjaśnieniem skuteczności tego algorytmu w problemach
klasyfikacji binarnej.

Random Forest dobrze radzi sobie z mieszanymi typami cech (długości, zliczenia, wskaźniki
binarne, miary informacyjne), które występują w opisie URL. W praktyce sprawdzono to na
własnym zbiorze cech: nawet kiedy do macierzy trafiały zmienne tak różne jak url_length
(rzędu setek) i has_https (zero-jedynkowe), las losowy nie wymagał skalowania i dawał stabilne
wyniki przy domyślnych ustawieniach. Jest też mało wrażliwy na cechy nieinformacyjne, bo przy
losowym wyborze podzbioru cech węzła nieistotne zmienne rzadko trafiają do podziału. W
projekcie zastosowałem implementację sklearn.ensemble.RandomForestClassifier z opcją



oob_score=True.      Out-of-bag score pozwala oszacować błąd generalizacji bez wydzielania
osobnego zbioru walidacyjnego: każde drzewo widzi w treningu średnio 63,2 procenta próbek (1
minus 1 podzielone przez liczbę Eulera), a pozostałe próbki stają się zbiorem walidacyjnym dla
tego drzewa.


### 4.3.2. Support Vector Machine


Maszyna wektorów nośnych szuka hiperpłaszczyzny separującej klasy z maksymalnym
marginesem [21]. W oryginalnej formie SVM operuje na danych liniowo separowalnych, ale
technika kernel trick pozwala na operacje w przestrzeni cech o bardzo wysokiej wymiarowości
bez jawnego obliczania transformacji. Najczęściej stosowane jądra to liniowe, wielomianowe
oraz radialne (RBF). Jądro RBF, oparte na funkcji gaussowskiej dwóch punktów, jest domyślnym
wyborem dla danych o nieliniowych granicach decyzyjnych i tak też zostało dobrane w projekcie.
Parametr gamma kontroluje szerokość gaussowskiego jądra, a parametr C wagę kary za źle
sklasyfikowane próbki w sformułowaniu z marginesem miękkim.

Dla wykrywania phishingu SVM ma jedną istotną zaletę i jedną wadę. Zaletą jest odporność na
cechy nieinformacyjne, ponieważ tylko wektory nośne (próbki leżące na lub w pobliżu granicy
decyzyjnej) wpływają na model. Wadą jest pamięciożerność i czas treningu rosnące co najmniej
kwadratowo z liczbą próbek, co czyni SVM nieoptymalnym wyborem dla bardzo dużych
zbiorów. W zestawach o wielkości kilkunastu tysięcy próbek, charakterystycznych dla zbiorów
phishingowych, ograniczenie to nie jest jednak praktycznie istotne. Ustawienie probability=True
powoduje, że klasa SVC po treningu wykonuje pięciokrotną walidację krzyżową w celu
skalibrowania funkcji predict_proba, co jest niezbędne dla soft voting w zespole.


### 4.3.3. Multi-Layer Perceptron


Wielowarstwowy perceptron należy do rodziny sztucznych sieci neuronowych. Tworzą go
warstwa wejściowa, jedna lub więcej warstw ukrytych oraz warstwa wyjściowa. Każdy neuron
oblicza ważoną sumę wejść, dodaje przesunięcie (bias) i przekazuje wynik przez nieliniową
funkcję aktywacji [35]. Uczenie odbywa się metodą propagacji wstecznej błędu z użyciem reguły
łańcuchowej    dla     gradientu   funkcji   straty.    W   projekcie   zastosowano   implementację
sklearn.neural_network.MLPClassifier         z aktywacją ReLU, optymalizatorem Adam oraz
binarną entropią krzyżową jako funkcją straty.


W problemie wykrywania phishingu pojedyncza warstwa ukryta z około pięćdziesięcioma
neuronami okazała się rozwiązaniem wystarczającym, co jest zgodne z twierdzeniem o
uniwersalnej aproksymacji [36]. Twierdzenie to mówi, że sieć z jedną dostatecznie szeroką
warstwą ukrytą i nieliniową aktywacją może przybliżyć dowolną funkcję ciągłą z dowolną
dokładnością. Zwiększanie liczby warstw lub neuronów ponad pewien próg przestaje poprawiać
jakość klasyfikacji na zbiorze testowym, a zwiększa ryzyko przeuczenia. Algorytm genetyczny
opisany w rozdziale 4.4 dobiera optymalną wielkość warstwy ukrytej i współczynnik
regularyzacji alpha.


### 4.3.4. Gradient Boosting (XGBoost)


Gradient boosting buduje zespół drzew sekwencyjnie. Każde kolejne drzewo uczy się
przewidywać błąd resztkowy poprzedniego zespołu, a wkład każdego nowego drzewa
kontrolowany jest przez współczynnik uczenia [19]. Implementacja XGBoost dodaje dwie istotne
ulepszenia. Pierwsze to przybliżenie funkcji celu rozwinięciem Taylora do drugiego rzędu, co
przyspiesza zbieżność. Drugie to wbudowana regularyzacja przez kary za liczbę liści i normę L1
oraz L2 wag liści, co ogranicza przeuczenie [6].

W zadaniach klasyfikacji binarnej z dziesiątkami cech XGBoost jest jednym z najczęściej
wybieranych algorytmów. Powodów jest kilka. Drzewa naturalnie obsługują interakcje między
cechami i niemonotoniczne zależności (na przykład długi URL bez słów kluczowych ma inne
znaczenie niż długi URL z wieloma słowami pilności). Regularyzacja chroni przed przeuczeniem,
co jest istotne przy małych zbiorach treningowych. Wreszcie implementacja jest wyjątkowo
zoptymalizowana, co pozwala na trenowanie modeli z setkami drzew w czasie porównywalnym z
lasami losowymi. Wadą jest większa liczba hiperparametrów (w projekcie optymalizowano
dziewięć z nich), co czyni XGBoost trudnym do dostrojenia bez automatycznej procedury, takiej
jak algorytm genetyczny.


### 4.3.5. Logistic Regression


Regresja logistyczna jest modelem liniowym przewidującym logarytm szansy klasy pozytywnej
jako kombinację liniową cech wejściowych [37]. Pomimo nazwy, regresja logistyczna jest
klasyfikatorem, a nie modelem regresji. Funkcja sigmoidalna przekształca wynik liniowy na



prawdopodobieństwo w przedziale od zera do jednego, a podział klas następuje przy progu 0,5
lub innym dobranym dla potrzeb danego zastosowania.

Mimo prostoty formalnej regresja logistyczna jest częstym wyborem w problemach wykrywania
phishingu i w wielu badaniach osiąga wyniki porównywalne lub nieznacznie gorsze niż lasy
losowe i XGBoost. To zresztą zaskoczyło mnie najbardziej w wynikach tego projektu: po
dobraniu parametru regularyzacji C przez algorytm genetyczny regresja logistyczna okazała się
klasyfikatorem o najwyższym CV-fitness podczas strojenia (0,9749); na odłożonym teście najwyższy F1 osiągnął MLP-GA (0,9583), wyprzedzając las losowy (0,9705) i
XGBoost (0,9623). Wartość C znaleziona przez GA wynosi około 7,97 - to relatywnie słaba
regularyzacja. Słaba regularyzacja jest tu uzasadniona, bo zbiór cech jest niskowymiarowy (30
cech URL), więc ryzyko przeuczenia modelu liniowego jest niskie. Drugą zaletą regresji
logistycznej jest pełna interpretowalność: każda cecha ma znany współczynnik, a logarytm
szansy klasy jest sumą wpływów cech, więc decyzję modelu da się wytłumaczyć słownie.


### 4.3.6. Gaussian Naive Bayes


Naiwny klasyfikator Bayesa stosuje twierdzenie Bayesa do obliczenia prawdopodobieństwa klasy
pod warunkiem cech. Przyjmuje przy tym naiwne założenie o warunkowej niezależności cech
wewnątrz każdej klasy [38]. Wariant gaussowski dodaje jeszcze jedno założenie: każda cecha
ciągła ma wewnątrz klasy rozkład normalny o nieznanej średniej i wariancji, które estymowane
są ze zbioru treningowego.

Założenie o niezależności cech jest oczywiście naruszone w praktyce. Długość URL koreluje
silnie z liczbą znaków specjalnych, liczba kropek z liczbą subdomen, a obecność słowa
kluczowego verify współwystępuje z obecnością słowa account. Mimo tego klasyfikator naiwny
często daje zaskakująco dobre wyniki. Powodem jest fakt, że błędne estymacje wartości
bezwzględnych prawdopodobieństw redukują się przy porównaniu prawdopodobieństw klas, jeśli
błędy korelacji są symetryczne dla obu klas [39]. Dla phishingu znaczenie tego klasyfikatora jest
dwojakie. Stanowi tani punkt odniesienia, a jednocześnie jego ortogonalność w stosunku do
modeli drzewiastych (bo bazuje na zupełnie innych założeniach) sprawia, że w zespole wnosi
nowe informacje. Klasyfikator bayesowski jest też trzonem trzeciej warstwy decyzyjnej systemu
(rozdział 4.6).





### 4.3.7. Decision Tree


Drzewo decyzyjne dzieli przestrzeń cech serią rekursywnych podziałów binarnych, dobieranych
tak, aby maksymalizować zysk informacyjny lub minimalizować zanieczyszczenie Giniego [41].
Każdy węzeł wewnętrzny zawiera pytanie typu czy cecha X jest mniejsza od progu T?, a każdy
liść zawiera predykcję klasy lub jej rozkład.

Pojedyncze drzewo wypada w tym zestawie najsłabiej spośród siedmiu klasyfikatorów (przy zbyt
głębokim drzewie się przeucza, przy zbyt płytkim niedouczy), ale jego obecność w zespole ma
uzasadnienie metodologiczne. Drzewo jest najprostszą formą interpretowalnej decyzji
algorytmicznej, a jego wynik da się narysować jako diagram if-then-else. Dla obrony przed
phishingiem ma to znaczenie praktyczne: analityk centrum bezpieczeństwa może wziąć graficzną
reprezentację drzewa i prześledzić ścieżkę, która doprowadziła do oznaczenia konkretnego URL
jako podejrzanego. W tym projekcie algorytm genetyczny dobrał głębokość drzewa równą sześć,
co daje maksymalnie 64 ścieżki decyzyjne - liczbę na tyle niewielką, że pełne drzewo można
zmieścić na jednym arkuszu A4 i pokazać operatorowi podczas obrony alarmu.


### 4.3.8. Zespoły klasyfikatorów


Trzy metody zespołowe zaimplementowano w module src/models/ensemble.py. Soft voting
polega na uśrednieniu prawdopodobieństw klas zwracanych przez wszystkie klasyfikatory.
Wymaga, aby każdy składowy model implementował metodę predict_proba. Stanowi domyślny
wariant agregacji ML w opisanej architekturze. Hard voting sprowadza się do głosowania
większościowego na poziomie decyzji binarnej i nie wymaga prawdopodobieństw. Daje gorsze
wyniki w przypadkach, gdy klasyfikatory mają zbliżone, ale niepewne prawdopodobieństwa,
ponieważ traci informację o stopniu pewności. Stacking uczy oddzielny meta-model
(LogisticRegression) na predykcjach klasyfikatorów bazowych. Aby zapobiec wyciekowi
danych, predykcje bazowe generowane są w trakcie pięciokrotnej walidacji krzyżowej, czyli
każda predykcja pochodzi z modelu, który tej próbki nie widział w treningu.

        final_estimator=LogisticRegression(class_weight='balanced',
                                                                max_iter=1000,                       random_state=42),



    c                                 v                                        =                                       5                           ,
)

Listing 2. Konfiguracja meta-modelu w stacking ensemble (src/models/ensemble.py).


### 4.3.9. Wykrywanie rozbieżności w zespole


Funkcja get_disagreement_summary (moduł src/models/disagreement.py) oblicza wskaźnik
rozbieżności między predykcjami klasyfikatorów. Wskaźnikiem jest znormalizowana entropia
rozkładu predykcji binarnych. Dla siedmiu klasyfikatorów rozkład typu [7, 0] (jednomyślność)
daje entropię równą zero, a rozkład [4, 3] (maksymalna niezgoda) zbliża się do jedności. W
obecnej implementacji próg uznania próbki za graniczną ustawiono empirycznie na 0,7.
Przekroczenie progu jest flagowane w odpowiedzi API i jest sygnałem dla analityka, że dany
przypadek wymaga ręcznej weryfikacji.

Wybór entropii zamiast prostszej miary, takiej jak proporcja głosów mniejszościowych, ma
uzasadnienie informacyjne. Entropia traktuje rozkład [6, 1] i [5, 2] różnie, co odzwierciedla
intuicję, że jeden dysydent w grupie siedmiu jest słabszym sygnałem niezgody niż dwóch. Dla
rozkładu jednomyślnego entropia jest dokładnie zerowa, co dobrze pasuje do agregatora
opisanego w rozdziale 4.7.



## 4.4. Optymalizacja ewolucyjna (algorytm genetyczny)



### 4.4.1. Motywacja i krótki rys historyczny


Dobór hiperparametrów klasyfikatora ML jest klasycznym problemem optymalizacji w
przestrzeni o mieszanym typie. Część parametrów jest liczbami całkowitymi (liczba drzew,
głębokość), część liczbami rzeczywistymi w skali liniowej lub logarytmicznej (C w SVM,
learning_rate     w XGBoost), a część zmiennymi kategorialnymi (rodzaj jądra, kryterium
podziału). Przestrzeń ta jest nieciągła i nie ma dostępnego gradientu, a próba dostrojenia każdego
parametru ręcznie nawet dla jednego klasyfikatora kosztuje godziny pracy badacza i daje wyniki
gorsze od metod automatycznych.


Klasyczna metoda wyszukiwania siatkowego (grid search) skaluje się wykładniczo z liczbą
wymiarów. Dla XGBoost, dla którego optymalizowano dziewięć parametrów, trzy wartości na
każdym wymiarze dają 39 = 19683 konfiguracji, co po pięciokrotnej walidacji krzyżowej daje
blisko 100 tysięcy treningów. Wyszukiwanie losowe (random search) jest istotnie bardziej
efektywne, ponieważ większość wymiarów ma niski wpływ i przeszukiwanie ich z siatkowym
krokiem jest marnotrawne [40]. Jeszcze efektywniejsza jest optymalizacja bayesowska (na
przykład Optuna), która modeluje funkcję celu zastępczo i dobiera kolejne próbki na podstawie
modelu zastępczego. Domyślnym samplerem biblioteki Optuna jest TPE (Tree-structured Parzen Estimator), a wariant oparty na procesie Gaussa stanowi osobną, opcjonalną metodę. Optymalizacja bayesowska bywa jednak wrażliwa na zmienne kategorialne i dobór przestrzeni; w tym projekcie wartości kategorialne i tak mapowane są na indeksy (src/optimization/search_spaces.py). Algorytm genetyczny wybrano ze względu na naturalną obsługę mieszanych przestrzeni oraz prostą kontrolę kosztu obliczeń, a nie z powodu udowodnionej przewagi nad optymalizacją bayesowską.

Algorytmy genetyczne, sformułowane przez Johna Hollanda w latach siedemdziesiątych [34] i
rozwijane jako odrębna gałąź obliczeń ewolucyjnych [18], przyjmują inną drogę. Przeszukują
przestrzeń utrzymując populację rozwiązań, które ewoluują przez selekcję, krzyżowanie i
mutację. W praktyce daje to kilka korzyści, które dobrze pasują do problemu hiperparametrów:
GA radzi sobie z mieszanką liczb całkowitych, ciągłych i kategorialnych bez sztucznego
mapowania, populacyjny charakter pomaga wyjść z lokalnych ekstremów, a ocena osobników w
jednej generacji jest niezależna, więc całość łatwo zrównoleglić. Ceną jest większy koszt
obliczeniowy niż w optymalizacji bayesowskiej i konieczność strojenia samych metaparametrów
algorytmu (wielkość populacji, prawdopodobieństwa krzyżowania i mutacji).


### 4.4.2. Implementacja na bazie DEAP


Optymalizację zrealizowano w bibliotece DEAP (Fortin i in. [7], Distributed Evolutionary
Algorithms in Python, wersja 1.4.3). DEAP udostępnia gotowe operatory selekcji, krzyżowania i
mutacji, łatwo integruje się ze scikit-learn i pozwala też sięgnąć po bardziej zaawansowane
warianty obliczeń ewolucyjnych (NSGA-II, CMA-ES, programowanie genetyczne), gdyby
projekt rozszerzano w przyszłości. W module src/optimization/ga_optimizer.py znajdują się
dwie kluczowe funkcje: setup_toolbox (konfiguracja DEAP) i run_ga_optimization (główna
pętla ewolucyjna).

Podczas implementacji szybko okazało się, że same operatory mutacji i krzyżowania nie
wystarczą - trzeba pilnować ograniczeń dziedziny. DEAP z operatorem cxBlend potrafił mi



wygenerować wartości ujemne dla parametrów takich jak n_estimators w Random Forest, czego
scikit-learn naturalnie nie zaakceptował. Dodanie dekoratora checkBounds rozwiązało problem,
ale dopiero po kilku nieudanych uruchomieniach i ręcznym przejrzeniu wartości osobników.
Lekcja: w tego typu optymalizacji warto narzucić ograniczenia od pierwszej generacji, nawet
jeśli wstępne osobniki wyglądają poprawnie.

Reprezentacja osobnika

Osobnik      jest    listą    wartości    hiperparametrów.   Każdy     hiperparametr   ma    w
src/optimization/search_spaces.py zdefiniowaną przestrzeń przeszukiwań - z trzema typami:


    •    integer - liczba całkowita w zakresie (np. n_estimators w RF: 50-500);
    •    float - liczba zmiennoprzecinkowa, opcjonalnie w skali logarytmicznej (np. C w SVM lub
         learning_rate w XGB);

    •    categorical - indeks w liście wartości (np. kernel ∈ {'rbf', 'linear', 'poly'}).

Operatory genetyczne

    •    Selekcja: turniejowa, rozmiar turnieju 3 (tools.selTournament(tournsize=3)). Wybór
         trzech osobników i przepuszczenie najlepszego do kolejnej generacji równoważy
         eksplorację i eksploatację.
    •    Krzyżowanie: mieszane (tools.cxBlend(alpha=0.5)). Tworzy dziecko jako kombinację
         afiniczną rodziców z parametrem mieszania 𝛼 = 0,5. Z prawdopodobieństwem cxpb=0.7.
    •    Mutacja:        ograniczona     wielomianowa   (tools.mutPolynomialBounded(eta=20.0,
         indpb=0.2)).    Dla każdego genu z prawdopodobieństwem 20% generuje wartość z
         rozkładu wielomianowego ograniczonego do dolnego i górnego ograniczenia parametru.
         Parametr eta=20 koncentruje mutacje blisko wartości oryginalnej, sprzyjając lokalnej
         eksploatacji.

Oprócz tego zaimplementowano dekorator checkBounds, który egzekwuje ograniczenia po
krzyżowaniu i mutacji. Eliminuje to przypadki, w których operatory ciągłe generują wartości
spoza dopuszczalnego zakresu albo liczby zespolone (problem znany z cxBlend dla skrajnych
alfa).




Funkcja celu

Funkcja celu (moduł src/optimization/fitness.py) maksymalizuje F1-score z 5-krotnej
stratifikowanej walidacji krzyżowej (cross_val_score(... cv=5, scoring=f1_scorer)). Wybór
F1 jest motywowany wrażliwością problemu na koszt fałszywych negatywów (przeoczona
próbka phishingowa) oraz fałszywych pozytywów (nieprawidłowo oznaczony legalny
komunikat). Klasa-mniejszościowa to phishing, a F1 binarny dobrze balansuje precyzję i czułość.

Stratifikowana 5-krotna walidacja krzyżowa chroni przed overfittingiem do losowego podziału i
jest standardem porównawczym w literaturze.

Pętla ewolucyjna

Pętla wykorzystuje algorytm eaSimple z DEAP:

     •   populacja początkowa: 50 osobników losowych w przestrzeni przeszukiwań;
     •   liczba generacji: 30;
     •   prawdopodobieństwo krzyżowania: 0,7;
     •   prawdopodobieństwo mutacji: 0,2;
     •   Hall of Fame: 10 najlepszych osobników, automatycznie przenoszonych pomiędzy
         generacjami (elitaryzm).

Każdy bieg jest rejestrowany w MLflow [23] (src/optimization/mlflow_tracker.py):
zapisywane są hiperparametry, F1-score, średnie, odchylenia standardowe, minima i maksima
populacji w każdej generacji, a także najlepszy osobnik jako artefakt.

Wersjonowanie modeli

Po       zakończeniu       optymalizacji    najlepszy      model         jest       zapisywany   w
models/optimized/{classifier}_optimized.joblib                wraz              z        metadanymi
(models/optimized/{classifier}_metadata.json - data treningu, F1 testowy, hiperparametry,
znacznik typu ga_optimized). Rejestr aktywnych modeli (src/optimization/model_registry.py )
wskazuje, którą wersję modelu (bazową, zoptymalizowaną) ma ładować API. Mechanizm
pozwala bezboleśnie podmieniać modele bez modyfikacji kodu serwera.



Przykładowa zawartość pliku metadanych po wykonaniu optymalizacji dla regresji logistycznej
(najlepszy z siedmiu klasyfikatorów po GA, F1=0,9749):

{
    "hyperparameters": { "C": 7.974174081913068, "penalty": "l2" },
}

Listing                     4.                  Przykład                             metadanych                                  modelu                              po                      optymalizacji                                   GA
(models/optimized/lr_metadata.json).

Pełny komplet siedmiu plików metadanych jest zapisany w repozytorium i jest jednym z
głównych źródeł wyników raportowanych w rozdziale piątym pracy.



## 4.5. System regułowy


System regułowy zapisuje wiedzę ekspercką w pliku YAML i ocenia adres URL przez
sprawdzenie kilku zważonych warunków. Plik z regułami ładuje RuleEngine (moduł
src/paradigms/rules/engine.py) i waliduje go schemat Pydantic.


Struktura reguły
    description:                                             "URL                    uses                known                           URL             shortening                                              service"
            -                                                                                        t                                               .                                               c                                        o



         - buff.ly

Listing      3.   Przykład   definicji   reguły      wykrywającej        skrócone     adresy   URL
(src/paradigms/rules/phishing_rules.yaml).

W systemie zaimplementowano 16 reguł w czterech kategoriach:

                  Liczba
Kategoria         reguł      Przykłady

Struktura         4          ip_address_host,        shortened_url,           excessive_subdomains,

URL                          suspicious_tld

Słowa             5          urgent_keywords,            security_keywords,         action_keywords,

kluczowe                     brand_impersonation, threat_keywords

Struktura         4          long_url, many_special_chars, high_entropy, deep_path

tekstu

Domena            3          no_https, port_in_url, at_symbol


Tabela 2. Kategorie i liczba reguł w warstwie eksperckiej PhishGuard.

Wagi reguł zostały dobrane na podstawie obserwacji literatury i danych historycznych.
Sumaryczna waga aktywnych reguł stanowi nieprzeszacowany wynik (znormalizowany do
zakresu [0,1] poprzez min(total_score, 1.0)).

Algorytm ewaluacji

RuleEngine.evaluate(features, raw_url=...) wykonuje następujące kroki:


# 1. Iteruje po wszystkich regułach.

   2. Dla każdej reguły wywołuje dedykowany ewaluator zależny od typu warunku:
          _evaluate_keyword_match, _evaluate_feature_check lub _evaluate_domain_match.

   3. Dla reguł aktywnych dolicza wagę do sumarycznego wyniku oraz zapisuje listę
          dopasowanych wartości.




   4. Zwraca      słownik    zawierający     znormalizowany      wynik,   decyzję     ('phishing'     /
       'legitimate'),     pewność (odległość od progu 0,5), listę aktywnych reguł oraz
       maksymalny możliwy wynik.

Trzy typy warunków:

   •   keyword_match - sprawdza obecność dowolnego ze słów kluczowych w surowym tekście

       (case-insensitive, podciągowy);
   •   feature_check - porównuje wartość cechy z wartością progową przy użyciu operatora

       (equals, greater_than, less_than, contains);
   •   domain_match     - sprawdza, czy URL zawiera dowolną domenę z listy (typowo dla
       skróconych linków).

System regułowy jest z założenia tańszy obliczeniowo i bardziej interpretowalny niż
klasyfikatory ML, a jego wynik jest jednym z trzech komponentów końcowej agregacji.



## 4.6. System probabilistyczny (klasyfikator bayesowski)



### 4.6.1. Twierdzenie Bayesa i jego zastosowanie do klasyfikacji


Probabilistyczna warstwa systemu opiera się na twierdzeniu Bayesa, sformułowanym przez
Thomasa Bayesa w połowie osiemnastego wieku i opublikowanym pośmiertnie w 1763 roku.
Twierdzenie pozwala odwrócić kierunek wnioskowania o prawdopodobieństwie warunkowym.
Jeśli interesuje nas prawdopodobieństwo klasy 𝐶 pod warunkiem zaobserwowania zbioru cech
𝑋 = (𝑥1 , 𝑥2 , … , 𝑥𝑛 ), możemy zapisać:

                                                   𝑃(𝑋 ∣ 𝐶) ⋅ 𝑃(𝐶)
                                      𝑃(𝐶 ∣ 𝑋) =
                                                        𝑃(𝑋)

Wzór ten zawiera cztery składowe interpretowane następująco. 𝑃(𝐶 ∣ 𝑋) to posterior, czyli
prawdopodobieństwo       klasy   po     zaobserwowaniu     cech. 𝑃(𝑋 ∣ 𝐶) to        likelihood,   czyli
prawdopodobieństwo zaobserwowania danych cech, jeżeli klasa byłaby 𝐶. 𝑃(𝐶) to prior, czyli
prawdopodobieństwo klasy bez znajomości cech, oszacowane na podstawie częstości klas w
zbiorze treningowym. 𝑃(𝑋) to evidence, mianownik normalizujący, niezależny od wyboru klasy i
pomijany w klasyfikacji binarnej, ponieważ jest taki sam dla obu klas.


W praktyce obliczenie 𝑃(𝑋 ∣ 𝐶) dla wielowymiarowego 𝑋 wymaga oszacowania pełnego
rozkładu łącznego cech, co jest niewykonalne ze względu na klątwę wymiarowości. Klasyfikator
naiwny Bayesa rozwiązuje ten problem przyjmując założenie o warunkowej niezależności cech,
czyli:

                                                   𝑛

                                                 𝑖=1


Każdy element iloczynu można oszacować osobno, co redukuje liczbę parametrów modelu z
wykładniczej do liniowej względem liczby cech. Naruszenie założenia w realnych danych
pogarsza estymację bezwzględnych wartości prawdopodobieństw, ale jak pokazano w badaniach
klasycznych [39], dokładność decyzji klasyfikacyjnej pozostaje wysoka, ponieważ błędy
korelacji często redukują się symetrycznie dla obu klas.


### 4.6.2. Wariant Gaussowski i kalibracja


Wariant gaussowski Naive Bayesa zakłada, że każda cecha ciągła ma wewnątrz klasy rozkład
normalny, którego średnia i wariancja estymowane są ze zbioru treningowego. Wzór staje się:

                                            1            (𝑥𝑖 − 𝜇𝑖,𝐶 )2
                           𝑃(𝑥𝑖 ∣ 𝐶) =            exp (−       2       )
                                                2            2𝜎𝑖,𝐶
                                         √2𝜋𝜎𝑖,𝐶


W implementacji sklearn.naive_bayes.GaussianNB parametr var_smoothing dodaje niewielką
wartość do wariancji każdej cechy, żeby zapewnić stabilność numeryczną. To jedyny
hiperparametr klasyfikatora i optymalizacja genetyczna znalazła dla niego wartość 4,4·10⁻¹¹,
znacznie niższą niż domyślne 10⁻⁹. Logarytmiczna wrażliwość tego parametru sprawia, że
dobranie go ręcznie albo siatkowym wyszukiwaniem jest niewdzięczne; algorytm genetyczny z
operatorem cxBlend poradził sobie z tą przestrzenią bez konieczności jawnego mapowania na
skalę log.

Trzeba dodać, że posteriory generowane przez Naive Bayesa są często słabo skalibrowane.
Klasyfikator ten ma tendencję do zwracania prawdopodobieństw bliskich zeru lub jedności,
nawet w przypadkach, w których faktyczna pewność jest mniejsza. Wynika to z mnożenia wielu
prawdopodobieństw warunkowych. Iloczyn dziesięciu liczb mniejszych od 0,5 wynosi około


0,001, co po normalizacji często daje skrajne wartości posteriora. Dla potrzeb klasyfikacji
binarnej (próg 0,5) zjawisko to ma niewielki wpływ, ale dla zastosowań wymagających
dokładnego oszacowania pewności (na przykład ranking próbek do ręcznej weryfikacji) zalecana
jest kalibracja izotoniczna lub kalibracja Platta. W projekcie nie zastosowano kalibracji w
obecnej wersji, choć jest ona wymieniona w rozdziale ograniczeń jako jeden z planowanych
kierunków rozwoju.


### 4.6.3. Implementacja w projekcie


Klasyfikator     bayesowski   (moduł    src/paradigms/bayesian/classifier.py )         opakowuje
GaussianNB     z biblioteki scikit-learn w klasę BayesianClassifier udostępniającą metodę
predict_with_posterior.    W odróżnieniu od standardowego predict_proba, metoda zwraca
rozszerzony słownik:

   •   posterior_phishing - 𝑃(phishing ∣ features);

   •   posterior_legitimate - 𝑃(legitimate ∣ features);

   •   prediction - decyzja binarna (próg 0,5);

   •   confidence - max z obu posteriorów;

   •   prior_info - słownik z logarytmami priorów i ich wartościami nominalnymi.

Klasyfikator     jest   skonstruowany    jako        Pipeline([('scaler',    StandardScaler()),

('classifier',      GaussianNB(var_smoothing=1e-9))]).       Skalowanie     poprawia   stabilność
numeryczną estymacji wariancji w GaussianNB, a parametr var_smoothing zapobiega dzieleniu
przez wariancję zerową.

W docstringach klasyfikatora zaznaczono, że posteriory Naive Bayes są często słabo
skalibrowane i przesunięte do skrajów 0/1 . Ich rola w warstwie agregacji jest więc raczej
rankingowa niż kalibracyjna. Mimo to klasyfikator bayesowski jest przydatny z dwóch powodów.
Zakłada warunkową niezależność cech, więc działa inaczej niż modele drzewiaste i jądrowe.
Dostarcza też jawnej oceny prawdopodobieństwa, którą łatwo zinterpretować w języku Bayesa.






## 4.7. Agregacja wielo-paradygmatowa


Agregator (moduł src/paradigms/aggregation/aggregator.py ) łączy wyniki trzech warstw (ML
ensemble, system regułowy, klasyfikator bayesowski) zgodnie z ważoną liniową kombinacją:

                        𝑃final = 𝑤ML ⋅ 𝑃ML + 𝑤rules ⋅ 𝑆rules + 𝑤bayes ⋅ 𝑃bayes

Domyślne wagi (DEFAULT_WEIGHTS w src/paradigms/aggregation/weights.py ) wynoszą 𝑤ML =
0,5, 𝑤rules = 0,3, 𝑤bayes = 0,2. Wagi można zmienić, przekazując inny obiekt ParadigmWeights
przy inicjalizacji agregatora (MultiParadigmAggregator(weights=...)). Dzięki temu można je
dostroić względem zbioru walidacyjnego.

Wkład poszczególnych warstw

W       odpowiedzi     API      endpoint       /predict/multi-paradigm           zwraca   strukturę
paradigm_contributions    z trzema obiektami (ml_ensemble, rules, bayesian), każdym o
atrybutach:

    •   probability - surowe prawdopodobieństwo z danej warstwy;

    •   weight - waga warstwy w agregacji;

    •   weighted_contribution - iloczyn prawdopodobieństwa i wagi;

    •   prediction - decyzja tej warstwy.

Dzięki temu w odpowiedzi widać konkretne wartości - dla phishingu PayPal  są
to: ML 0,4602, reguły 0,3 i Bayes 0,2 jako wkłady wagowe, a po zsumowaniu wynik finalny
0,9602.

Wykrywanie rozbieżności między warstwami decyzyjnymi

Moduł src/paradigms/aggregation/disagreement.py oblicza wskaźnik rozbieżności w oparciu o
cztery komponenty:


# 1. Wariancja prawdopodobieństw - Var([𝑃ML , 𝑆rules , 𝑃bayes ]).


    2. Rozkład decyzji binarnych - liczba warstw wskazujących phishing kontra legitimate.
    3. Lista odstających - te z warstw, których decyzja odbiega od większości.




# 4. Rozpiętość prawdopodobieństw - max𝑃 − min𝑃.


Wskaźnik sumaryczny obliczany jest jako znormalizowana entropia rozkładu binarnych decyzji
trzech warstw, 𝐻/log₂2 = 1 (dwie klasy głosów; dla rozkładu 2:1 ≈ 0,918, dla 4:3 ≈ 0,985) , gdzie 𝐻 liczone jest dla dwóch klas (phishing, legitimate). Cztery
wymienione wielkości (wariancja, rozkład, lista odstających, rozpiętość) zwracane są jako
diagnostyka towarzysząca, ale do samego scoru wchodzi tylko rozkład głosów binarnych. Próg
0,7 pozwala oznaczyć próbkę jako edge case wymagający dalszej analizy. Wartość ta jest
zapisana           w          stałej        PARADIGM_DISAGREEMENT_THRESHOLD               modułu
src/paradigms/aggregation/disagreement.py.


Generowanie wyjaśnienia

Funkcja _generate_explanation agregatora produkuje tekstowe podsumowanie decyzji
zawierające:

   •   typ decyzji i prawdopodobieństwo;
   •   wartości prawdopodobieństwa każdej z warstw;
   •   listę pierwszych trzech aktywnych reguł (z dopisem +N more, jeśli reguł jest więcej);
   •   ostrzeżenie o wysokim disagreement, gdy próbka jest edge case.



## 4.8. API REST i aplikacja serwerowa


Warstwa serwerowa została zaimplementowana w oparciu o framework FastAPI (Ramirez [10],
src/api/main.py,       src/api/endpoints.py).    Architektura    realizuje   sześć    endpointów
predykcyjnych oraz endpoint zdrowia (/health) i metadanych (/).

Inicjalizacja modeli

Decyzja architektoniczna ważna dla wydajności: modele ładowane są raz, w trakcie startu
aplikacji, przez mechanizm lifespan FastAPI. Eliminuje to opóźnienie wczytywania modeli z
dysku przy każdym żądaniu (które dla pełnego zespołu sięgałoby kilkuset milisekund) i
utrzymuje czas odpowiedzi poniżej 500 ms.

Sekwencja ładowania (uproszczona):




    1. phishing_detector - aktywny model RF z rejestru (z fallbackiem do wersji bazowej);
    2. ensemble/voting_soft      -      aktywny    zespół    z   rejestru       (z     fallbackiem    do
         models/ensemble/voting_soft.joblib);


# 3. Ewentualnie voting_hard i stacking (do porównań);

    4. rule_engine - silnik regułowy z YAML;
    5. bayesian - klasyfikator bayesowski z models/bayesian/;
    6. aggregator - inicjalizacja agregatora z domyślnymi wagami;
    7. email_ensemble i sms_ensemble - modele wyspecjalizowane dla wiadomości tekstowych z
         ich metadanymi (liczba cech, dokładność testowa).

Endpointy

Endpoint                  Metoda           Zwraca
/                         GET              Metadane API, lista endpointów
/health                   GET              Status modeli (model_loaded, email_model_loaded,
                                           sms_model_loaded)

/predict                  POST             Szybka klasyfikacja URL przez aktywny RF
/predict/ensemble         POST             Klasyfikacja      zespołem       7        klasyfikatorów   +
                                           indywidualne wyniki + disagreement
/predict/multi-           POST             Synteza ML + reguły + Bayes + rozbieżności między
paradigm
                                           warstwami + aktywne reguły + wyjaśnienie
/predict/email            POST             Klasyfikacja surowego tekstu e-mail (65 cech)
/predict/email/file       POST             Klasyfikacja przesłanego pliku .eml (max 5 MB)
                          (multipart)
/predict/sms              POST             Klasyfikacja wiadomości SMS (70 cech)

Tabela 3. Wykaz endpointów API PhishGuard wraz z funkcjami.

Tabela     3   opisuje   pełną   wersję    repozytorium.     Lokalny    demo          build   URL-only
(C:\Users\ldrazek\phishguard-build), używany podczas prac; udostępnia
podzbiór tych endpointów: /, /health, /predict, /predict/ensemble, /predict/multi-paradigm



oraz /app (frontend webowy). Endpointy e-mail i SMS pozostają domeną pełnego repozytorium,
ponieważ wymagają modeli wyspecjalizowanych z fazy 6, których w demo build nie
wytrenowano.

Walidacja danych wejściowych

Wszystkie żądania są walidowane modelami Pydantic [25] (src/api/models.py). Dla każdego
endpointu zdefiniowany jest model żądania (np. URLRequest, EmailTextRequest, SMSRequest)
oraz      odpowiedzi         (np.       PredictionResponse,          EnsemblePredictionResponse ,

MultiParadigmResponse).    FastAPI automatycznie generuje schematy OpenAPI 3.0 oraz
dokumentację Swagger UI dostępną pod /docs.

Obsługa błędów

Endpointy zwracają standardowe kody HTTP:

   •   200 - poprawna klasyfikacja;
   •   400 - błąd walidacji wejścia (np. plik inny niż .eml, zbyt duży plik);
   •   500 - błąd wewnętrzny (np. nieoczekiwany wyjątek w pipeline ekstrakcji cech);
   •   503 - jeden z wymaganych modeli nie został załadowany (np. brak zoptymalizowanego
       ensemble).

Mechanizm 503 jest istotny dla niezawodności. Zamiast zwracać błędną klasyfikację, API jawnie
informuje, że nie potrafi obsłużyć żądania i wskazuje, którego modelu brakuje.

Wybór def vs async def

W warstwie endpointów świadomie zastosowano synchroniczne def zamiast async def dla
operacji predykcji - inferencja ML jest ograniczona CPU, a nie I/O. FastAPI automatycznie
wykonuje synchroniczne funkcje w puli wątków, co eliminuje ryzyko blokowania pętli zdarzeń.
Asynchronicznie     zaimplementowano        wyłącznie     endpoint    przyjmujący    plik   .eml

(predict_email_file), gdzie odczyt pliku z requestu jest typową operacją I/O.






## 4.9. Aplikacja webowa demonstratora


Warstwa prezentacji systemu jest jednostronicową aplikacją webową, którą serwuje ten sam
proces FastAPI co API. Pliki statyczne znajdują się w katalogu src/api/static/, a montowanie
odbywa się przez wbudowaną klasę StaticFiles. Trzymanie frontendu i backendu w jednym
procesie upraszcza demo: nie trzeba uruchamiać osobnego serwera Node.js ani Nginx, nie ma
problemu z CORS i nie da się przypadkiem wdrożyć rozbieżnych wersji.


### 4.9.1. Wybór technologii


Frontend wykonano w czystym HTML, CSS i JavaScript, bez żadnego frameworku ani biblioteki
zewnętrznej. Frameworki typu React czy Vue.js mają sens, gdy aplikacja ma rozbudowaną logikę
widoku, dużo stanów lokalnych i potrzebę szybkiego prototypowania. Tutaj zakres funkcjonalny
jest świadomie minimalny - jedno pole wejściowe i kilka paneli wyników - więc komplikowanie
stosu narzędziowego o transpilery i bundlery byłoby nieproporcjonalne do zysku. Aplikacja bez
zewnętrznych zależności jest natychmiast uruchamialna i nie wymaga osobnego okresu wsparcia
dla łatania luk w bibliotekach.


### 4.9.2. Schemat działania


Aplikację tworzą trzy pliki. Plik index.html definiuje statyczną strukturę dokumentu z sześcioma
głównymi panelami informacyjnymi. Plik styles.css zawiera własne reguły wizualne, oparte na
palecie stalowo-grafitowej z akcentem bursztynowym (kolor wiodący, używany do podkreślania
ważnych elementów), mglistej miętowej zieleni (sygnalizującej bezpieczne predykcje) oraz
amarantu (oznaczającego phishing). Typografia łączy IBM Plex Sans dla tekstu informacyjnego i
JetBrains Mono dla wartości liczbowych, fragmentów kodu i nazw klasyfikatorów. Wybór
czcionek monospacjowych dla wartości liczbowych wynika z potrzeby wyrównania wizualnego
(procenty o tej samej liczbie cyfr ułożone w kolumnach). Plik app.js zawiera całą logikę
interakcji, w tym wywołania trzech endpointów API (/health, /predict/multi-paradigm,
/predict/ensemble) oraz renderowanie wyników.

Układ aplikacji jest podzielony na sześć paneli odpowiadających kolejnym krokom analizy:
wejście   (pole    URL     i      przyciski   przykładów),   werdykt   końcowy   z   miernikiem
prawdopodobieństwa, wkład trzech warstw decyzyjnych w postaci pasków, siatka siedmiu


klasyfikatorów ML z indywidualnymi predykcjami, lista aktywnych reguł eksperckich oraz
zestaw wybranych cech URL liczonych w przeglądarce. Najważniejsze trzy panele to werdykt,
wkład warstw decyzyjnych i siatka klasyfikatorów - to one pozwalają operatorowi szybko
zobaczyć, co przesądziło o decyzji i które warstwy się ze sobą zgadzają. Pozostałe panele (reguły,
cechy) pełnią rolę pomocniczą, dostarczając kontekstu uzasadniającego werdykt.





 Rysunek 2. Aplikacja webowa po analizie phishingu PayPal  - werdykt PHISHING z
              prawdopodobieństwem 96,02%, siedem aktywnych reguł eksperckich.




Rysunek 3. Aplikacja webowa po analizie URL Bank of America  - werdykt LEGALNA,
              brak aktywnych reguł, wszystkie warstwy zgodnie wskazują legitimate.





Rysunek 4. Aplikacja webowa po analizie URL z adresem IP w prywatnym zakresie  -
          werdykt PHISHING z prawdopodobieństwem 99,41%, sześć aktywnych reguł.






### 4.9.3. Komunikacja z API


Aplikacja komunikuje się z backendem przez fetch, używając metody POST z ciałem w
formacie JSON dla endpointów predykcji oraz GET dla sprawdzenia stanu. Wszystkie
wywołania są opakowane w obsługę błędów, która prezentuje komunikat o niepowodzeniu w
pasku statusu pod polem wejściowym. Wskaźnik stanu w pasku nawigacyjnym aktualizowany
jest co trzydzieści sekund i sygnalizuje, czy serwer jest dostępny i czy modele są załadowane. W
razie awarii backendu (na przykład zatrzymania procesu uvicorn) wskaźnik zmienia kolor na
amarantowy w ciągu pół minuty, co pozwala operatorowi szybko zorientować się w sytuacji.

Aplikacja w obecnej formie zamyka fazę ósmą roadmapy projektu (interfejs webowy),
pierwotnie planowaną na późniejszy etap pracy. Funkcjonalność batch CSV i upload plików .eml
z poziomu UI pozostaje w fazie planowania.



## 4.10. Testy automatyczne i zapewnienie jakości


Pełne repozytorium zawiera zestaw testów automatycznych w katalogu tests/. Testy obejmują
ekstrakcję cech, ewaluację reguł, trening klasyfikatorów, agregację wyników oraz endpointy
FastAPI. Testy jednostkowe weryfikują pojedyncze funkcje, testy integracyjne sprawdzają
współpracę modułów, a testy API używają klienta testowego FastAPI do obsługi typowych i
brzegowych żądań. Dodatkową rolę pełnią testy regresyjne, które chronią przed niezamierzoną
zmianą predykcji po modyfikacji kodu. Lokalny demo build URL-only nie zawiera katalogu
tests/, ponieważ powstał z plików źródłowych pobranych z raw.githubusercontent.com z

pominięciem klona; weryfikacja działania endpointów odbywa się w nim przez smoke-testy w
praca/smoke-tests/.

Framework testowy to pytest. Wybór ten jest standardem w społeczności Pythona ze względu na
zwięzłą składnię, bogaty system fixtur i naturalną obsługę parametryzacji. Do pomiaru pokrycia
można użyć pytest-cov, natomiast w ramach tej pracy głównym celem testów była weryfikacja
działania najważniejszych ścieżek programu, a nie osiągnięcie konkretnego procentu pokrycia.

Klient testowy FastAPI używany jest w testach API. Tworzy on instancję aplikacji w pamięci
procesu testowego, dzięki czemu testy nie wymagają uruchamiania serwera HTTP. Dla testów




używających pełnych modeli zastosowano fikstury sesyjne. Ładują one modele raz na cały
zestaw testów, co skraca czas wykonania i ogranicza liczbę kosztownych operacji I/O.

Polityka modyfikacji projektu zakłada, że zmiana kodu powinna być sprawdzona uruchomieniem
odpowiedniego fragmentu testów. W razie wykrycia regresji kod należy poprawić albo
świadomie zaktualizować test, jeżeli wcześniejsza asercja przestała odpowiadać aktualnemu
założeniu projektowemu. Taka praktyka ogranicza ryzyko cichego pogorszenia jakości
demonstratora.







# 5. Wyniki projektu

Wszystkie wyniki URL pochodzą z jednego protokołu: wspólny odłożony zbiór testowy
z artefaktu `cache/url_training_data.joblib` (200 próbek treningowych, 50 testowych,
25/25, 30 cech), podział **losowy stratyfikowany** (`random_state=42`) — nie
temporalny. Skrypt: `scripts/evaluate_url_models_honest.py`, raport:
`reports/url_eval_honest.csv`. Mały zbiór testowy (50 próbek) oznacza, że różnice
są orientacyjne i opisowe.

## 5.1. Klasyfikatory bazowe i zoptymalizowane GA (wspólny test)

Każdy klasyfikator oceniono na tym samym odłożonym teście. Kolumna „CV-fitness" to
F1 z 5-krotnej walidacji krzyżowej najlepszego osobnika GA i jest inną wielkością
niż wynik testowy; nie należy ich od siebie odejmować.

| Klasyfikator | F1 baza (test) | F1 GA (test) | Zysk (test) | CV-fitness |
|---|---|---|---|---|
| Logistic Regression | 0,9200 | 0,9362 | +0,0162 | 0,9749 |
| Random Forest | 0,9091 | 0,9259 | +0,0168 | 0,9705 |
| MLP | 0,9167 | 0,9583 | +0,0417 | 0,9697 |
| XGBoost | 0,9231 | 0,9259 | +0,0028 | 0,9623 |
| SVM (RBF) | 0,8846 | 0,9020 | +0,0173 | 0,9502 |
| Naive Bayes | 0,9020 | 0,9020 | +0,0000 | 0,9438 |
| Decision Tree | 0,8980 | 0,9259 | +0,0280 | 0,9656 |

Na wspólnym teście optymalizacja GA dała niewielką poprawę F1 (od +0,000 dla Naive
Bayes do +0,042 dla MLP). Jest to wynik jednego losowego podziału; stabilności
poprawy przy innych ziarnach nie badano, a koszt wyszukiwania (populacja 50,
30 generacji) nie jest tu zestawiony z wielkością zysku.

## 5.2. Zespoły klasyfikatorów (wspólny test)

| Wariant | F1 (test) |
|---|---|
| Hard voting | 0,9200 |
| Soft voting | 0,9231 |
| Stacking | 0,9231 |
| Najlepszy pojedynczy (MLP-GA) | 0,9583 |

Na wspólnym zbiorze testowym zespoły osiągnęły F1 ≈ 0,92 i **nie przewyższyły**
najlepszego pojedynczego modelu zoptymalizowanego GA (MLP, 0,958). W tym
eksperymencie zespół nie uzyskał przewagi; wynik ten opisano zgodnie z pomiarem.

## 5.3. Modele wyspecjalizowane (e-mail, SMS) — dane syntetyczne

Trzy różne wielkości należy rozróżnić. Zapisane w modelach pole `test_accuracy=1,0`
pochodzi z **syntetycznego odłożonego zbioru 20%** utworzonego przez skrypt
treningowy (`scripts/train_email_sms_models.py`, podział 80/20). Niezależne
5-krotne CV (`scripts/evaluate_email_sms_honest.py`) dało: e-mail acc 0,985 /
F1 0,984, SMS acc 1,0 / F1 1,0. Ewaluacja na pełnym zbiorze daje 1,0 (ten sam
zbiór, na którym trenowano) i jest wyłącznie kontrolą, nie miarą generalizacji.

| Typ | 5-fold CV acc | 5-fold CV F1 |
|---|---|---|
| E-mail (65 cech) | 0,985 | 0,984 |
| SMS (70 cech) | 1,000 | 1,000 |

Istotne ograniczenie zakresu: dane są syntetyczne i generowane z 20 szablonów na
klasę dla każdego typu (`scripts/create_email_sms_dataset.py`). W walidacji
krzyżowej większość wiadomości testowych ma swój szablon obecny w zbiorze
treningowym, dlatego CV mierzy przede wszystkim rozpoznawanie **wariantów znanych
szablonów**, a nie nowych kampanii ani rzeczywistych wiadomości. Wynik SMS równy
1,0 wynika z trywialnej separowalności tych danych. Twierdzenie o skuteczności
poza danymi syntetycznymi wymagałoby podziału grupowego według szablonu albo
niezależnego, ręcznie oznaczonego zbioru rzeczywistych wiadomości.

## 5.4. System wielowarstwowy — miara rozbieżności, wkład warstw, czas

**Miara rozbieżności.** Wskaźnik rozbieżności to znormalizowana entropia Shannona
rozkładu głosów, dzielona przez maksymalną entropię binarną log2(2) = 1 bit
(`src/models/disagreement.py`, `src/paradigms/aggregation/disagreement.py`;
17 testów jednostkowych). Dla trzech warstw każda niejednomyślność daje wynik
≈ 0,918, a jednomyślność 0. Dla siedmiu klasyfikatorów najbardziej wyrównany
podział 4/3 daje maksimum ≈ 0,985. Próg oznaczania przypadku granicznego ustawiono
na 0,7: dla warstw oznacza to „paradygmaty nie są jednomyślne", a dla zespołu ML —
„co najmniej dwa z siedmiu klasyfikatorów są odmiennego zdania". Flaga jest
wskaźnikiem niezgody głosów, a nie dowodem, że dana decyzja jest błędna.

**Wkład warstw (próba ilustracyjna z nakładaniem danych).** Na zbiorze 50
etykietowanych adresów (40 phishingowych z OpenPhish, 10 znanych legalnych) sam
zespół ML osiągnął 48/50 poprawnych decyzji, a pełny agregator trójwarstwowy 46/50.
Agregator zmienił dwie decyzje względem samego ML i obie okazały się błędne. Jest
to jednak **próba ilustracyjna, nie niezależna ocena skuteczności**: pierwsze 40
adresów pochodzi z tego samego pliku OpenPhish, z którego losowano dane treningowe
URL — po odtworzeniu losowania 13 z 40 trafia do zbioru treningowego, a 4 do
testowego. Dla rzetelnej oceny wkładu warstw potrzebna byłaby niezależna próba
(z deduplikacją) z pełnym raportem zmian decyzji oraz błędów FN/FP. W badanym
zakresie integracja trzech warstw nie poprawiła decyzji względem samego ML.

**Czas odpowiedzi.** Pomiar `/predict/multi-paradigm` (50 żądań, model rozgrzany,
cechy leksykalne, pomiar lokalny in-process przez TestClient): mediana ≈ 15 ms,
95. percentyl ≈ 16 ms — poniżej wymaganych 500 ms. Zakres twierdzenia ograniczono
do pojedynczego żądania po rozgrzaniu; nie obejmuje ono opóźnienia klient–serwer
ani obciążenia równoległego.



# 6. Podsumowanie

Zaprojektowano i wykonano system PhishGuard łączący ekstrakcję cech, siedem
klasyfikatorów uczenia maszynowego, optymalizację hiperparametrów algorytmem
genetycznym, system regułowy, klasyfikator bayesowski oraz warstwę agregacji z
interfejsem API i demonstratorem. Wkład własny obejmuje integrację komponentów,
dobór cech i mechanizm wykrywania rozbieżności między warstwami.

Wyniki należy odczytywać w zakresie przeprowadzonych pomiarów. Na wspólnym,
losowo podzielonym zbiorze testowym 50 adresów URL optymalizacja GA dała niewielką
poprawę F1 (do +0,042 dla MLP), a zespoły klasyfikatorów nie przewyższyły
najlepszego pojedynczego modelu zoptymalizowanego GA. Wyniki e-mail i SMS uzyskano
na danych syntetycznych generowanych z ograniczonej liczby szablonów i nie mierzą
one skuteczności na rzeczywistych wiadomościach. Na ilustracyjnej próbie 50 adresów
agregator trójwarstwowy uzyskał 46/50 poprawnych decyzji wobec 48/50 dla samego
zespołu ML; nie wykazano wzrostu skuteczności wynikającego z integracji warstw.
Naprawiono natomiast główny mechanizm pracy: po poprawieniu normalizacji entropii
flaga rozbieżności jest osiągalna i poprawnie sygnalizuje niezgodę głosów.
Czas odpowiedzi pojedynczego żądania po rozgrzaniu modelu mieści się poniżej 500 ms
w pomiarze lokalnym.

System pokazuje wyniki trzech warstw oraz aktywne reguły, co zwiększa
interpretowalność decyzji. Jest to cecha interfejsu, odrębna od zmierzonej
skuteczności klasyfikacji. Dalsze prace, które pozwoliłyby rozszerzyć wnioski, to
w szczególności: ewaluacja na niezależnych, rzeczywistych zbiorach wiadomości i
adresów, podział grupowy danych syntetycznych według szablonu, zestawienie kosztu
wyszukiwania GA z uzyskanym zyskiem oraz powtórzenia optymalizacji dla oceny jej
stabilności. Zakres opcjonalny obejmuje porównanie z modelem głębokim oraz
rozszerzenia OCR i wyjaśnień SHAP/LIME. Praca nie obejmowała bezpośredniego
porównania z modelami głębokimi i nie formułuje wniosku o przewadze nad nimi.


# 7. Bibliografia

7. Bibliografia
  1. APWG (Anti-Phishing Working Group), Phishing Activity Trends Report 4Q2025, 2026,
     https://apwg.org/trendsreports.
  2. Aleroud A., Zhou L., Phishing environments, techniques, and countermeasures: A survey,
     Computers & Security, vol. 68, 2017, ss. 160-196.
  3. Sahingoz O. K., Buber E., Demir O., Diri B., Machine learning based phishing detection
     from URLs, Expert Systems with Applications, vol. 117, 2019, ss. 345-357.
  4. Mohammad R. M., Thabtah F., McCluskey L., An assessment of features related to
     phishing websites using an automated technique, w: Proceedings of the International
     Conference for Internet Technology and Secured Transactions (ICITST-2012), IEEE,
     London 2012.
  5. Pedregosa F. i in., Scikit-learn: Machine Learning in Python, Journal of Machine
     Learning Research, vol. 12, 2011, ss. 2825-2830.
  6. Chen T., Guestrin C., XGBoost: A Scalable Tree Boosting System, w: Proceedings of the
     22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining,
     ACM, San Francisco 2016, ss. 785-794.
  7. Fortin F.-A., De Rainville F.-M., Gardner M.-A., Parizeau M., Gagne C., DEAP:
     Evolutionary Algorithms Made Easy, Journal of Machine Learning Research, vol. 13,
     2012, ss. 2171-2175.
  8. Chawla N. V., Bowyer K. W., Hall L. O., Kegelmeyer W. P., SMOTE: Synthetic Minority
     Over-sampling Technique, Journal of Artificial Intelligence Research, vol. 16, 2002, ss.
     321-357.
  9. Honnibal M., Montani I., Van Landeghem S., Boyd A., spaCy: Industrial-strength
     Natural Language Processing in Python, Explosion AI, 2020-2025, https://spacy.io.
  10. Ramirez S., FastAPI: Modern, fast (high-performance), web framework for building APIs
     with Python, Tiangolo, 2018-2026, https://fastapi.tiangolo.com.
  11. Pourreza M. i in., Machine Learning and Neural Networks for Phishing Detection: A
     Systematic Review (2017-2024), Electronics, vol. 14, no. 18, 2025, art. 3744.




12. Lundberg S. M., Lee S.-I., A Unified Approach to Interpreting Model Predictions, w:
   Advances in Neural Information Processing Systems 30 (NIPS 2017), Curran Associates,
   Long Beach 2017, ss. 4765-4774.
13. Ribeiro M. T., Singh S., Guestrin C., "Why Should I Trust You?": Explaining the
   Predictions of Any Classifier, w: Proceedings of the 22nd ACM SIGKDD International
   Conference on Knowledge Discovery and Data Mining, ACM, San Francisco 2016, ss.
   1135-1144.
14. UCI       Machine    Learning      Repository,      Phishing   Websites        Data   Set,
   https://archive.ics.uci.edu/dataset/327/phishing+websites (dostęp: maj 2026).
15. PhishTank Community, PhishTank - Out of the Net, into the Tank, OpenDNS LLC,
   https://www.phishtank.com (dostęp: maj 2026).
16. Nazario J., Phishing Corpus, https://monkey.org/~jose/phishing/ (dostęp: maj 2026).
17. CERT Polska, Krajobraz bezpieczeństwa polskiego internetu. Raport roczny CERT
   Polska za rok 2024, NASK PIB, Warszawa 2025, https://www.cert.pl/publikacje/raporty-
   roczne/.
18. Eiben A. E., Smith J. E., Introduction to Evolutionary Computing, wyd. 2., Springer,
   Berlin-Heidelberg 2015.
19. Friedman J. H., Greedy Function Approximation: A Gradient Boosting Machine, The
   Annals of Statistics, vol. 29, no. 5, 2001, ss. 1189-1232.
20. Breiman L., Random Forests, Machine Learning, vol. 45, no. 1, 2001, ss. 5-32.
21. Cortes C., Vapnik V., Support-Vector Networks, Machine Learning, vol. 20, no. 3, 1995,
   ss. 273-297.
22. Hochreiter S., Schmidhuber J., Long Short-Term Memory, Neural Computation, vol. 9, no.
   8, 1997, ss. 1735-1780 (cytowane w kontekście potencjalnych rozszerzeń).
23. MLflow: An open source platform for the machine learning lifecycle, Databricks Inc.,
   https://mlflow.org (dostęp: maj 2026).
24. imbalanced-learn: Toolbox for Imbalanced Datasets in Machine Learning, Lemaitre G.,
   Nogueira F., Aridas C. K., Journal of Machine Learning Research, vol. 18, 2017, ss. 1-5.
25. Pydantic: Data validation using Python type hints, Pydantic Services Inc.,
   https://pydantic.dev (dostęp: maj 2026).


26. CSIRT KNF, Lista ostrzeżeń przed niebezpiecznymi stronami internetowymi, Komisja
   Nadzoru                 Finansowego,                  Warszawa                 2024-2026,
   https://www.knf.gov.pl/dla_konsumenta/ostrzezenia_publiczne.
27. NASK PIB, Phishing - jak rozpoznać i zgłosić. Materiały edukacyjne kampanii Stop
   Cyberprzemocy, NASK Państwowy Instytut Badawczy, Warszawa 2023.
28. Rządowe Centrum Bezpieczeństwa, Raport o stanie bezpieczeństwa cyberprzestrzeni RP
   w 2023 roku, RCB, Warszawa 2024.
29. Najwyższa Izba Kontroli, Cyberbezpieczeństwo w jednostkach samorządu terytorialnego,
   raport pokontrolny, NIK, Warszawa 2023.
30. Komisja Nadzoru Finansowego, Komunikaty Departamentu Cyberbezpieczeństwa -
   zagrożenia phishingowe wobec klientów polskich banków, KNF, Warszawa 2022-2025,
   https://www.knf.gov.pl/dla_rynku/cyberbezpieczenstwo.
31. Związek Banków Polskich, Bankowość elektroniczna i cyberbezpieczeństwo. Raport
   roczny ZBP, Warszawa 2024.
32. UODO (Urząd Ochrony Danych Osobowych), Wytyczne dotyczące zgłaszania incydentów
   naruszenia ochrony danych osobowych, Warszawa 2022.
33. Agencja UE ds. Cyberbezpieczeństwa ENISA, ENISA Threat Landscape Report 2024,
   Ateny     2024,   https://www.enisa.europa.eu/topics/threat-risk-management/threats-and-
   trends.
34. Holland J. H., Adaptation in Natural and Artificial Systems, University of Michigan Press,
   Ann Arbor 1975.
35. Rumelhart D. E., Hinton G. E., Williams R. J., Learning representations by back-
   propagating errors, Nature, vol. 323, 1986, ss. 533-536.
36. Cybenko G., Approximation by superpositions of a sigmoidal function, Mathematics of
   Control, Signals, and Systems, vol. 2, no. 4, 1989, ss. 303-314.
37. Cox D. R., The Regression Analysis of Binary Sequences, Journal of the Royal Statistical
   Society. Series B (Methodological), vol. 20, no. 2, 1958, ss. 215-242.
38. Lewis D. D., Naive (Bayes) at forty: The independence assumption in information
   retrieval, w: Proceedings of the 10th European Conference on Machine Learning,
   Springer, Chemnitz 1998, ss. 4-15.



39. Domingos P., Pazzani M., On the Optimality of the Simple Bayesian Classifier under
   Zero-One Loss, Machine Learning, vol. 29, 1997, ss. 103-130.
40. Bergstra J., Bengio Y., Random Search for Hyper-Parameter Optimization, Journal of
   Machine Learning Research, vol. 13, 2012, ss. 281-305.
41. Breiman L., Friedman J. H., Olshen R. A., Stone C. J., Classification and Regression
   Trees, Wadsworth, Belmont 1984.
42. Marchal S., François J., State R., Engel T., PhishStorm: Detecting Phishing With
   Streaming Analytics, IEEE Transactions on Network and Service Management, vol. 11,
   no. 4, 2014, ss. 458-471.
43. Le H., Pham Q., Sahoo D., Hoi S. C. H., URLNet: Learning a URL Representation with
   Deep Learning for Malicious URL Detection, arXiv:1802.03162, 2018.





8. Wykaz tabel, rysunków i listingów

Tabele

   •   Tabela 1. Grupy cech URL ekstrahowanych przez PhishGuard.
   •   Tabela 2. Kategorie i liczba reguł w warstwie eksperckiej PhishGuard.
   •   Tabela 3. Wykaz endpointów API PhishGuard wraz z funkcjami.


Rysunki

   •   Rysunek 1. Architektura logiczna systemu PhishGuard.


Listingi

   •   Listing   1.     Implementacja     entropii     Shannona   dla        ciągu     znaków    URL
       (src/features/url_features.py).
   •   Listing 2. Konfiguracja meta-modelu w stacking ensemble (src/models/ensemble.py).
   •   Listing   3.    Przykład   definicji   reguły    wykrywającej        skrócone    adresy   URL
       (src/paradigms/rules/phishing_rules.yaml).
   •   Listing    4.      Przykład      metadanych       modelu        po      optymalizacji     GA
       (models/optimized/lr_metadata.json).







# Załącznik A — rysunki

![Rysunek A1. Architektura logiczna systemu PhishGuard (przycięty diagram, s. 25).](/Users/lukaszdrazek/Inzynierka/reports/figury2/diagram_architektura.png)

*Rysunek A1. Architektura logiczna systemu PhishGuard (przycięty diagram, s. 25).*

![Rysunek A2. Interfejs — zrzut ekranu (s. 48 oryginału).](/Users/lukaszdrazek/Inzynierka/reports/figury2/zrzut-000.png)

*Rysunek A2. Interfejs — zrzut ekranu (s. 48 oryginału).*

![Rysunek A3. Interfejs — zrzut ekranu (s. 49 oryginału).](/Users/lukaszdrazek/Inzynierka/reports/figury2/zrzut-001.png)

*Rysunek A3. Interfejs — zrzut ekranu (s. 49 oryginału).*

![Rysunek A4. Interfejs — zrzut ekranu (s. 50 oryginału).](/Users/lukaszdrazek/Inzynierka/reports/figury2/zrzut-002.png)

*Rysunek A4. Interfejs — zrzut ekranu (s. 50 oryginału).*



# Załącznik B — wybrane listingi kodu

**Miara rozbieżności (poprawiona normalizacja)** (`src/paradigms/aggregation/disagreement.py`):

```python
"""Cross-paradigm disagreement detection using normalized Shannon entropy.

Extends Phase 3 classifier disagreement approach to detect disagreements
between the three paradigms: ML ensemble, rule-based, and Bayesian.

Key differences from classifier disagreement:
- 3 paradigms vs 7 classifiers
- Votes take 2 classes (phishing/legitimate); max binary entropy = log2(2) = 1 bit
  (a 2:1 split scores ~0.918, a unanimous vote scores 0)
- Different probability scales (ML proba, rule score, Bayesian posterior)
"""

import numpy as np
from scipy.stats import entropy
from typing import Dict, List, Tuple

# Threshold for edge case detection (consistent with Phase 3)
PARADIGM_DISAGREEMENT_THRESHOLD = 0.7


def calculate_paradigm_disagreement(
    ml_prediction: str,
    ml_probability: float,
    rule_prediction: str,
    rule_probability: float,
    bayesian_prediction: str,
    bayesian_probability: float
) -> Dict:
    """Calculate disagreement across three paradigms.

    Args:
        ml_prediction: 'phishing' or 'legitimate' from ML ensemble
        ml_probability: Phishing probability from ML (0-1)
        rule_prediction: 'phishing' or 'legitimate' from rules
        rule_probability: Rule score (0-1)
        bayesian_prediction: 'phishing' or 'legitimate' from Bayesian
        bayesian_probability: Posterior phishing probability (0-1)

    Returns:
        Dict with:
            'score': Normalized entropy (0-1)
            'is_edge_case': True if score > threshold
            'vote_distribution': {'phishing': N, 'legitimate': M}
            'probability_variance': Variance across paradigm probabilities
            'disagreeing_paradigms': List of paradigms disagreeing with majority
            'probability_spread': Max - min probability across paradigms
    """
    predictions = {
        'ml_ensemble': ml_prediction,
        'rules': rule_prediction,
        'bayesian': bayesian_prediction
    }
    probabilities = [ml_probability, rule_probability, bayesian_probability]

    # Count votes
    votes = {}
    for paradigm, pred in predictions.items():
        votes[pred] = votes.get(pred, 0) + 1

    # Convert to binary for entropy calculation
    binary_preds = 
```

**Wagi paradygmatów (ML 0,5 / reguły 0,3 / Bayes 0,2)** (`src/paradigms/aggregation/weights.py`):

```python
"""Paradigm weight management for multi-paradigm aggregation.

Default weights: ML ensemble (0.5), Rules (0.3), Bayesian (0.2)
based on Phase 5 research recommendations.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ParadigmWeights:
    """Configurable weights for paradigm aggregation.

    Weights must sum to 1.0 and stay within bounds:
    - ML ensemble: 0.4-0.6 (dominant but not overwhelming)
    - Rules: 0.2-0.4 (interpretable contribution)
    - Bayesian: 0.1-0.3 (probabilistic complement)

    Attributes:
        ml_ensemble: Weight for ML ensemble prediction
        rules: Weight for rule-based system score
        bayesian: Weight for Bayesian posterior
    """

    ml_ensemble: float = 0.5
    rules: float = 0.3
    bayesian: float = 0.2

    def __post_init__(self):
        """Validate weights after initialization."""
        self._validate()

    def _validate(self):
        """Ensure weights sum to 1.0 and are in valid ranges."""
        total = self.ml_ensemble + self.rules + self.bayesian
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Weights must sum to 1.0, got {total:.4f}. "
                f"ML={self.ml_ensemble}, Rules={self.rules}, Bayesian={self.bayesian}"
            )

        # Bound validation (soft warning, not error)
        if not (0.4 <= self.ml_ensemble <= 0.6):
            import warnings
            warnings.warn(
                f"ML ensemble weight {self.ml_ensemble} outside recommended range [0.4, 0.6]"
            )
        if not (0.2 <= self.rules <= 0.4):
            import warnings
            warnings.warn(
                f"Rules weight {self.rules} outside recommended range [0.2, 0.4]"
            )
        if not (0.1 <= self.bayesian <= 0.3):
            import warnings
            warnings.warn(
                f"Bayesian weight {self.bayesian} outside recommended range [0.1, 0.3]"
            )

    def to_dict(self) -> Dict[str, float]:
        """Return weights as dictionary."""
        return {
            'ml_ensemble': self.ml_ensemble,
            'rules': self.rules,
            'bayesian': self.bayesian
        }

    @classmetho
```

