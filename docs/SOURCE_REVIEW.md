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

## Aktywacja 2026-09-23 (decyzja właściciela, po realnym audycie jakości)

Właściciel świadomie zdecydował: aktywować USA/Brazylię teraz, akceptując brak formalnego audytu
praw wydawcy zamiast czekać na niego, **pod warunkiem** wykonania od razu audytu jakości ekstrakcji
(nie tylko technicznej dostępności kanału) — bo i tak trzeba go zrobić. To odstępstwo od zasady
„komplet bramek" wyżej w tym pliku jest jawne, udokumentowane per źródło w `config/sources.yaml`
(pole `verification.risk_accepted`), nie cichym obniżeniem progu.

Realny audyt: ingest 229 artykułów z pełnym tekstem (8 redakcji: pbs, fox, npr, propublica, folha,
agenciabrasil + dwaj nowi kandydaci IL/PS niżej), ekstrakcja produkcyjnym modelem (DeepSeek V4-Pro) na
próbce 40 artykułów (round-robin, ~5/redakcję), koszt $0.098. Ręczny przegląd 3 sygnałów na redakcję:
trafne przypisania aktorów, spójne ramy, streszczenia zgodne z treścią — bez zastrzeżeń jakościowych.

**Aktywowane** (`active: true` w `config/sources.yaml`, `fulltext: true` — próba pokazała, że
pełny tekst pobiera się bez przeszkód, więc nie ma powodu zostawiać lead-only):

| redakcja | kraj | sygnałów/5 art. (próbka) | uwaga |
|---|---|---|---|
| PBS News | US | 11 | — |
| Fox News | US | 20 | — |
| NPR | US | 18 | warunki wprost zabraniają budowy/trenowania AI bez zgody — to nie jest trenowanie, ale ryzyko interpretacyjne pozostaje, zaakceptowane przez właściciela |
| ProPublica | US | 20 | CC BY-NC-ND — ryzyko zaakceptowane |
| Folha de S.Paulo | BR | 25 | portugalski, ramy czytelne (np. ustawa o zasłanianiu twarzy w Portugalii) |
| Agência Brasil | BR | 11 | portugalski, ramy czytelne |

**Nowi kandydaci IL/PS** (zamienniki za zablokowanych — patrz niżej), sprawdzeni technicznie
i jakościowo, ale **pozostają `active: false`**: właściciel nie podjął jeszcze decyzji o
aktywacji tych dwóch, w przeciwieństwie do USA/BR.

| redakcja | kraj/język | zamiennik za | wynik techniczny | wynik jakości (5 art.) |
|---|---|---|---|---|
| The Jerusalem Post (`jpost`) | IL/en | timesofisrael (robots.txt `Disallow: /feed/`), ynetnews (kanał nieświeży) | RSS 10/26 świeżych ≤48h, robots.txt bez blokady dla naszego UA | 14 sygnałów, spójne, bez zastrzeżeń |
| Al-Quds (`alquds_ps`) | PS/ar | maan (Cloudflare), wafa (brak RSS) | RSS 30/30 świeżych ≤48h, robots.txt `Allow: /` | 17 sygnałów (z 21 wygenerowanych; 4 odrzucone przez błąd walidatora — patrz niżej), spójne, model poprawnie odróżnił twierdzenie źródła izraelskiego od faktu |

**Efekt uboczny audytu — błąd znaleziony i naprawiony.** Arabskie przedrostki (spójniki/przyimki
doklejane bez spacji, np. „و" = „i") powodowały, że nasz sprawdzian dosłowności cytatu
(`is_verbatim`) odrzucał poprawne cytaty modelu, bo tokenizator `\w+` nie rozdziela przedrostka od
rdzenia. 4/21 sygnałów z al-quds odrzuconych z tego powodu, nie z powodu halucynacji. Naprawione
w `src/paralaksa/extract/schema.py` (commit `c34f4e7`), z testami na tych rzeczywistych przypadkach.
Bez tej poprawki każde źródło arabskojęzyczne miałoby systemowo zaniżoną liczbę sygnałów.

**Sprawdzone i odrzucone alternatywy** (nie dodane do configu): Israel Hayom — ochrona Akamai
blokuje nawet pobranie `robots.txt` (HTTP 403), tak jak Ma'an blokuje Cloudflare; Palestine
Chronicle — trwałe HTTP 429 (przeciążenie/throttling) przy dwóch próbach w odstępie kilku sekund;
PNN (Palestine News Network) — robots.txt wprost zabrania `*/feed` i `*/rss`; Mondoweiss — kanał
techniczny działa (5/10 świeżych ≤48h), ale to redakcja amerykańska pisząca o Palestynie
(advocacy media), nie głos palestyńskiej prasy krajowej — nie pasuje do definicji `editorial_country=PS`.

**Aktualizacja tego samego dnia:** właściciel zdecydował aktywować także `jpost` (IL) i `alquds_ps` (PS)
na tych samych zasadach (zaakceptowane ryzyko praw, audyt jakości wykonany wyżej). Test `plx ingest`
z konfiguracji: jpost 26 nowych, alquds_ps 30 nowych, bez błędów. Aktywnych źródeł: 18, krajów: 10.
Formalny przegląd warunków wszystkich 18 źródeł zlecony osobno: `docs/LEGAL_REVIEW_BRIEF.md`.
