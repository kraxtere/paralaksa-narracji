# Paralaksa: strona wewnętrzna

Repo generowane przez `plx site --publikuj` z repo `paralaksa-narracji`. Nie edytuj ręcznie: każda publikacja
zastępuje całą zawartość jednym commitem.

- `public/`: zbudowana strona (nagłówki do 15 słów, tłumaczenia, linki; bez pełnych tekstów).
- `server.py`: serwer z logowaniem (linki zaproszenia, hasło właściciela, podpisane ciasteczko na 365 dni odnawiane
  przy czytaniu; HTTP Basic Auth dla skryptów), biblioteka standardowa (poza powiadomieniami).
- `konta.py`: konta innych osób (linki zaproszenia, klucze logowania; starsze konta z hasłem jako skrót PBKDF2) i czas
  na stronie.
- `powiadomienia.py`: powiadomienia push o nowym wydaniu (Web Push, `pywebpush` z `requirements.txt`).

Render: Web Service z tego repo, start `python server.py`, zmienne `SITE_USER` i `SITE_PASSWORD` (konto właściciela).
Bez nich serwer odpowiada 503 i niczego nie pokazuje.

Konta innych osób, bez haseł: właściciel otwiera `/osoby`, dodaje osobę i wysyła jej imienny link `/zaproszenie/...`;
otwarcie od razu loguje („Witaj, imię”), także na kolejnych urządzeniach, przez 30 dni. „Nowy link” unieważnia
poprzedni (zalogowane urządzenia zostają), „Zablokuj” wylogowuje wszędzie i unieważnia linki. Link ogólny (włączany na
`/osoby`, „Nowy link ogólny” unieważnia stary) pyta tylko o imię lub nazwę: nowe imię zakłada konto, to samo imię na
innym urządzeniu to to samo konto (można się podszyć), zablokowane imię nie wejdzie. Link można też wkleić na stronie
logowania (aplikacja na ekranie głównym nie ma paska adresu). Hasło ma tylko właściciel. Strony co minutę zgłaszają, co jest czytane,
gdy karta jest widoczna i ktoś jej używał w ostatnich 5 minutach (przewijanie, dotyk, mysz, klawisz), oraz od razu,
gdy karta zostanie schowana. Karta zostawiona bez ruchu milknie, więc serwer może zasnąć po 15 minutach. „Usuń” kasuje konto, historia zostaje.
Dysk darmowego Rendera znika przy każdym uśpieniu i wdrożeniu, więc osoby i aktywność trafiają do prywatnego repo
`ACTIVITY_REPO` (domyślnie `kraxtere/paralaksa-aktywnosc`) przez API GitHuba; wymagany `ACTIVITY_TOKEN`: token
fine-grained z dostępem tylko do tego repo, uprawnienie Contents: Read and write. Bez tokenu działa tylko konto właściciela.

Powiadomienia: osoba włącza je w menu w pasku (iPhone: tylko w zainstalowanej aplikacji). Subskrypcje trafiają do
`powiadomienia.json` w repo aktywności. Po każdym wdrożeniu serwer przy starcie wysyła jedno powiadomienie o najnowszym dniu
(`public/v2/powiadomienie.json`), jeśli ten dzień nie był jeszcze ogłoszony. Wymaga `VAPID_PRIVATE_KEY` (klucz P-256 w base64url,
ten sam co w lokalnym `.env` repo źródłowego); bez niego menu nie pokazuje powiadomień.
