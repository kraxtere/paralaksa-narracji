# Paralaksa: strona wewnętrzna

Repo generowane przez `plx site --publikuj` z repo `paralaksa-narracji`. Nie edytuj ręcznie: każda publikacja
zastępuje całą zawartość jednym commitem.

- `public/`: zbudowana strona (nagłówki do 15 słów, tłumaczenia, linki; bez pełnych tekstów).
- `server.py`: serwer z hasłem (HTTP Basic Auth), tylko biblioteka standardowa.

Render: Web Service z tego repo, start `python server.py`, zmienne `SITE_USER` i `SITE_PASSWORD`.
Bez nich serwer odpowiada 503 i niczego nie pokazuje.
