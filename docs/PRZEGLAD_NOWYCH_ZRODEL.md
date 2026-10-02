# Przegląd nowych źródeł: FR, HU, IR, JP, SA — 2026-10-02

Tylko przegląd. Nic nie dodano do `config/sources.yaml`, nic nie zapisano do bazy. Test: `PoliteClient` z naszym UA
(`paralaksa-narracji/0.1`, respektuje robots RFC 9309), `parse_feed`, `fetch_fulltext` (trafilatura, limit 400 słów) na pierwszych
3 artykułach z kanału. „słowa” = długość wyciągniętego tekstu (limit 400; ≤60 = tylko lead/paywall). Liczba wpisów to rozmiar kanału
w chwili testu, nie dzienna produkcja (większość kanałów to ostatnie 1–3 doby).
Profil redakcji to ocena z wiedzy ogólnej, do potwierdzenia przez człowieka (pole `ownership` w YAML do uzupełnienia).

## Francja (FR) — przechodzi, 3 źródła

| źródło | kanał | robots/art. | wpisy | słowa (3 art.) | profil / ryzyka |
|---|---|---|---|---|---|
| France 24 (EN) | `https://www.france24.com/en/rss` | ok | 24 | 58, 56, 327 | publiczne (France Médias Monde); część wpisów to zapowiedzi programów TV, krótkie |
| RFI (EN) | `https://www.rfi.fr/en/rss` | ok | 19 | 400×3 | publiczne (ten sam wydawca co France 24: **jedna `publisher_group`**) |
| Le Figaro | `https://www.lefigaro.fr/rss/figaro_actualites.xml` | ok | ~20 | 400×3 | prywatne (Dassault), centroprawicowe; po francusku; część treści paywall, ale 3/3 próbek pełne |
| Le Monde (EN) | `https://www.lemonde.fr/en/rss/une.xml` | ok | 18 | 46×3 | prywatne, centrolewicowe; **paywall**: tylko lead |
| Libération | `…/arc/outboundfeeds/rss-all/collection/accueil-une/` | ok | 20 | 0×3 | lewicowe; **paywall**, brak tekstu |
| Mediapart | `https://www.mediapart.fr/articles/feed` | ok | 10 | 400×3 (do weryfikacji, czy to nie fragment przed paywallem) | niezależne, śledcze, subskrypcyjne; mało wpisów dziennie |
| francetvinfo | `https://www.francetvinfo.fr/titres.rss` | ok | 31 | 400×3 | publiczne (France Télévisions) |
| 20 Minutes | `https://www.20minutes.fr/feeds/rss-une.xml` | ok | 30 | 400, 400, 280 | prywatne, popularne, bezpłatne |
| La Croix | `https://www.la-croix.com/RSS` | ok | 50 | 400, 400, 74 | katolickie, prywatne |
| Euronews (EN) | `https://www.euronews.com/rss?format=mrss` | ok | 50 | 400, 400, 271 | paneuropejskie, nie francuskie w sensie redakcyjnym (siedziba Lyon, własność portugalsko-egipska); odradzane jako „głos Francji” |
| Humanité | `https://www.humanite.fr/feed` | **blokuje** | — | — | odpada |
| Le Point | `https://www.lepoint.fr/rss.xml` | **blokuje** | — | — | odpada |

**Rekomendacja FR:** Le Figaro (prawica, pełny tekst) + francetvinfo (publiczne) + RFI EN (publiczne, międzynarodowe; ale to samo
`publisher_group` co France 24, więc nie liczy się jako drugi wydawca). Opcjonalnie 20 Minutes jako popularne prywatne. Le Monde i
Libération: tylko lead, wartość ograniczona (jak Haaretz); lewą stronę lepiej reprezentuje Mediapart po sprawdzeniu pełnotekstu,
albo Le Monde z samym leadem.
Dla progu SPEC (≥2 wydawców): Figaro + francetvinfo wystarczą.

## Węgry (HU) — przechodzi, 3 źródła (węgierski)

| źródło | kanał | robots/art. | wpisy | słowa | profil / ryzyka |
|---|---|---|---|---|---|
| Telex | `https://telex.hu/rss` | ok | 50 | 318, 152, 293 | niezależne (założone przez ekipę Indexu 2020), krytyczne wobec Fidesz |
| HVG | `https://hvg.hu/rss` | ok | 60 | 297, 400, 367 | prywatne, liberalno-opozycyjny tygodnik; metered paywall dla części |
| Index | `https://index.hu/24ora/rss/` | ok | 51 | 400, 400, 138 | prywatne, od 2020 zwrot w stronę kręgu prorządowego (do Fidesz) |
| Magyar Nemzet | `https://magyarnemzet.hu/feed` | ok | 25 | 58, 96, 400 | prorządowe wobec dotychczasowej koalicji Fidesz (Mediaworks/KESMA); część artykułów krótka |
| Portfolio | `https://www.portfolio.hu/rss/all.xml` | ok | 20 | 400×3 | biznesowe, neutralne; wąski zakres tematów |
| Daily News Hungary (EN) | `https://dailynewshungary.com/feed/` | ok | 20 | 373, 400, 400 | prywatne, angielskie, tabloidowe/lokalne |
| Hungary Today (EN) | `…/feed/` | **blokuje** | — | — | odpada (kojarzone z kręgiem prorządowym) |
| Hungarian Conservative | `…/feed/` | **blokuje** (+ timeouty) | — | — | odpada |
| hirado.hu (MTVA) | `https://hirado.hu/feed/` | HTTP 500 | — | — | odpada (media publiczne, pod kontrolą rządu; kanał niedziałający) |
| kormany.hu | — | 404 | — | — | brak kanału |

Uwaga kontekstowa: kanały wskazują, że po wyborach 2026 władza się zmieniła (Magyar jako premier, śledztwa wobec Orbána), więc
„prorządowy/opozycyjny” zależy od daty; w YAML opisywać właścicielem i linią redakcyjną, nie rolą wobec obecnego rządu.

**Rekomendacja HU:** Telex (niezależne) + Index (prywatne, rząd. krąg) + Magyar Nemzet (prorządowe wobec Fidesz); HVG jako
czwarte, jeśli chcemy więcej głosu liberalnego. Ryzyko: język węgierski wymaga sprawdzenia, czy ekstrakcja go obsługuje
(`src/paralaksa/extract`, brak sprawdzenia w tym przeglądzie).

## Iran (IR) — przechodzi warunkowo, 3 źródła

| źródło | kanał | robots/art. | wpisy | słowa | profil / ryzyka |
|---|---|---|---|---|---|
| Tehran Times | `https://www.tehrantimes.com/rss` | ok | 30 | 400, 77, 107 | angielski, prorządowe (instytucja powiązana z Organizacją Kultury i Komunikacji Islamskiej) |
| Mehr News (EN) | `https://en.mehrnews.com/rss` | ok | 30 | 400, 58, 140 | agencja półpaństwowa, linia IRGC-kompatybilna; język agresywny |
| IRNA (EN) | `https://en.irna.ir/rss` | ok (timeout robots w teście) | 30 | 12×3 | agencja państwowa; **pełny tekst nie wychodzi** (tylko lead) |
| ISNA (EN) | `https://en.isna.ir/rss` | ok | 30 | 12×3 | agencja półpaństwowa; j.w. |
| Iran International (EN) | `https://iranintl.com/en/feed` | ok | 50 | 400×3 | emigracyjna, londyńska (od 2023 saudyjskie powiązania w oskarżeniach Teheranu; krytyczna wobec władz); **domena bez `www`**, adres `www…/en/rss` niepoprawny XML |
| IranWire (EN) | `https://iranwire.com/en/feed/` | kanał ok | 516 (miesiąc) | **0×3** | niezależne/opozycyjne; artykuły za **Cloudflare 403** (nie obchodzimy): tylko lead |
| Press TV | `https://www.presstv.ir/rss.xml` | ok | 107 (brak dat) | 0×3 | **sankcjonowany (UE/UK)**; artykuły na `presstv.co.uk` z błędnym certyfikatem (nie wyłączamy weryfikacji); odpada technicznie |
| Radio Farda / Tasnim / IFP | — | **blokują** / nieosiągalne | — | — | odpadają; Fars: kanał z niepoprawnym XML |

**Rekomendacja IR:** Tehran Times (stanowisko oficjalne, pełny tekst) + Iran International (opozycja emigracyjna, pełny tekst) +
Mehr (druga linia państwowa). Mapa kraju to głównie głos państwowy i emigracyjny, a nie opinia wewnętrzna; oznaczyć profil
`type: government/agency` i uwagę o emigracji. Ryzyka: dostęp z serwerów GitHub Actions (część irańskich domen bywa blokowana z
adresów chmurowych, nie sprawdzono; test tylko z domowego łącza), sankcje na Press TV (pominięty).

## Japonia (JP) — słaba oferta, 1–2 źródła

| źródło | kanał | robots/art. | wpisy | słowa | profil / ryzyka |
|---|---|---|---|---|---|
| Japan Today (EN) | `https://japantoday.com/feed` | ok | 30 | 198, 328, 400 | prywatne (GPlusMedia), agregat depesz Kyodo/AFP/własne; bezpłatne; mniej „japońskie” niż „dla obcokrajowców” |
| Nippon.com (EN) | `https://www.nippon.com/en/feed/` | ok | 20 (od 23.09) | 240, 400, 255 | Nippon Communications Foundation, półoficjalne, wyważone; mało wpisów dziennie (~1–2), analizy |
| Asahi (JA) | `https://www.asahi.com/rss/asahi/newsheadlines.rdf` | ok | 40 | 14, 9, 6 | lewo-liberalne, prywatne; **paywall**, tylko nagłówek |
| Mainichi flash (JA) | `https://mainichi.jp/rss/etc/mainichi-flash.rss` | ok | 20 | 15, 5, 7 | prywatne; krótkie depesze |
| Mainichi EN | `https://mainichi.jp/english/rss/` | ok | — | — | **kanał z niepoprawnym XML** (pozycja 150:56), parser odrzuca |
| NHK (JA) | `https://www3.nhk.or.jp/rss/news/cat0.xml` | ok | 7 | 26, ~0, 0 | publiczne; **kanał nieświeży** (ostatnie wpisy z 08.08.2026) |
| Nikkei Asia | `https://asia.nikkei.com/rss/feed/nar` | ok | 50 | nie mierzono | **paywall**, brak dat w kanale |
| Japan Times | feedy | **blokuje** | — | — | odpada |
| Yahoo News JP, nhk.or.jp | | **blokuje** | — | — | odpadają |
| Kyodo, Asahi AJW, Jiji, Yomiuri | | 404 / 403 / niepoprawny XML | — | — | brak działającego kanału |

**Rekomendacja JP:** Japan Today + Nippon.com dają 2 wydawców po angielsku, ale to wąski i „eksportowy” wycinek (Nippon.com ~1–2
wpisy dziennie, Japan Today częściowo depesze międzynarodowe). Dla progu ≥2 źródła/kraj w typowym dniu to ryzykowne.
Dobrych źródeł japońskojęzycznych z pełnym tekstem brak (paywalle, nieświeże kanały). **Japonia: odradzam albo „warunkowo” z
oznaczeniem słabego pokrycia.**

## Arabia Saudyjska (SA) / ZEA

| źródło | kanał | robots/art. | wpisy | słowa | profil / ryzyka |
|---|---|---|---|---|---|
| Arab News (EN) | `https://www.arabnews.com/rss.xml` | ok | 50 | 221, 289, 400 | prywatne właścicielsko (SRMG, spółka z kręgu rządzącego), linia prorządowa, redakcja w Rijadzie/Dżuddzie |
| Asharq Al-Awsat (EN) | `https://english.aawsat.com/feed` | ok | 300 | 400×3 | SRMG, redakcja londyńska, prosaudyjska; **ten sam wydawca co Arab News** (SRMG) |
| Asharq Al-Awsat (AR) | `https://www.aawsat.com/feed` | ok | 300 | 400×3 | j.w., po arabsku |
| Saudi Gazette | `…/rss`, `/rss/all` | — | 0 / niepoprawny XML | — | kanał niedziałający |
| SPA (agencja państwowa) | `https://www.spa.gov.sa/rss` | — | — | — | nie zwraca RSS |
| Al Arabiya EN | | **blokuje** | — | — | odpada (MBC, prosaudyjska) |
| Saudi Embassy | | **blokuje** | — | — | odpada |
| Okaz | `…/rss` | — | — | — | nie RSS |
| **ZEA:** The National (EN) | `https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml` | ok | 100 | 400, 229, 400 | Abu Zabi, własność rodziny rządzącej/media państwowe, prorządowe |
| ZEA: Gulf News (EN) | `https://gulfnews.com/stories.rss` | ok | 53 | 400×3 | Dubaj, prywatne (Al Nisr), prorządowe |
| ZEA: Khaleej Times, WAM | | 404 / niepoprawny XML | — | — | brak kanału |

**Rekomendacja SA:** kanały działają, ale **nie ma w Arabii Saudyjskiej niezależnej alternatywy** (media prywatne to SRMG i MBC,
pod kontrolą kręgu władzy; Arab News i Asharq Al-Awsat to jeden wydawca). Przy `publisher_group` liczy się 1 wydawca, więc
SA nie przejdzie progu ≥2 źródła/kraj tak samo jak Katar. Jeśli właściciel chce kraj Zatoki z 2 wydawcami: **ZEA (The National + Gulf News)**
zamiast SA, oba prorządowe, bez opozycyjnej alternatywy (dopuszczalne, oznaczyć profil).

## Podsumowanie

| kraj | decyzja | źródła |
|---|---|---|
| FR | tak | Le Figaro, francetvinfo, RFI EN (+ 20 Minutes) |
| HU | tak | Telex, Index, Magyar Nemzet (+ HVG) |
| IR | warunkowo | Tehran Times, Iran International, Mehr |
| JP | słabo / odradzam | Japan Today, Nippon.com (wąskie, brak japońskich z pełnym tekstem) |
| SA | odpada; zamiast tego ZEA | SA: jeden wydawca (SRMG); ZEA: The National + Gulf News |

Otwarte pytania do właściciela: czy ekstrakcja obsługuje węgierski, japoński i arabski; czy IR zaakceptować mimo braku głosu
wewnętrznego; czy SA zastąpić ZEA (zmiana kodu kraju w projekcie).

## Gotowe wpisy YAML (NIE dodane do sources.yaml)

Wzorowane na istniejących polach. `activated_at` i `license_note` do ustawienia przy faktycznym dodaniu; pole `fulltext` zgodnie z testem.

```yaml
# --- FR ---
- id: lefigaro
  name: Le Figaro
  aliases: ['Le Figaro', 'lefigaro.fr']
  country: FR
  language: fr
  type: private
  feeds:
  - {url: 'https://www.lefigaro.fr/rss/figaro_actualites.xml', section: actualites}
  fulltext: true
  active: true
  editorial_country: FR
  publisher_group: lefigaro
  channel_scope: actualites
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: prywatne (Groupe Dassault); centroprawicowe
- id: francetvinfo
  name: francetvinfo
  aliases: ['France Info', 'francetvinfo']
  country: FR
  language: fr
  type: public
  feeds:
  - {url: 'https://www.francetvinfo.fr/titres.rss', section: titres}
  fulltext: true
  active: true
  editorial_country: FR
  publisher_group: francetv
  channel_scope: titres
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: publiczne (France Télévisions)
- id: rfi_en
  name: RFI (English)
  aliases: ['RFI']
  country: FR
  language: en
  type: public
  feeds:
  - {url: 'https://www.rfi.fr/en/rss', section: all}
  fulltext: true
  active: true
  editorial_country: FR
  publisher_group: fmm
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: publiczne (France Médias Monde)
# --- HU ---
- id: telex
  name: Telex
  aliases: ['Telex', 'telex.hu']
  country: HU
  language: hu
  type: private
  feeds:
  - {url: 'https://telex.hu/rss', section: all}
  fulltext: true
  active: true
  editorial_country: HU
  publisher_group: telex
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: niezależne (Telex Media)
- id: index_hu
  name: Index
  aliases: ['Index', 'index.hu']
  country: HU
  language: hu
  type: private
  feeds:
  - {url: 'https://index.hu/24ora/rss/', section: 24ora}
  fulltext: true
  active: true
  editorial_country: HU
  publisher_group: index_hu
  channel_scope: 24ora
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: prywatne; linia zbliżona do kręgu Fidesz (do potwierdzenia)
- id: magyarnemzet
  name: Magyar Nemzet
  aliases: ['Magyar Nemzet']
  country: HU
  language: hu
  type: private
  feeds:
  - {url: 'https://magyarnemzet.hu/feed', section: all}
  fulltext: true
  active: true
  editorial_country: HU
  publisher_group: mediaworks
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: prywatne (grupa Mediaworks/KESMA); linia prorządowa wobec Fidesz
# --- IR ---
- id: tehrantimes
  name: Tehran Times
  aliases: ['Tehran Times']
  country: IR
  language: en
  type: government
  feeds:
  - {url: 'https://www.tehrantimes.com/rss', section: all}
  fulltext: true
  active: true
  editorial_country: IR
  publisher_group: tehrantimes
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: powiązane z państwem (Islamic Culture and Relations Organization); stanowisko oficjalne
- id: iranintl
  name: Iran International
  aliases: ['Iran International', 'Iran Intl']
  country: IR
  language: en
  type: private
  feeds:
  - {url: 'https://iranintl.com/en/feed', section: all}
  fulltext: true
  active: true
  editorial_country: IR
  publisher_group: iranintl
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: emigracyjna, Londyn; opozycyjna wobec władz IR
- id: mehr_en
  name: Mehr News (EN)
  aliases: ['Mehr News', 'Mehr']
  country: IR
  language: en
  type: agency
  feeds:
  - {url: 'https://en.mehrnews.com/rss', section: all}
  fulltext: true
  active: true
  editorial_country: IR
  publisher_group: mehr
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: agencja półpaństwowa (IRIB/Organizacja Kultury Islamskiej)
# --- JP (warunkowo) ---
- id: japantoday
  name: Japan Today
  aliases: ['Japan Today']
  country: JP
  language: en
  type: private
  feeds:
  - {url: 'https://japantoday.com/feed', section: all}
  fulltext: true
  active: true
  editorial_country: JP
  publisher_group: japantoday
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: prywatne (GPlusMedia); część depesz Kyodo/AFP
- id: nippon_com
  name: Nippon.com
  aliases: ['Nippon.com']
  country: JP
  language: en
  type: private
  feeds:
  - {url: 'https://www.nippon.com/en/feed/', section: all}
  fulltext: true
  active: true
  editorial_country: JP
  publisher_group: nippon
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: Nippon Communications Foundation; półoficjalne, ~1–2 wpisy/dzień
# --- AE zamiast SA ---
- id: thenational
  name: The National
  aliases: ['The National']
  country: AE
  language: en
  type: private
  feeds:
  - {url: 'https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml', section: all}
  fulltext: true
  active: true
  editorial_country: AE
  publisher_group: thenational
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: Abu Zabi, rodzina rządząca; prorządowe
- id: gulfnews
  name: Gulf News
  aliases: ['Gulf News']
  country: AE
  language: en
  type: private
  feeds:
  - {url: 'https://gulfnews.com/stories.rss', section: all}
  fulltext: true
  active: true
  editorial_country: AE
  publisher_group: gulfnews
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: Dubaj (Al Nisr); prorządowe
# --- SA (jeśli mimo jednego wydawcy) ---
- id: arabnews
  name: Arab News
  aliases: ['Arab News']
  country: SA
  language: en
  type: private
  feeds:
  - {url: 'https://www.arabnews.com/rss.xml', section: all}
  fulltext: true
  active: true
  editorial_country: SA
  publisher_group: srmg
  channel_scope: all
  license_note: Przegląd 2026-10-02; nie oznacza udzielenia licencji.
  ownership: SRMG, krąg władzy; prorządowe
```

Zastrzeżenia: test z jednego łącza i jednego momentu; profile redakcji z wiedzy ogólnej, nie z weryfikacji; typów `government/agency`
trzeba użyć zgodnie z wartościami dozwolonymi w schemacie `sources.yaml`.
