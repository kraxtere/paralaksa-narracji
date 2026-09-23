# Warianty po przeglądzie warunków źródeł (2026-09-23)

Uzupełnienie do [`LEGAL_REVIEW_2026-09-23.md`](LEGAL_REVIEW_2026-09-23.md). **Nie jest poradą prawną.**
Decyzja właściciela z tego dnia: system działa bez zmian; poniższe to analiza i materiały na później.
Nic z tego nie zostało wdrożone.

## 1. Guardian Open Platform — nie rozwiązuje problemu

Sprawdzone 2026-09-23: [warunki Open Platform](https://www.theguardian.com/open-platform/terms-and-conditions).

- Klauzula 6(g), dodana 25.01.2024: zakaz użycia treści „for any text and data aggregation, analysis or mining
  purposes (including to generate any patterns, trends or correlations)” oraz „with any machine learning and/or
  artificial intelligence technologies to generate any data or content or to synthesise or combine with any other
  data or content”. To samo zastrzeżenie co w zwykłym regulaminie Guardiana — API go nie omija.
- Klauzula 5: treści z API trzeba usuwać lub odświeżać co najmniej co 24 godziny.
- Klauzula 7(a): treści tylko dla użytkowników końcowych „personal and non-commercial use”.

Wniosek: dla Paralaksy jedyną drogą do Guardiana jest indywidualna licencja
(`licensing@theguardian.com`, ewentualnie przez NLA Media Access dla monitoringu mediów).

## 2. Wariant „bez archiwum pełnych tekstów” (pomysł właściciela)

Idea: pełny tekst żyje tylko do chwili ekstrakcji; w bazie zostają tytuł, lead, URL, sygnały
(rama, nacechowanie, streszczenie po polsku, cytat ≤ 15 słów) i hash treści.

### Czy to technicznie możliwe

Tak. Po udanej ekstrakcji (`articles.extracted = 1`) pełny tekst czytają jeszcze tylko dwa miejsca:

| miejsce | po co | czym zastąpić |
|---|---|---|
| `ingest/dedup.py` `mark_syndication` | hash identycznych przedruków; **liczy go od nowa przy każdym ingeście ze wszystkich artykułów** | policzyć hash raz przy pobraniu, zapisać, nie przeliczać dla artykułów bez tekstu |
| `aggregate/sample.py` | liczba „pełny tekst / tylko lead” w metadanych raportu | flaga głębokości (jest już w `signals.source_depth`) albo kolumna `had_fulltext` |

Do tego jedna migracja (kolumny hash/flagi) i krok „wyczyść `fulltext` po ekstrakcji” w `run-daily`.
Szacunek: mała zmiana, kilka testów. Obecna baza ma ok. 1,4 MB pełnych tekstów z 490 artykułów —
po wyczyszczeniu backup w Release przestaje zawierać artykuły, zostają tylko nasze wnioski.

Koszt jakościowy: brak — ekstrakcja nadal widzi pełny tekst. Tracimy tylko możliwość ponownej ekstrakcji
starych artykułów (np. po zmianie promptu) bez ponownego pobrania.

### Co to zmienia prawnie (według cytatów z przeglądu)

Usuwa jeden z trzech spornych elementów — **archiwizację**. Nie usuwa dwóch pozostałych:
kopii tekstu w chwili pobrania i **przesłania go do zewnętrznego API** (DeepSeek, Anthropic).

| grupa | źródła | czy wariant pomaga |
|---|---|---|
| zakaz archiwizacji | tagesschau („Die Inhalte dürfen nicht archiviert werden”) | tak, w tym punkcie; zostaje zakaz przekazania danych osobom trzecim (API) |
| zakaz treści spoza RSS | jpost (wolno budować usługi na samym RSS) | pomaga dopiero razem z `fulltext: false` (tylko tytuł + lead z kanału) |
| zakaz samej automatycznej analizy / AI | guardian, aljazeera, bbc | nie — zakazana jest analiza, nie przechowywanie |
| tylko użytek osobisty | fox, alquds_ps | nie w wariancie publicznym; patrz punkt 4 |
| ryzyko / niejasne (pozostałe 11) | onet, rp, ukrinform, pravda_ua, spiegel, cgtn, pbs, npr, propublica, folha, agenciabrasil | zmniejsza ryzyko tam, gdzie przeszkodą była kopia/baza; nie rozstrzyga kwestii API |

Najmocniejsza kombinacja dla „szarej strefy”: **brak archiwum + `fulltext: false` dla źródeł z zakazem
treści spoza kanału** (kosztem płytszych sygnałów — jak dziś przy rp i Spieglu).

## 3. Szkic listu do wydawców

Do wysłania ręcznie przez właściciela (adresy: sekcja „Do kogo pisać” w przeglądzie).
Wersja angielska dla wydawców zagranicznych; polską dla Onetu/Gremi Media łatwo przetłumaczyć.
Pola w nawiasach kwadratowych do uzupełnienia.

> **Subject:** Permission request: non-commercial media-framing analysis using your RSS feed
>
> Dear [Publisher] licensing team,
>
> I run *Paralaksa narracji*, a [non-commercial / personal] project that compares how media in ten countries
> frame the same topics (e.g. sanctions, the war in Ukraine) — not what happened, but how it is presented.
> [Publisher] is one of [2] sources representing [country].
>
> What the system does with your content:
> - once a day it reads your public RSS feed [and the article pages linked from it], identifying itself as
>   `paralaksa-narracji/0.1 (+https://github.com/kraxtere/paralaksa-narracji)` and respecting robots.txt;
> - each article is analysed once by a language model via API ([DeepSeek, Anthropic]) to extract the frame,
>   tone and a short summary. This is inference only; the providers do not train on API data under their terms;
> - [the full text is deleted right after analysis / is kept in a private encrypted database];
> - a daily report [published on GitHub / kept private] contains our own analysis, article titles, links back
>   to your site and quotes of at most 15 words.
>
> Volume: about [20–40] articles per day. No advertising, no fees, no republication of articles.
>
> Could you tell me whether this use is permitted under your terms, or under what licence it could be?
> If you would prefer a narrower scope (e.g. headlines and RSS summaries only, no article pages),
> I will adapt the system accordingly. If you do not want your content included, I will remove it.
>
> Kind regards,
> [name, contact]

Uwagi: pisać prawdę o obecnym stanie (w chwili pisania pełne teksty **są** archiwizowane — wybrać
wariant w nawiasie zgodnie z faktami). Odpowiedzi zapisywać w `docs/` z datą; zgoda na piśmie
to jedyna rzecz, która zmienia werdykt „niedozwolone”.

## 4. Wariant prywatny (tylko do użytku własnego)

Zmienia obraz częściowo — to pytanie do prawnika, nie wniosek:

- Klauzule „personal, non-commercial use” (Fox RSS, Al-Quds, użytkownicy końcowi u Guardiana) opisują
  właśnie użytek osobisty; prywatne narzędzie dla jednej osoby jest mu znacznie bliższe niż publiczny raport.
- W Polsce istnieje dozwolony użytek prywatny (art. 23 pr. aut.). Otwarte pytania: czy obejmuje przesłanie
  tekstu do zewnętrznego API i czy zastrzeżenia regulaminowe (umowne) go ograniczają.
- Wyraźne zakazy analizy/TDM/AI (Guardian, Al Jazeera, BBC) **nie mają wyjątku dla użytku osobistego**
  w samych regulaminach. Formalnie problem pozostaje; praktycznie maleje ekspozycja (brak publikacji).
- Technicznie wariant prywatny to: prywatne repozytorium (albo raporty poza repo), a backup i tak jest zaszyfrowany.
  Uwaga: prywatne repo ma limity minut GitHub Actions na darmowym planie — do sprawdzenia przed przejściem.
