# Paralaksa: strona wewnętrzna

Repo generowane przez `plx site --publikuj` z repo `paralaksa-narracji`. Nie edytuj ręcznie: każda publikacja
zastępuje całą zawartość jednym commitem.

- `public/`: zbudowana strona (nagłówki do 15 słów, tłumaczenia, linki; bez pełnych tekstów).
- `server.py`: serwer z hasłem (HTTP Basic Auth), tylko biblioteka standardowa.
- `konta.py`: konta innych osób (zaproszenia, hasła jako skróty PBKDF2) i czas na stronie.

Render: Web Service z tego repo, start `python server.py`, zmienne `SITE_USER` i `SITE_PASSWORD` (konto właściciela).
Bez nich serwer odpowiada 503 i niczego nie pokazuje.

Konta innych osób: właściciel otwiera `/osoby`, dodaje osobę i wysyła jej jednorazowy link `/zaproszenie/...`
(ważny 7 dni), pod którym osoba sama ustawia hasło. Strony co minutę zgłaszają czas czytania, gdy karta jest widoczna.
Dysk darmowego Rendera znika przy każdym uśpieniu i wdrożeniu, więc osoby i aktywność trafiają do prywatnego repo
`ACTIVITY_REPO` (domyślnie `kraxtere/paralaksa-aktywnosc`) przez API GitHuba; wymagany `ACTIVITY_TOKEN`: token
fine-grained z dostępem tylko do tego repo, uprawnienie Contents: Read and write. Bez tokenu działa tylko konto właściciela.
