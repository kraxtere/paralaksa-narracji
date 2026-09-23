# Zlecenie: przegląd warunków korzystania ze źródeł (dla GPT)

**Zakres pracy: wyłącznie badanie i raport tekstowy.** Nie zmieniaj kodu, konfiguracji
(`config/`), testów, workflowów ani innych plików poza jednym plikiem wynikowym opisanym niżej.
Nie aktywuj ani nie dezaktywuj źródeł. Decyzje na podstawie raportu podejmuje właściciel.

## Czym jest projekt (potrzebne do oceny)

Paralaksa narracji: automatyczna, codzienna analiza porównawcza przekazu medialnego z kilku krajów.
Szczegóły: `SPEC.md`, `README.md`. Istotne dla oceny praw:

1. **Pobieranie:** raz dziennie kanał RSS każdej redakcji (identyfikujący User-Agent
   `paralaksa-narracji/0.1 (+https://github.com/kraxtere/paralaksa-narracji)`, respektowanie robots.txt,
   2 s odstępu na domenę). Dla części źródeł także pełny tekst artykułu ze strony (bez obchodzenia paywalli).
2. **Przetwarzanie:** tekst artykułu trafia do zewnętrznego modelu językowego przez API
   (DeepSeek do ekstrakcji, Anthropic Claude do syntezy). To **wnioskowanie**, nie trenowanie modelu;
   dostawcy nie trenują na danych z API wg ich warunków — sprawdź, czy regulamin wydawcy to rozróżnia.
3. **Przechowywanie:** pełne teksty tylko w prywatnej, zaszyfrowanej bazie SQLite (backup w
   GitHub Release publicznego repo, zaszyfrowany AES-256). Nigdy w jawnym repo.
4. **Publikacja:** codzienny raport Markdown w **publicznym repozytorium GitHub**: własne omówienie
   przekazu (ramy, nacechowanie, porównania między krajami), tytuły i linki do artykułów,
   cytaty maks. 15 słów. Obecnie **niekomercyjne**, bez reklam i opłat. Właściciel nie wyklucza
   przyszłego produktu — oceń oba warianty osobno.

## Źródła do oceny (18 aktywnych)

| redakcja | kraj | id | punkt wyjścia (warunki/RSS) | kanał |
|---|---|---|---|---|
| Rzeczpospolita | PL | rp | — (znajdź regulamin) | https://www.rp.pl/rss_main |
| Onet Wiadomości | PL | onet | — | https://wiadomosci.onet.pl/.feed |
| Ukrinform | UA | ukrinform | — | https://www.ukrinform.ua/rss/block-lastnews |
| Ukraińska Prawda | UA | pravda_ua | — | https://www.pravda.com.ua/rss/ |
| Tagesschau (ARD) | DE | tagesschau | — | https://www.tagesschau.de/xml/rss2 |
| Der Spiegel | DE | spiegel | — | https://www.spiegel.de/ausland/index.rss |
| BBC News | UK | bbc | — | https://feeds.bbci.co.uk/news/world/rss.xml |
| The Guardian | UK | guardian | — (Guardian ma Open Platform — sprawdź) | https://www.theguardian.com/world/rss |
| Al Jazeera English | QA | aljazeera | — | https://www.aljazeera.com/xml/rss/all.xml |
| CGTN | CN | cgtn | — | https://www.cgtn.com/subscribe/rss/section/world.xml |
| PBS News | US | pbs | https://www.pbs.org/newshour/about/pbs-news-rss-feeds | https://www.pbs.org/newshour/feeds/rss/headlines |
| Fox News | US | fox | https://www.foxnews.com/story/foxnews-com-rss-feeds | https://moxie.foxnews.com/google-publisher/us.xml |
| NPR | US | npr | https://www.npr.org/about-npr/179876898/terms-of-use | https://feeds.npr.org/1004/rss.xml |
| ProPublica | US | propublica | https://www.propublica.org/steal-our-stories | https://www.propublica.org/feeds/propublica/main |
| The Jerusalem Post | IL | jpost | — | https://www.jpost.com/rss/rssfeedsfrontpage.aspx |
| Al-Quds (جريدة القدس) | PS | alquds_ps | — | https://www.alquds.com/ar/feed |
| Folha de S.Paulo | BR | folha | https://www1.folha.uol.com.br/feed/ | https://feeds.folha.uol.com.br/mundo/rss091.xml |
| Agência Brasil | BR | agenciabrasil | https://agenciabrasil.ebc.com.br/feed/ | https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml |

Znane wcześniej uwagi są w `config/sources.yaml` (`license_note`) i `docs/SOURCE_REVIEW.md` —
zweryfikuj je, nie przepisuj bez sprawdzenia.

## Pytania dla każdego źródła

1. Czy warunki (regulamin serwisu, warunki RSS, licencja treści) **dopuszczają automatyczne pobieranie** RSS
   i ewentualnie pełnego tekstu?
2. Czy dopuszczają **przetwarzanie treści przez zewnętrzny model AI** (wnioskowanie)? Czy mają klauzule o AI,
   text-and-data mining (np. zastrzeżenie TDM wg art. 4 dyrektywy UE 2019/790 dla źródeł z UE)?
3. Czy dopuszczają **publikację własnej analizy** z tytułem, linkiem i krótkim cytatem (≤ 15 słów)?
   Uwzględnij dozwolony użytek / fair use / prawo cytatu, jeśli regulamin milczy.
4. Czy przechowywanie pełnego tekstu w prywatnej, zaszyfrowanej bazie jest dopuszczalne?
5. Różnica: obecne użycie niekomercyjne vs przyszły produkt komercyjny.

## Wymagany wynik

Jeden plik: `docs/LEGAL_REVIEW_<RRRR-MM-DD>.md`. Dla każdego źródła:

- **werdykt** dla użycia niekomercyjnego i osobno komercyjnego: `dopuszczalne` / `ryzyko` / `niedozwolone` / `niejasne`;
- **dosłowny cytat** kluczowej klauzuli (w oryginalnym języku) + URL + data dostępu. Bez cytatu werdykt
  nie jest wiarygodny: jeśli nie znalazłeś klauzuli, napisz to wprost i daj `niejasne`, nie zgaduj;
- konkretna **rekomendacja** (np. „wyłączyć pobieranie pełnego tekstu”, „dopisać atrybucję w raporcie”,
  „wymaga zgody — adres kontaktowy X”, „bez zmian”).

Na końcu: tabela zbiorcza i lista źródeł, gdzie warto napisać do wydawcy o zgodę (z adresem).
Dodatkowo oceń zablokowane dotąd: Times of Israel (robots.txt `Disallow: /feed/`) i Ma'an (Cloudflare) —
czy mają oficjalną drogę licencyjną/partnerską.

**Zastrzeżenie w nagłówku pliku:** to przegląd pomocniczy, nie porada prawna.
