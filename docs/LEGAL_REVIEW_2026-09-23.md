# Przegląd warunków źródeł — Paralaksa narracji

**Przegląd pomocniczy, nie porada prawna.** Stan sprawdzenia: **2026-09-23**. Ocena dotyczy opisanego w [zleceniu](LEGAL_REVIEW_BRIEF.md) łącznego procesu: regularnego pobierania RSS i, tam gdzie skonfigurowano `fulltext: true`, strony artykułu; prywatnej kopii tekstu; przesłania go do zewnętrznego API w celu analizy; oraz publicznego raportu. „Niekomercyjne” oznacza tutaj publiczny, automatyczny projekt bez opłat, **nie prywatny czytnik jednej osoby**. Wariant komercyjny oznacza przyszły produkt. Werdykt dotyczy **całego procesu w obecnej konfiguracji**, a nie samej możliwości napisania własnego komentarza i umieszczenia linku.

Skala: **dopuszczalne** — potwierdzono adekwatne uprawnienie dla całego procesu; **ryzyko** — istnieje klauzula, ale jej zastosowanie do części procesu lub wyjątku prawnego wymaga oceny; **niedozwolone** — jawne warunki wydawcy wykluczają istotny krok obecnego procesu bez dodatkowej zgody; **niejasne** — nie znaleziono miarodajnej klauzuli lub nie udało się odczytać aktualnych warunków. „Niedozwolone” opisuje treść znalezionych warunków, **nie ostateczny wyrok o wszystkich możliwych ustawowych wyjątkach**. `robots.txt` i działający RSS nie są licencją. Zaszyfrowanie kopii i brak treningu modeli nie tworzą automatycznie prawa do jej wykonania ani przesłania dostawcy API.

## Ramy oceny

- [Dyrektywa 2019/790, art. 3–4](https://eur-lex.europa.eu/eli/dir/2019/790/oj?locale=pl) rozróżnia badania określonych instytucji i ogólny wyjątek eksploracji tekstów oraz danych z legalnie dostępnych utworów; w tym drugim przypadku uprawniony może skutecznie zastrzec prawa. Polskie [art. 26²–26³ prawa autorskiego](https://isap.sejm.gov.pl/isap.nsf/download.xsp/WDU19940240083/U/D19940083Lj.pdf) trzeba oceniać wraz z zastrzeżeniami wydawcy, prawami do baz danych i konkretnymi kopiami. Samo prowadzenie projektu bez reklam nie czyni go badaniem instytucji uprawnionej do szczególnego wyjątku.
- W UK wyjątek dla text and data mining dotyczy [badań niekomercyjnych](https://www.gov.uk/guidance/exceptions-to-copyright); nie przyjmuję bez dodatkowej analizy, że publiczny codzienny radar i przekazanie pełnych tekstów dostawcom API spełniają tę przesłankę. W USA [fair use](https://www.copyright.gov/fair-use/) zależy od czterech czynników i kontekstu konkretnego użycia, a nie od limitu 15 słów.
- Własne omówienie faktów, tytuł, odnośnik i krótki uzasadniony cytat są osobnymi zagadnieniami od systematycznego pobierania, kopiowania, analizy i archiwizacji artykułów. Nie ma ogólnej bezpiecznej liczby słów. W źródłach zewnętrznych i agencyjnych trzeba sprawdzić także prawa podmiotów trzecich.
- Poniższe cytaty są celowo krótkie. Data dostępu do **każdego** podlinkowanego dokumentu w tej sekcji: **2026-09-23**. Gdy strona była niedostępna dla sprawdzenia, odnotowuję brak cytatu zamiast przypisywać jej treść na podstawie starszej notatki.

## Ocena 18 aktywnych źródeł

### 1. Rzeczpospolita (`rp`, PL) — niekomercyjne: **niejasne**; komercyjne: **niejasne**

W [regulaminie Gremi Media dotyczącym rp.pl](https://gremimedia.pl/regulamin-serwisow.html) nie znalazłem klauzuli upoważniającej do pobierania RSS, automatycznej analizy ani kopiowania tekstów do bazy/API. **Brak adekwatnego cytatu zezwalającego lub zakazującego tego procesu.** Regulamin dotyczy dostępu do serwisu i subskrypcji, nie jest licencją na monitoring. W konfiguracji `fulltext: false`, więc ryzyko jest mniejsze niż przy kopii artykułu, lecz lead/tytuł nadal jest analizowany przez API i raportowany. Własny komentarz z linkiem wymaga odrębnej oceny prawa cytatu i praw wydawcy prasowego. **Działanie:** zapytać wydawcę o RSS, automatyczną analizę leadów, API i retencję; nie wywodzić zgody z samego feedu.

### 2. Onet Wiadomości (`onet`, PL) — niekomercyjne: **ryzyko**; komercyjne: **ryzyko**

[Regulamin Onetu, rozdział IV](https://polityka-prywatnosci.onet.pl/regulamin.html): „Użytkownicy nie nabywają żadnych praw ani też nie uzyskują licencji do tych utworów lub baz danych”. Dalej dopuszcza tylko użytek przewidziany prawem bez wcześniejszej zgody i ogranicza pobieranie istotnej części bazy. Regulamin wymienia RSS jako sposób zapoznania się z materiałem, ale `fulltext: true`, prywatna baza i zewnętrzne API wychodzą poza zwykłe czytanie. Własny opis z linkiem nie jest tym samym co przedruk; żadna klauzula nie rozstrzyga tutaj wprost wnioskowania AI. **Działanie:** uzyskać potwierdzenie licencji na pobranie całego tekstu i codzienną analizę albo ocenić w polskiej jurysdykcji przesłanki ustawowego wyjątku przed dalszym archiwizowaniem.

### 3. Ukrinform (`ukrinform`, UA) — niekomercyjne: **ryzyko**; komercyjne: **ryzyko**

[Informacja o zasadach korzystania](https://www.ukrinform.ua/info/about_agency.html) wymaga: „гіперпосилання не нижче першого абзацу на «ukrinform.ua» — обов’язкові” (link nie niżej niż w pierwszym akapicie). Taka sama uwaga widnieje przy [zasadach serwisu](https://www.ukrinform.ua/info/reg_rules.html); przekłady zagranicznych mediów wymagają ponadto linku do oryginału. Własny raport z linkiem może odpowiadać wymogowi atrybucji, lecz nie znalazłem zezwolenia na codzienne kopiowanie pełnych tekstów (`fulltext: true`), ich przesyłanie do AI ani przechowywanie. Oznaczenie przez agencję „wszelkie prawa zastrzeżone” nie wyklucza ustawowych wyjątków, ale samo też nie daje licencji. **Działanie:** pytanie o analizę i prywatne kopie; przy materiałach tłumaczonych przez Ukrinform rozważyć podwójne źródłowanie.

### 4. Ukraińska Prawda (`pravda_ua`, UA) — niekomercyjne: **ryzyko**; komercyjne: **niedozwolone**

[Zasady redakcji](https://www.pravda.com.ua/rules/): „Забороняється будь-яке комерційне використання інформації” (zakazane wszelkie komercyjne wykorzystanie informacji). Pozwalają określonym wydaniom internetowym na użycie informacji przy widocznym hiperłączu i wskazaniu źródła; nie jest jasne, czy prywatna baza plus dwa zewnętrzne API mieszczą się w tej zgodzie. Publiczny raport niekomercyjny może korzystać z własnego komentarza i linków, ale obecne `fulltext: true` wymaga doprecyzowania zakresu. **Działanie:** wyjaśnić automatyczne pobieranie, przekazanie AI i przechowanie; przed wersją płatną uzyskać odrębną licencję.

### 5. Tagesschau (`tagesschau`, DE) — niekomercyjne: **niedozwolone**; komercyjne: **niedozwolone**

[Warunki kanału RSS](https://www.tagesschau.de/rssfeed-ts-104.html): „Die Inhalte dürfen nicht archiviert werden.” Serwis dopuszcza zastosowanie RSS w niekomercyjnym serwisie internetowym z atrybucją i bez przekazania danych osobom trzecim, ale obecny proces zapisuje tekst w trwałej bazie, przesyła go do zewnętrznych API i ma `fulltext: true`. Dla produktu komercyjnego ograniczenie jest dodatkowo wyraźne. Własny komentarz z linkiem jest odrębny od kopiowania feedu. **Działanie:** zgoda obejmująca przechowywanie i API albo wyłącznie linki i analiza po uzgodnieniu zakresu; zapytać przez [kontakt Tagesschau](https://www.tagesschau.de/kontakt).

### 6. Der Spiegel (`spiegel`, DE) — niekomercyjne: **ryzyko**; komercyjne: **niedozwolone**

[Warunki udzielanych licencji grupy Spiegel](https://gruppe.spiegel.de/syndication/anfrage): „Die Verwendung des Materials für jede Art von Training oder Nutzung für KI-Modelle ist unzulässig.” Ta klauzula występuje w **warunkach licencjonowania materiałów**, a nie w odrębnym, potwierdzonym regulaminie publicznego RSS, więc nie przypisuję jej automatycznie każdemu pobraniu RSS. Warunki licencyjne ograniczają też bazy danych i wskazują na pisemną zgodę oraz wynagrodzenie przy eksploatacji komercyjnej. `fulltext: false`, ale lead nadal trafia do zewnętrznego modelu. **Działanie:** zapytać przez [formularz licencyjny](https://gruppe.spiegel.de/syndication/anfrage), czy dozwolony jest taki właśnie tryb wnioskowania i retencja metadanych; komercyjnie negocjować wyraźny wyjątek dla AI.

### 7. BBC News (`bbc`, UK) — niekomercyjne: **niedozwolone**; komercyjne: **niedozwolone**

[Oficjalne warunki BBC, sekcje 8 i 15, wersja PDF dostępna przy badaniu](https://downloads.bbc.co.uk/usingthebbc/bbc_terms_of_use_31March2022english.pdf): „Anything plucked from our services to develop or train artificial intelligence or to do computer analysis” wymaga pozwolenia. Dopuszczenie umieszczenia RSS na stronie z atrybucją nie daje licencji na analizę komputerową, kopię pełnych tekstów (`fulltext: true`) ani zewnętrzne API. Wykorzystanie biznesowe RSS wymaga odrębnej zgody. **Działanie:** uzyskać od BBC licencję na computer analysis, RSS, archiwizację i dostawców API; sprawdzić aktualność przytoczonej wersji PDF u BBC.

### 8. The Guardian (`guardian`, UK) — niekomercyjne: **niedozwolone**; komercyjne: **niedozwolone**

[Warunki Guardian, sekcja 3](https://www.theguardian.com/help/terms-of-service) zastrzegają bez uprzedniej pisemnej zgody użycie „for any text and data aggregation, analysis or mining purposes”. Ta sama sekcja obejmuje wprost zastosowania AI do generowania i syntezy, boty, tworzenie baz oraz komercjalizację. Warunki obejmują także RSS i stwierdzają, że `robots.txt` nie jest zgodą. Obecny proces jest dokładnie analizą przekazów w bazie, więc samo rozróżnienie **wnioskowania od treningu** go nie usuwa. **Działanie:** uzyskać licencję na monitoring/AI albo pominąć to źródło w takim procesie; [licensing@theguardian.com](mailto:licensing@theguardian.com); dla usługi monitoringu wydawca wskazuje także NLA Media Access.

### 9. Al Jazeera English (`aljazeera`, QA) — niekomercyjne: **niedozwolone**; komercyjne: **niedozwolone**

[Aktualne warunki serwisu](https://www.aljazeera.com/terms-and-conditions) zakazują bez upoważnienia „any unauthorised copying, text or data mining, or web scraping”; obejmują też automatyczne analizowanie treści w celu wyłapania trendów, korelacji i wzorców. To odpowiada celowi Paralaksy, niezależnie od braku opłat i od tego, czy model jest trenowany. `fulltext: true` zwiększa zakres kopiowania. **Działanie:** uzyskać wyraźną pisemną zgodę na RSS, analizę wzorców, prywatne kopie i przesłanie do API przez dział prawny wskazany na [oficjalnej stronie sieci Al Jazeera](https://www.aljazeera.com/eu-eea-regulatory): `legal@aljazeera.net`.

### 10. CGTN (`cgtn`, CN) — niekomercyjne: **ryzyko**; komercyjne: **ryzyko**

[Warunki CGTN](https://www.cgtn.com/terms-of-use.html) podają: „you may not modify any of the materials and you may not copy, distribute, transmit”. Ten zapis ma zastrzeżenie dla właściwych wyjątków prawnych, a wyszukiwarka nie dała dostępu do pełnego dokumentu w czasie badania; nie znalazłem adekwatnego zezwolenia na systematyczny RSS, `fulltext: true`, zewnętrzną analizę AI ani prywatną kopię. Krótki własny komentarz nie jest równoważny przedrukowi, ale nie wyjaśnia uprawnień do wejściowych tekstów. **Działanie:** potwierdzić pełne warunki i możliwość licencji bezpośrednio u wydawcy przed wykorzystaniem w płatnej usłudze; ponowić ręczną kontrolę dokumentu.

### 11. PBS News (`pbs`, US) — niekomercyjne: **ryzyko**; komercyjne: **niedozwolone**

[Warunki PBS](https://www.pbs.org/about/about-pbs/terms-of-use/) ograniczają „use or exploit any Information for commercial purposes”; [lista kanałów NewsHour](https://www.pbs.org/newshour/about/pbs-news-rss-feeds) potwierdza ich istnienie, nie licencję na pełne teksty. `fulltext: true`, prywatna kopia, zewnętrzne API i publiczna analiza nie są tam jednoznacznie dozwolone. Prawa konkretnego programu mogą przysługiwać jego producentowi. **Działanie:** zapytać właściwy zespół [PBS NewsHour](https://www.pbs.org/newshour/about/contact-us), wprost `licensing@newshour.org`, o aktualny i przyszły model wykorzystania.

### 12. Fox News (`fox`, US) — niekomercyjne: **niedozwolone**; komercyjne: **niedozwolone**

[Oficjalne zasady RSS](https://www.foxnews.com/story/foxnews-com-rss-feeds) mówią: „FOX offers free headlines for personal, non-commercial use”. Publiczny automatyczny radar nie jest osobistym czytnikiem RSS; ponadto obecne `fulltext: true` pobiera ze strony więcej niż nagłówki. Zasady wymagają bezpośredniego odnośnika do artykułu, ale to wymóg dystrybucji RSS, nie zgoda na przechowywanie artykułów i analizę w API. **Działanie:** ubiegać się o licencję obejmującą zastosowanie publiczne/automatyczne i przyszły produkt; do czasu odpowiedzi nie utożsamiać „non-commercial” z „personal”.

### 13. NPR (`npr`, US) — niekomercyjne: **niejasne**; komercyjne: **niejasne**

Oficjalny [adres regulaminu NPR](https://www.npr.org/about-npr/179876898/terms-of-use) był podczas badania niedostępny dla narzędzia (odmowa `robots.txt`); nie potwierdziłem bieżącej klauzuli dotyczącej AI, RSS, archiwum i wydawania raportu. **Brak zweryfikowanego cytatu z aktualnego regulaminu**; uwaga o AI ze starszego audytu repozytorium nie stanowi w tej ocenie dowodu. Nie przenoszę warunków sklepu NPR, podcastów ani stacji członkowskich na serwis informacyjny. `fulltext: true` oraz API wymagają wyjaśnienia. **Działanie:** uzyskać tekst aktualnych warunków albo pisemne stanowisko przez [oficjalny kontakt NPR](https://help.npr.org/) i dopiero wtedy przypisać werdykt.

### 14. ProPublica (`propublica`, US) — niekomercyjne: **ryzyko**; komercyjne: **ryzyko**

[Zasady „Steal Our Stories”](https://www.propublica.org/steal-our-stories): „You can’t republish our material wholesale, or automatically”. Linkowana [licencja CC BY-NC-ND 3.0 US](https://creativecommons.org/licenses/by-nc-nd/3.0/us/) dotyczy określonego przedruku materiałów, a nie automatycznie wszystkich analiz własnym tekstem. Dlatego nie nazywam własnej analizy „zakazaną pochodną” ani licencji CC pełną zgodą na systematyczne pobieranie, `fulltext: true`, zewnętrzne API i bazę. Licencja nie obejmuje komercyjnej redystrybucji tekstów; dla produktu potrzebne są uzgodnienia. **Działanie:** poprosić o pisemne stanowisko dotyczące monitoringu i wnioskowania API przez [kontakt ProPublica](https://www.propublica.org/contact/), odróżniając to od przedruku.

### 15. The Jerusalem Post (`jpost`, IL) — niekomercyjne: **niedozwolone**; komercyjne: **niedozwolone**

[Warunki serwisu, część RSS](https://www.jpost.com/landedpages/termsofservice.aspx): „do not crawl or otherwise parse, display or publish any content from the Website which was not presented in the RSS feed”. Wydawca dopuszcza zbudowanie aplikacji na **samym feedzie**, co jest wartościową, węższą ścieżką, ale obecna konfiguracja ma `fulltext: true`, a tekst spoza RSS jest pobierany i analizowany. Warunki wskazują ponadto użycie osobiste i niekomercyjne oraz ograniczenia skryptów wobec serwisu. Osobna [strona o prawach autorskich](https://www.jpost.com/landedpages/copyright.aspx) zabrania też przechowywania materiałów w systemie wyszukiwawczym bez pozwolenia i wskazuje osobne prawa AP. **Działanie:** przed kontynuacją takiego procesu uzyskać rozszerzoną licencję albo osobno ocenić wariant feed-only; [redaktor ds. zezwoleń](mailto:syndication@jpost.com).

### 16. Al-Quds (`alquds_ps`, PS) — niekomercyjne: **niedozwolone**; komercyjne: **niedozwolone**

[Warunki w języku arabskim](https://www.alquds.com/ar/terms): „يسمح لك باستخدام المحتوى للأغراض الشخصية غير التجارية فقط” (treść wyłącznie do osobistego użytku niekomercyjnego). [Wersja angielska](https://www.alquds.com/en/terms) potwierdza to ograniczenie. Publiczny automatyczny raport i `fulltext: true` nie są osobistym korzystaniem. Strona opisuje własną politykę korzystania z AI przez redakcję; nie jest to zgoda dla podmiotów trzecich na wysyłanie artykułów do modeli. **Działanie:** wyraźna zgoda na RSS, pełny tekst, API i archiwizację przez [formularz Al-Quds](https://www.alquds.com/ar/contacts/new?language=ar).

### 17. Folha de S.Paulo (`folha`, BR) — niekomercyjne: **ryzyko**; komercyjne: **niedozwolone**

[Warunki Folha](https://www1.folha.uol.com.br/paineldoleitor/2020/04/termos-e-condicoes-de-uso-folha-de-spaulo.shtml): „É vedada a reprodução total ou parcial, de qualquer conteúdo” bez pisemnej zgody Folhapress; dalej ograniczają użycie serwisu do niekomercyjnego. Czy techniczne kopie dla własnej analizy (również w zewnętrznym API) mieszczą się w ewentualnym ustawowym wyjątku, wymaga szczególnej oceny; oficjalna [lista RSS](https://www1.folha.uol.com.br/feed/) tego nie rozstrzyga. `fulltext: true` i przyszły produkt przekraczają węższy scenariusz czytania feedu. **Działanie:** wystąpić do Folhapress o monitoring, przechowywanie, AI i komercyjne użycie; przeprowadzić osobno analizę praw w Brazylii i prawa właściwego dla usługi.

### 18. Agência Brasil (`agenciabrasil`, BR) — niekomercyjne: **ryzyko**; komercyjne: **ryzyko**

[Zasady reprodukcji na stronie „Sobre”](https://agenciabrasil.ebc.com.br/sobre) zawierają zwrot „Para reproduções com fins comerciais” i kierują takie wnioski do `licenciamento@ebc.com.br`. W chwili sprawdzenia wyszukiwarka udostępniała oficjalny fragment, natomiast bezpośrednie otwarcie strony zakończyło się błędem czasu; pełną aktualną treść trzeba potwierdzić u EBC. Materiały agencyjne własne mogą mieć inne zasady niż zdjęcia i depesze partnerów, na których stronach występuje oznaczenie „É proibida a reprodução deste conteúdo”. Własny raport z linkami nie jest komercyjnym przedrukiem, ale brak potwierdzenia automatycznych kopii (`fulltext: true`) i przesyłania do AI. **Działanie:** potwierdzić reguły dla tekstów własnych oraz wykluczenie treści partnerów; uzgodnić przyszłą licencję pod `licenciamento@ebc.com.br`.

## Zestawienie

| Źródło | Teraz: publiczne bez opłat | Produkt komercyjny | Główna przeszkoda obecnej konfiguracji |
|---|---|---|---|
| rp | niejasne | niejasne | brak klauzuli o automatycznej analizie leadów |
| onet | ryzyko | ryzyko | brak licencji na kopie/eksplorację poza wyjątkami |
| ukrinform | ryzyko | ryzyko | wymagane linki; niejasne archiwum i AI |
| pravda_ua | ryzyko | niedozwolone | zakaz komercyjnego wykorzystania informacji |
| tagesschau | niedozwolone | niedozwolone | zakaz archiwizacji i przekazania danych RSS |
| spiegel | ryzyko | niedozwolone | warunki licencjonowania wykluczają KI |
| bbc | niedozwolone | niedozwolone | BBC wymaga pozwolenia na computer analysis |
| guardian | niedozwolone | niedozwolone | wyraźne ograniczenie analizy, AI i botów |
| aljazeera | niedozwolone | niedozwolone | wyraźny zakaz automatycznego data mining |
| cgtn | ryzyko | ryzyko | kopiowanie i zakres wyjątków bez potwierdzenia |
| pbs | ryzyko | niedozwolone | brak uprawnienia do pełnych tekstów, zakaz komercyjny |
| fox | niedozwolone | niedozwolone | RSS tylko personal/non-commercial |
| npr | niejasne | niejasne | aktualna klauzula niedostępna |
| propublica | ryzyko | ryzyko | CC dotyczy przedruku, automatyczny przedruk zabroniony |
| jpost | niedozwolone | niedozwolone | obecny pełny tekst spoza RSS zabroniony |
| alquds_ps | niedozwolone | niedozwolone | dozwolony tylko osobisty użytek |
| folha | ryzyko | niedozwolone | reprodukcja wymaga pisemnej zgody |
| agenciabrasil | ryzyko | ryzyko | mieszane prawa materiałów i zakres licencji komercyjnej |

## Zablokowani kandydaci: legalna droga do rozmowy

- **Times of Israel:** [strona kontaktowa](https://www.timesofisrael.com/contact/) pozwala linkować, ale mówi, by poza nagłówkiem i podtytułem nie kopiować treści; kieruje zainteresowanych syndykacją do formularza redakcji. [Opis programu syndykacji](https://www.timesofisrael.com/times-of-israel-syndication-meet-your-newest-writers/) potwierdza istnienie oferty płatnej, lecz **przedruk nie oznacza automatycznie licencji na RSS/TDM/API**. Odmowa `/feed/` w `robots.txt` pozostaje blokadą techniczną i nie jest obchodzona. Adres: [formularz redakcji](https://www.timesofisrael.com/contact/); starsza strona syndykacji podaje także `syndication@timesofsrael.com` — domena wygląda nietypowo, więc preferowany jest formularz.
- **Ma’an:** w trakcie badania **nie znalazłem oficjalnej, aktualnej oferty licencji na automatyczne pobieranie i AI ani miarodajnej klauzuli do zacytowania**. W repozytorium odnotowano zarówno niedostępność przez Cloudflare, jak i odmowę pobrania `/feed/` zgodnie z `robots.txt`; żadnej blokady nie należy obchodzić. [Oficjalny wykaz kontaktów palestyńskiego biura prasowego](https://pmo.pna.ps/en/Article/4794/media-contacts) wskazuje `news@maannews.net`; można tam zapytać o licencjonowany feed/API, zasady retencji i analizę przez zewnętrzny model. Bez odpowiedzi: **niejasne**, bez aktywacji.

## Do kogo pisać w pierwszej kolejności

To są **adresy do ewentualnego kontaktu**, nie wysłane wiadomości ani uzyskane zgody. W pierwszym piśmie opisać cały proces z briefu: liczbę zapytań, RSS i pełny tekst, prywatną retencję oraz okres usuwania, dostawców DeepSeek/Anthropic, wnioskowanie bez treningu, zaszyfrowany backup w publicznym Release, publiczny raport z własnym tekstem i linkami, a także przyszły model płatny. Prosić o wyraźne odpowiedzi osobno dla obu wariantów.

| Priorytet | Źródła | Zweryfikowana droga kontaktu |
|---|---|---|
| Pilne: wyraźne zakazy lub wymagana zgoda | Guardian | [licensing@theguardian.com](mailto:licensing@theguardian.com) |
| Pilne | BBC | [warunki i ścieżka licencji BBC](https://downloads.bbc.co.uk/usingthebbc/bbc_terms_of_use_31March2022english.pdf) |
| Pilne | Al Jazeera | [legal@aljazeera.net](mailto:legal@aljazeera.net) — dział prawny wskazany na [oficjalnej stronie sieci](https://www.aljazeera.com/eu-eea-regulatory) |
| Pilne | Tagesschau | [kontakt Tagesschau](https://www.tagesschau.de/kontakt) |
| Pilne | Fox | [pomoc Fox News](https://help.foxnews.com/hc/en-us) — wyraźnie pytać o tekst/RSS; znaleziony adres `ArchiveSales@foxnews.com` dotyczy materiału filmowego, więc nie zakładam jego właściwości dla feedu |
| Pilne | Jerusalem Post, Al-Quds | [syndication@jpost.com](mailto:syndication@jpost.com) — [oficjalna strona zezwoleń](https://www.jpost.com/landedpages/copyright.aspx); [formularz Al-Quds](https://www.alquds.com/ar/contacts/new?language=ar) |
| Dalej: ustalenie zakresu | Spiegel, Folha | [licencjonowanie Spiegel](https://gruppe.spiegel.de/syndication/anfrage), [warunki Folha i Folhapress](https://www1.folha.uol.com.br/paineldoleitor/2020/04/termos-e-condicoes-de-uso-folha-de-spaulo.shtml) |
| Dalej | NPR, PBS, ProPublica | [NPR](https://help.npr.org/), [PBS NewsHour — licensing@newshour.org](https://www.pbs.org/newshour/about/contact-us), [ProPublica](https://www.propublica.org/contact/) |
| Dalej | Onet, rp, Ukrinform, Ukraińska Prawda, CGTN, Agência Brasil | [Onet/RASP — adres i telefon](https://polityka-prywatnosci.onet.pl/regulamin.html), [Gremi Media — adres wydawcy](https://gremimedia.pl/kontakt.html), [kontakt Ukrinform](https://www.ukrinform.ua/info/contacts.html), [Ukraińska Prawda — upeng@pravda.ua](https://www.pravda.com.ua/eng/supportus/), [CGTN — warunki i dane wydawcy](https://www.cgtn.com/terms-of-use.html), [licenciamento@ebc.com.br](mailto:licenciamento@ebc.com.br). Dla rp i CGTN kanał licencyjny wymaga jeszcze potwierdzenia. |
| Kandydaci z blokadą | Times of Israel, Ma’an | [formularz ToI](https://www.timesofisrael.com/contact/), [news@maannews.net](mailto:news@maannews.net) |

**Decyzja do właściciela:** pierwszeństwo ma wyjaśnienie źródeł, których literalne warunki kolidują już z dzisiejszym procesem; lista „aktywnych” jest stanem technicznym, nie potwierdzeniem uprawnienia. Nie zmieniono konfiguracji ani działania systemu na podstawie tego przeglądu.
