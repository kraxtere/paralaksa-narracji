# Oś czasu: kółko myszy i kolejność wątków — 2026-10-17

- Kółko na komputerze (`scripts/v2/os_czasu.py`, JS strony): oś przesuwa się w bok tylko na wysokości paska z datą i obrazków (od góry
  karty do dołu obrazka), niżej (tekst, nagłówki, przerwy) kółko przewija stronę. Wcześniej rozstrzygało, czy kursor jest na karcie.
  Opis pod tytułem osi mówi to samo.
- Filtry wątków nad osią: od ostatnio wspomnianych (najnowszy czas zdarzenia, przy remisie więcej zdarzeń); najstarsze wątki na końcu.
  „Wszystko” zostaje pierwsze; wątek z jednym zdarzeniem nadal bez filtra.
- Sprawdzone w przeglądarce (Playwright, strona osi z 16.10): kółko na obrazku i na dacie przesuwa w bok, na tekście przewija stronę.

# Przycisk Udostępnij, powitanie, poprawka cięcia okładki — 2026-10-17

- Pasek (`assets/pasek.js`): ikona „Udostępnij Paralaksę” obok logo (`aria-label`, bez napisu). Zawsze cała Paralaksa: link do roota
  (`new URL("../", base)`, na Cloudflare przekierowanie na najnowszy dzień) z opisem „Paralaksa narracji: jak prasa z N krajów opisuje to samo
  wydarzenie. Codzienny przegląd w obrazkach.” Telefon i tablet (dotyk + `navigator.share`): systemowe okno udostępniania, też z aplikacji
  zainstalowanej na ekranie głównym; komputer: kopiowanie linku z komunikatem „Skopiowano” (bez schowka: okno z linkiem). Bez ekranu wyboru.
- N krajów z danych: `build._active_countries()` liczy kraje aktywnych źródeł z `config/sources.yaml` (dziś 17) i wstawia do `pasek.js`
  (`"__KRAJE__"`); gdy konfiguracji nie da się wczytać, tekst brzmi „z wielu krajów”.
- Powitanie (modal „Czym jest Paralaksa narracji?”): raz na kartę przeglądarki, dopóki ktoś nie zaznaczy „Nie pokazuj więcej” (flaga
  `plx-powitanie` w localStorage na stałe, `plx-powitanie-sesja` w sessionStorage). Stały link „O Paralaksie” w stopce i w menu osoby (Render).
  Treść wstępna z mojej propozycji; do podmiany na wersję z drugiej sesji.
- `paski.py`: ciemna scena zlana z ramką (okładka 15.10, `okladka2-A`: pasy 586/224/676 px) dawała nierówne cięcie. `detect_strips` przy
  wyraźnie nierównych pasach próbuje ramek na brzegach grubych ciemnych pasm i bierze równiejszy układ (15.10 → 494/490/504 px). Ponownie
  przecięte okładki 02.10 i 03.10.
- Testy: asercje w `tests/test_site.py` (pasek z ikoną, „O Paralaksie”, brak niepodmienionego `__KRAJE__`); zachowanie w przeglądarce sprawdzone
  ręcznie (Playwright: kopiowanie, `navigator.share`, powitanie, flaga).

# dzien.py: krok bez wyniku to błąd, współbieżność przez zmienne — 2026-10-13

- Przebieg 13.10: `plx site` przy 429 z Codexa skończył się kodem 0 bez `data/stories/D.json` („strona bez historii”), krok zapisał się jako gotowy,
  a `os-dzien` i dalsze czekały na marker; wznowienie nic nie robiło. Teraz krok z `result`, który zwraca 0 bez pliku wynikowego, jest błędem
  (nie trafia do `_dzien.json`) w `run_parallel` i `run_steps`; niespełnione markery wypisuje „! nie ruszyły: … (brak markera: …)”. Kod wyjścia 1.
- Współbieżność bez zmiany logiki: `DZIEN_WORKERS` (kroki fazy 1, domyślnie 9), `PLX_TYTULY_WORKERS` (tłumaczenia nagłówków, domyślnie 8).
- Testy: `tests/test_dzien.py` (krok bez wyniku, exit ≠ 0 przy braku markera, komunikat).

# Przyspieszenie fazy 1 dzien.py — 2026-10-13

- Przyczyna (analiza 12.10): faza 1 = `site` → `os-dzien` → `kraje-D` → `kraje-ciag`, a czas wynika z długich wywołań Codexa w `plx site` (historie dnia,
  potem tłumaczenia nagłówków po kolei) i w `os-dzien` (weryfikacje szeregowo); liczba wywołań i kontekst historii się nie zmieniły.
- `os-dzien` rusza, gdy `data/stories/D.json` jest kompletny (`Step.wait_files`, sprawdzanie co `POLL_S` = 2 s), nie po całym `plx site`. `kraje-D` nadal
  czeka na cały `site` (czyta `data/tytuly/D.json`). `stories.generate` zapisuje plik atomowo.
- `plx site`: historie dnia i tłumaczenia nagłówków dnia idą równolegle (`site/data.py`; każdy callback ma własne połączenie SQLite, klient i koszt pod blokadą),
  tłumaczenia po 60 nagłówków i 8 workerów (było 120 i 4). Weryfikacje historii (`stories.generate`) i `os_czasu.extra_events` równolegle
  (`stories.parallel_map`, wyniki w kolejności porcji, jak w pętli).
- Logi: `paralaksa/extract/call_log.py` zapisuje czas każdego wywołania Codexa (CodexClient i `codex_text`) do `data/widok/D/_wywolania.jsonl`;
  `_czasy.json` zachowuje fazy i kroki z poprzednich procesów, dodaje `przebiegi` ze startem i końcem (także obrazki fazy 2).
- Testy: graf `phase1` bez cyklu, start po markerze, kolejność wyników, log wywołań (`tests/test_dzien.py`, `tests/test_przyspieszenie_fazy1.py`).

# Cloudflare Pages: strona główna i aplikacja — 2026-10-11

- `/` zwracał stary „Przegląd” (root `index.html`), a `_redirects` nie zadziałało. `stage_cf` nie wysyła już `_redirects`: root `index.html` to teraz
  strona z natychmiastowym przekierowaniem (meta refresh + `location.replace`) na `/v2/NAJNOWSZY/` (forma katalogowa, bo Pages odpowiada 308 na `.html`),
  a stary „Przegląd” jest pod `/przeglad.html` (linki z `dziennik/` i `zdarzenia/` przepisane w kopii wdrożeniowej).
- Manifest ma `start_url` i `scope` względne (`./`), więc pasują do domeny `pages.dev`; bez zmian.
- Ekstrakcja 10.10: dwa artykuły z `extracted=2` (walidacja po ponowieniu) blokowały `plx report` (niepełna ekstrakcja); ponowne uruchomienie
  `ekstrakcja_codex_dnia.py` dla dnia je naprawia (losowo, do 2–3 prób).

# Statyczna kopia na Cloudflare Pages — 2026-10-09

- Powód: Render zatrzymany po 5 GB transferu; Docker Space na HF wymaga płatnego planu. `plx site --publikuj-cf` (`publish.stage_cf`, `publish_cf`)
  wdraża `npx wrangler pages deploy` (bezpośredni upload, bez dodatkowego repo; token i Account ID tylko w środowisku procesu).
  Katalog: sama strona + `_headers` (noindex, cache obrazków 1 dzień, html/js/json no-cache), `robots.txt` (Disallow), `_redirects` (`/` → najnowszy
  dzień z `v2/dni.json`, odświeżany przy każdym wdrożeniu). Opcjonalny beacon Cloudflare Web Analytics tylko przy `CF_ANALYTICS_TOKEN`.
- Strona statyczna nie ma haków serwera (menu osoby, heartbeat, push wstawia tylko server.py przez `window.plxJa`), więc nic nie trzeba wyłączać;
  `sw.js` i manifest działają (instalacja jako aplikacja), bez push. Limity Free: 20 000 plików i 25 MiB na plik; mamy ok. 3600 plików, max <10 MB.
- `.env`: `CF_PROJECT`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, opcjonalnie `CF_ANALYTICS_TOKEN`. Testy w `tests/test_site_publish.py`.

# Zapasowy hosting: Hugging Face Space (Docker) — 2026-10-08

- Powód: Render zatrzymał serwis po 5 GB transferu. `plx site --publikuj-hf` układa katalog jak `--publikuj` (`publish.stage_hf`), dokłada
  `hosting/hf/Dockerfile` (python:3.12-slim, uid 1000, `PORT=7860`) i README Space (YAML `sdk: docker`, `app_port: 7860`), wypycha jednym
  commitem do `HF_SPACE` (użytkownik/nazwa) z `HF_TOKEN` (tylko w URL pushu, bez zapisu w `.git/config`, maskowany w błędach).
- `server.py`: adres dla powiadomień push z `PUBLIC_URL` (przed `RENDER_EXTERNAL_URL`). Serwer nie zapisuje na dysk (konta i subskrypcje
  w repo ACTIVITY_REPO), więc restart Space niczego nie gubi. Pliki strony < 10 MB, Git LFS niepotrzebny. Testy w `tests/test_site_publish.py`.

# Serwer strony: cache i gzip przeciw zużyciu transferu — 2026-10-08

- Powód: 5 GB transferu Rendera zużyte w 8 dni. Każda publikacja to force-push i nowy deploy, więc wszystkie pliki miały nowe `Last-Modified`
  i przeglądarki pobierały je od nowa (to samo po restarcie usypiającego się serwisu).
- `hosting/server.py`: obrazki, js, css, json mają ETag z zawartości (304 po deployu i restarcie); obrazki dodatkowo `max-age=86400`;
  HTML (z indywidualnym dopiskiem) idzie gzipem, nadal `no-cache`. Test w `tests/test_site_publish.py`.
- Efekt dopiero po publikacji strony (`plx site --publikuj`), bo serwer jest wdrażany razem ze stroną.

# Strona dnia 07.10: poprawki widok_obrazkowy — 2026-10-07

- `theme_page`: kraje zapisanego `plakat-*.json`, których nie ma już w danych tematu (po przeliczeniu raportu), są pomijane (wcześniej `KeyError`).
- `limit_guard`: odczyt limitu Codexa co najwyżej raz na 2 min na proces; gdy odczyt się nie uda (błąd sieci), kontrola jest pomijana
  zamiast przerywać obrazki i streszczenia. Stop przy >= 95% działa, gdy odczyt się powiedzie. `kraje.py`: odczyt limitu tylko do statystyki,
  jego brak nie przerywa kroku (wcześniej tracił wynik).
- Kraje 07.10 po dociągnięciu: dla krajów z innymi tytułami tematów niż zapisane przy obrazkach przywrócono tematy z pierwszego przebiegu
  (obrazki w `data/widok/kraje/D/` pasują tylko przy zgodnych tytułach).
- Procedura po dociągnięciu źródeł lokalnie: po zmianie danych dnia trzeba zresetować kroki (`_dzien.json`, `data/stories/D.json`,
  `reports/D.json`, wyniki osi i krajów) oraz usunąć zdarzenia dnia z `data/widok/os/plan.json`, bo numery historii się zmieniają.

# daily.yml: tylko ingest i backup — 2026-10-06

- Za zgodą właściciela Actions robi `plx ingest` + snapshot/backup bazy; bez ekstrakcji i bez kluczy DeepSeek/Anthropic (artykuły zostają
  `extracted=0`, podejmuje je lokalnie `scripts/ekstrakcja_codex_dnia.py`). Nie powstaje już `reports/D.status.json` z Actions.
  Po ekstrakcji baza musi wrócić do Release (`docs/OPERATIONS.md`), inaczej następny przebieg ją nadpisze.

# Ekstrakcja przez Codex na stałe — 2026-10-06

- Decyzja właściciela: bez płatnych API (DeepSeek); ekstrakcja lokalnie przez Codex z limitu konta (`codex:gpt-6-luna:medium`,
  wsady 25, prompt v3 w `scripts/v2/prompt_luna_v3.md`). Skrypt dnia: `scripts/ekstrakcja_codex_dnia.py` (opcje: `--model`, `--wsad`,
  `--rownolegle`, `--dodatek`, `--limit`). Zmiana procedury i `daily.yml`: osobno, po zgodzie właściciela.

# Archiwum: jeden filtr „Temat” zamiast kategorii i tematów — 2026-10-06

- `archiwum.js`: znika wiersz „Kategoria” (przyciski „tematy analizy”, „polityka”…) i osobny filtr tematu w „Więcej filtrów”.
  W jego miejscu pod okresem jest jedna rozwijana lista „Temat” (natywny wybierak, na telefonie czytelny, pełna szerokość).
- Zasada: artykuł ma jedną etykietę: temat analizy z sygnałów (jak dotąd tylko stałe, bez `emergent:*`; artykuł z kilkoma
  tematami liczy się w każdym), a gdy sygnałów brak, kategoria ogólna. Duplikaty scalane po zapisie (wielkość liter, polskie
  znaki, spacje: „Polityka”/„polityka”) i po nazwie tematu analizy (kategoria „wojna w Ukrainie” to temat „Wojna w Ukrainie”).
  Bez zgadywania znaczeń: „polityka” i „gospodarka” zostają osobnymi opcjami obok „Wybory i polityka” / „Gospodarka i sankcje”.
- Filtry progresywne bez zmian w zasadzie: liczba przy każdej opcji (bez własnego filtra, z kraj/źródło/ton/aktor/słowa/dzień),
  opcje zerowe ukryte, wybrana zostaje; ton i aktor nadal dotyczą sygnałów (artykuły bez sygnałów znikają z listy tematów).
  Znacznik pod artykułem to jeden „temat” (bez „kategoria”). Stare linki `#kat=…` działają jak `#th=…`; `kat=*` ignorowane.
- Testy: `tests/test_archiwum_ui.py` (lista tematów, scalanie, progresja, stary link); wykres i pozostałe filtry bez zmian.

# schema.py: naprawa evidence_span z wielokropkiem — 2026-10-06

- `parse_extraction` z `source_text`: gdy `evidence_span` skleja fragmenty przez „...”/„…”, wybierany jest najdłuższy kawałek, który
  sam występuje dosłownie w artykule (min. 3 słowa, maks. 15; `longest_verbatim_segment`), i liczony jako `repairs`. Gdy żaden
  kawałek nie spełnia warunków, sygnał nadal jest odrzucany jak dotąd. Reszta walidacji bez poluzowania. Powód: test Luny
  (Codex) odrzucał ok. 7% sygnałów, z czego część to wielokropki mimo zakazu w prompcie. Testy w `tests/test_extract_schema.py`.

# Starsze wpisy: docs/CHANGELOG_ARCHIWUM.md (tylko grep)
