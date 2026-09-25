# Paralaksa: krótki opis do konsultacji (stan 2026-09-25)

## Idea
Jedno zdarzenie, wiele opowieści. Pokazujemy obok siebie nagłówki z różnych krajów o tym samym fakcie,
bez komentarza, i pozwalamy widzowi zobaczyć, gdzie opowieści się rozchodzą: co jest na pierwszym planie,
czyj głos, co pominięto. Hasło: „jeśli chcesz wiedzieć, co się dzieje, czytaj wiadomości z różnych miejsc”.

## Przykłady z ostatnich dni
- **Wystąpienie Nawrockiego w ONZ.** W Polsce: „imperialna pycha Rosji”. W Rosji: „Nawrocki zażądał przyjęcia Polski do G20”,
  „Polska poprosiła się do G20”. W Ameryce Łacińskiej dwie depesze tego samego wieczoru: „Polska chce uniknąć wojny” albo
  „Polska ostrzega przed arogancją Rosji”. Duże media zachodnie: nic.
- **Przylot Xi do USA.** Chiny: „partnerzy, nie rywale”. BBC: czerwony dywan i bombowce z arsenału USA. Spiegel: bombowiec
  zaskoczył Trumpa, „na mema”. Guardian jako jedyny: przedłużony rozejm handlowy. Onet: komentarz, że Trump „wpada w pułapkę”.
- **Wycofanie szczepionki AstraZeneca (2024).** 39 nagłówków z 14 krajów: tylko 3 zaczynają od zakrzepów, 11 od rynku,
  polskie portale chowają powód za kliknięciem („Podano powód”).
- **Sikorski o NATO i Rosji.** Warunek „jeśli Rosja zaatakuje” znika po drodze: od „gdyby nas zaatakowała”, przez
  „Pokonalibyśmy Rosję bardzo szybko”, do „Putin upokorzony”.

## Co już działa
1. **Codzienny automat** (GitHub Actions, ok. 2 $ dziennie): 18 redakcji z 9 krajów (PL, UA, DE, UK, US, BR, CN, QA, IL),
   ok. 460 artykułów dziennie, model językowy wyciąga ramy i ton, raport dzienny z linkami do źródeł.
   Na razie daje głównie materiał wyjściowy, nie wnioski: linia bazowa (trendy) będzie po 14 dniach.
2. **Karty zdarzeń** (`events/`, ok. 15): fakt ze źródła pierwotnego, relacje z linkami, godziny publikacji,
   kopie w archiwum internetowym (jedna komenda), kontrasty i jawne zastrzeżenia.
3. **Narzędzia weryfikacji**: sprawdzanie nagłówków na stronach i w archiwum Wayback, wykrywanie zmian nagłówka
   w czasie, automatyczne zapisywanie kopii stron (dowód, jak nagłówek wyglądał).
4. **Roboczy generator krótkich filmów** (pion 1080×1920, ok. 50 s): plansze z nagłówkami, napisy, tekst lektora,
   opis ze źródłami. Są trzy wersje robocze: oligarchowie/sankcje UE, szczepionka, Sikorski. Bez głosu, muzyki i animacji.

## Czym się różnimy
- **Stan wiedzy w czasie**: pokazujemy, która wersja nagłówka była o której godzinie, z kopią w archiwum.
  Konkurent (newscord.org) porównuje redakcje, ale bez osi czasu i bez rozróżnienia wersji.
- **Obie strony**, także media rosyjskie i chińskie, podpisane (państwowe, prywatne, emigracyjne).
- **Bez komentarza i bez oceny**: hipoteza odbioru jest jawna, do oceny widza.

## Ograniczenia i ryzyka
- **Prawo**: przegląd warunków źródeł (23.09) pokazał, że BBC, Guardian i Al Jazeera zastrzegają sobie zakaz
  automatycznej analizy (TDM/AI). Cytowanie nagłówka z linkiem to przegląd prasy; automat to szara strefa.
  Media rosyjskie objęte sankcjami UE: od 25.09 używamy ich świadomie, trzeba ocenić ryzyko publikacji.
- **Koszt pracy**: karta zdarzenia to dziś 15–30 min, odcinek do publikacji dodatkowo nagranie i sprawdzenie przez człowieka.
- **Zasięg próby**: kilkanaście redakcji z RSS; szersze wyszukiwanie ręczne.

## Pytania do konsultacji
1. **Forma**: krótkie pionowe filmy (TikTok/Reels/Shorts), strona z kartami, newsletter, czy produkt dla redakcji i badaczy?
2. **Odbiorca**: szeroka publiczność („zobacz, jak inni to widzą”) czy profesjonaliści (dziennikarze, analitycy, edukacja medialna)?
3. **Rytm**: jedno zdarzenie dziennie czy tygodniowy przegląd?
4. **Model**: granty (edukacja medialna, przeciwdziałanie dezinformacji), wsparcie widzów czy licencje/API?
5. **Prawo**: jak publikować nagłówki mediów objętych sankcjami i jak ułożyć licencje z dużymi redakcjami?
