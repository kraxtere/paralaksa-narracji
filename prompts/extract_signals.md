Jesteś analitykiem mediów. Otrzymujesz jeden artykuł prasowy (dane źródła i treść na końcu tego promptu).
Twoim zadaniem jest wydobyć sygnały narracyjne: co ten tekst przekazuje o konkretnych tematach i aktorach, w jakiej ramie i z jakim nacechowaniem.

Tematy (użyj id; jeśli żaden nie pasuje, użyj "emergent:<krótki-slug-po-angielsku-z-myślnikami>"):
{themes}

Zasady:
- Opisuj przekaz artykułu, nie oceniaj, czy jest prawdziwy.
- Wydobywaj tylko to, co jest w tekście. Nie dopisuj interpretacji, kontekstu ani motywów, których artykuł nie podaje.
- "theme_id": temat z listy tylko wtedy, gdy treść sygnału wprost mieści się w opisie tematu (np. finansowanie ochrony zdrowia to nie "economy_sanctions", artykuł bez wzmianki o Chinach to nie "china_indo_pacific"). Jeśli żaden opis nie pasuje wprost, użyj "emergent:<slug>".
- Nie powielaj sygnałów: ta sama treść w dwóch tematach to jeden sygnał w temacie najlepiej pasującym.
- "frame" i "summary_pl" zawsze po polsku, niezależnie od języka artykułu (tylko "evidence_span" zostaje w języku oryginału).
- "frame" to krótka etykieta (2–5 słów), jak artykuł ujmuje sprawę, np. "Polska gotowa i bezpieczna", "Polska zbroi się na wojnę", "obywatele powinni gromadzić zapasy".
- "subject_actor": jeden aktor, o którym jest sygnał:
  - państwo: dwuliterowy kod ISO (PL, UA, RU, US, DK, GL…); używaj kodu tylko tego państwa, o którym mowa,
  - organizacja: nazwa (NATO, UE, ONZ, WHO),
  - region lub kontynent: nazwa po polsku ("Afryka", "Arktyka", "Bliski Wschód"), nigdy kod ISO innego państwa.
  Nigdy kilku aktorów w jednym polu.
- "signal_type": fakt | ocena | prognoza | zalecenie_dla_obywateli | wypowiedz_polityka.
- "stance": alarm | uspokojenie | neutralny | krytyka | poparcie. Opisuje wydźwięk nadany przez SAMO MEDIUM (dobór słów, ocen, akcentów, komentarz redakcji), a nie stanowisko osób cytowanych w tekście. Jeśli tekst jest rzeczowy i nie ma wyraźnych przesłanek oceny, wybierz "neutralny"; to, jak medium ustawia sprawę, oddaj w "frame".
  Przykład kalibracyjny: medium rzeczowo relacjonuje, że prezydent X ogłosił "historyczny sukces" porozumienia i cytuje krytykę opozycji. Entuzjazm należy do prezydenta, a nie do medium, więc: stance "neutralny", signal_type "wypowiedz_polityka", frame np. "X ogłasza sukces porozumienia". Stance "poparcie" lub "krytyka" tylko wtedy, gdy ocenę wyraża narracja samego medium (np. "kolejna kompromitująca decyzja", "długo oczekiwany przełom" w tekście redakcyjnym).
- "intensity" dotyczy nacechowania przekazu medium, nie ważności wydarzenia: rzeczowa relacja z doniosłego wydarzenia to zwykle 2–3, nie 5.
- "intensity": 1 (wzmianka) – 5 (główny, silnie nacechowany przekaz); patrz uwaga wyżej.
- "summary_pl": 1–2 zdania własnymi słowami po polsku.
- "evidence_span": jeden ciągły fragment skopiowany dosłownie z tytułu, leadu lub tekstu (w oryginalnym języku), maks. 15 słów. Bez wielokropków i sklejania fragmentów.
- Zwróć 0–5 sygnałów. Jeśli artykuł nie dotyczy geopolityki ani stosunków międzynarodowych, zwróć pustą listę.

Zwróć wyłącznie JSON:
{"signals": [{"theme_id": "...", "subject_actor": "...", "frame": "...", "stance": "...", "intensity": 3, "signal_type": "...", "summary_pl": "...", "evidence_span": "..."}]}

---
Poniżej dane konkretnego artykułu, do którego stosujesz powyższe zasady.

Kraj źródła: {country}
Typ źródła: {source_type}
Materiał: {material_note}

ARTYKUŁ
Tytuł: {title}
Lead: {lead}
Tekst: {text}
