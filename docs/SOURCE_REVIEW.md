# Źródła przed KM4 — audyt 2026-09-23

To zapis sprawdzeń, nie deklaracja uzyskania licencji. **Nie aktywowano nowych redakcji**:
żaden kandydat nie ma jeszcze jednocześnie potwierdzonych pięciu bramek dla docelowego zastosowania.
Stan techniczny z tego środowiska nie jest gwarancją dostępności z runnera Actions.
Dane liczbowe: [source-checks-2026-09-23.json](source-checks-2026-09-23.json).

| redakcja | kraj / język | wynik kanałów (wpisy / świeże ≤48 h) | pozostała bramka |
|---|---|---|---|
| PBS News | US / en | headlines 20/20, politics 20/20 | zakres wykorzystania w produkcie, audyt ekstrakcji |
| Fox News | US / en | us 25/25, world 25/5 | warunki RSS i analizy/archiwizacji, audyt ekstrakcji |
| NPR | US / en | world 10/10 | zakres użycia i ograniczenia AI, audyt ekstrakcji |
| ProPublica | US / en | 20/2 | czwarty kandydat, inne tempo i zakres śledczy; CC BY-NC-ND nie jest bezwarunkową zgodą na produkt |
| Times of Israel | IL / en | odmowa według robots.txt | kanał, prawa, odróżnienie redakcji od blogów |
| Ynetnews | IL / en | 30/21 | warunki ograniczają RSS do prywatnego niekomercyjnego użycia |
| Haaretz | IL / en | brak potwierdzonego kanału | technika i prawa, bez obchodzenia paywalla |
| WAFA | PS / en | brak potwierdzonego kanału | oficjalna perspektywa instytucjonalna, nie niezależna redakcja |
| Ma’an | PS / ar | odmowa pobrania kandydata /feed/ | kanał, niezależność finansowania, prawa |
| Daily Sabah | TR / en | timeout robots.txt, kanału nie pobrano | ponowny test i prawa |
| Hürriyet Daily News | TR / en | world 100/24 | zakres wykorzystania i audyt ekstrakcji |
| Folha de S.Paulo | BR / pt | mundo 100/51 | prawa i ręczny audyt ram w portugalskim |
| Agência Brasil | BR / pt | 10/10 | polityka reprodukcji i treści partnerów, audyt ram PT |

Nowy Source z niepełną `verification` nie może mieć `active: true`. Pola `feed`, `fresh`,
`robots`, `usage`, `quality` muszą wszystkie wynosić `true`; decyzja i zakres wymagają notatki.
`usage=false` oznacza **brak potwierdzenia dopuszczalności w tym projekcie**, a nie orzeczenie,
że każda analiza danego materiału jest zabroniona. Nie utożsamiamy wnioskowania LLM z jego trenowaniem.

## Źródła warunków i decyzje

- [PBS RSS](https://www.pbs.org/newshour/about/pbs-news-rss-feeds),
  [warunki PBS](https://www.pbs.org/about/about-pbs/terms-of-use/): ograniczenia użycia komercyjnego.
  Oba kanały są jednym wydawcą, nie dwiema perspektywami.
- [Fox RSS](https://www.foxnews.com/story/foxnews-com-rss-feeds),
  [warunki ogólne](https://www.foxnews.com/terms-of-use): kanał ma odrębne zasady odsyłania,
  a regulamin ogólny ogranicza m.in. kopiowanie/archiwizację i użycie komercyjne.
  Nie uznano samego istnienia RSS za zgodę na cały proces produktu.
- [NPR](https://www.npr.org/about-npr/179876898/terms-of-use): ograniczenia personal/nonprofit,
  przekształcania i budowy/trenowania AI; wymaga wyjaśnienia zakres dla tego zastosowania.
- [ProPublica](https://www.propublica.org/steal-our-stories): CC BY-NC-ND i dodatkowe zasady
  przedruków. Redakcja śledcza nie zapewnia symetrycznej liczby publikacji dziennych.
- [Ynetnews RSS](https://www.ynetnews.com/articles/0,7340,L-3124381,00.html): prywatne,
  niekomercyjne użycie; inne zastosowanie wymaga odrębnego ustalenia. Edycja angielska jest wycinkiem debaty.
- [Times of Israel](https://www.timesofisrael.com/contact/): nie obchodzono odmowy robots.
  Odrębne blogi/opinie nie mogą być kodowane automatycznie jako wiadomości redakcji.
- [WAFA](https://english.wafa.ps/Home/AboutUs/1000): osobny kraj PS i perspektywa oficjalna.
  [Ma’an](https://www.maannews.net/) pozostaje kandydatem lokalnym. Al Jazeera pozostaje QA.
- [Folha RSS](https://www1.folha.uol.com.br/feed/): oficjalnie wskazany kanał Mundo;
  publiczna lista RSS nie rozstrzyga dopuszczalnego zakresu wykorzystania.
- [Agência Brasil — RSS](https://agenciabrasil.ebc.com.br/feed/),
  [polityka reprodukcji](https://agenciabrasil.ebc.com.br/sobre): użytek dziennikarski z atrybucją,
  zastosowania komercyjne kierowane do licencjonowania; materiały partnerów mogą mieć inne prawa.
- Dodatkowo sprawdzono [Reason](https://reason.com/terms-of-use/),
  [VOA](https://www.voanews.com/p/5338.html) i dostępne wskazania The Conversation:
  nie zastąpiono nimi koszyka bez testów kanału, pochodzenia poszczególnych materiałów i jakości.

Regulaminy PBS, Fox, NPR, ProPublica i Agência Brasil zostały także odczytane bezpośrednio
przez identyfikujący klient z respektowaniem robots; nie publikujemy ich pełnych kopii.
Nie kontaktowano się z wydawcami.

## Dotychczasowy koszyk i zakres

Pierwotne 10 źródeł pozostaje skonfigurowane. Rzeczywisty dodatkowy ingest w tej sesji dał
282 nowe materiały z 9 redakcji; kanał Spiegla został odrzucony przez kontrolę robots.
Pozostawiono go jako aktywny z widocznym błędem dostępności, aby pojedyncza próba nie stała się
nieodwracalną decyzją o koszyku. DE ma w tym przebiegu tylko jedną dostępną redakcję;
próg dwóch niezależnych redakcji pozostaje bez zmian.

Kanały ogólne i world/ausland nie są identycznymi mianownikami. Raport pokazuje sekcje,
język, pełny tekst/lead, liczby artykułów i rozpoznany gatunek; `unknown` pozostaje nieznanym gatunkiem.
Typ własności nie jest etykietą ideologiczną. Nie dodano El País América do BR.

## Następna czynność

Po potwierdzeniu zakresu wykorzystania: uruchomić `scripts/check_sources.py`, wykonać
kontrolę 3–5 materiałów każdej redakcji i ich sygnałów, zapisać datę i zakres aktywacji.
Dla BR potrzebny jest ręczny przegląd portugalskich ram — sam poprawny Unicode nie wystarcza.
Dopiero komplet bramek uprawnia do `active: true`. Minimum US 3 (lub jawnie 2), IL 2,
BR 2 pozostaje **niespełnionym kryterium odbioru**, nie deklarowanym wynikiem tej iteracji.
