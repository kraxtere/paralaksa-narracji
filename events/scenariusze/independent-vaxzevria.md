# Independent: jeden adres, dwa nagłówki na przemian

Próbny odcinek pionowy, ok. **55 s**. Materiał: `../2024-05-07-vaxzevria-wycofanie.md` (relacja r2) i raport generowany przez `plx events check events/2024-05-07-vaxzevria-wycofanie.md` w `data/checks/2024-05-07-vaxzevria-wycofanie.md`. Raport nie jest częścią repozytorium; poniższa sekwencja pochodzi z jego ustaleń zapisanych w aktualnej karcie i korekcie poprzedniego scenariusza. Podajemy **godziny wykonania kopii, nie godziny edycji**. Na zegarze większy jest czas polski (CEST, UTC+2), mniejszy czas londyński (BST, UTC+1).

| Ujęcie / czas filmu | Tekst na ekranie | Lektor | Co widać na zegarze i w kadrze |
| --- | --- | --- | --- |
| 1 / 0–6 s | „The Independent · 8 maja 2024” / „Jeden adres. Dwa nagłówki.” | „Czy ten sam link zawsze pokazuje nam ten sam nagłówek?” | Data i dwa puste pola A/B; zegar ma podpisy **Polska CEST / Londyn BST**. Własna typografia, bez makiety serwisu i zdjęć pacjentów. |
| 2 / 6–17 s | „The Independent · wersja A · kopia 07:27 CEST” / „AstraZeneca withdrawing Covid vaccine, months after admitting rare side effect” / „tłum. robocze: miesiące po przyznaniu rzadkiego działania niepożądanego”. | „Pierwsza z opisanych kopii mówi o rzadkim działaniu niepożądanym, ale go nie nazywa.” | **07:27 CEST / 06:27 BST**. Pole A i znacznik „kopia archiwalna”; nagłówek podpisany nazwą redakcji i godziną. |
| 3 / 17–32 s | „The Independent · wersja B · kopia 07:33 CEST” / „AstraZeneca withdraws Covid vaccine worldwide after admitting it can cause rare blood clots” / „tłum. robocze: po przyznaniu rzadkiego ryzyka zakrzepów”. Potem małe etykiety: „A znów” / „B znów”. | „Sześć minut później kopia pokazuje zakrzepy. Potem wraca pierwszy wariant, a następnie znów drugi. To nie była prosta zmiana z A na B.” | Zegar przechodzi kolejno przez **07:33 / 07:39 / 08:08 CEST**, mniejszy: **06:33 / 06:39 / 07:08 BST**. Każde pojawienie się A lub B ma własny podpis „The Independent · kopia” i godzinę. Nie sugerować ciągłego wyświetlania między zapisami. |
| 4 / 32–43 s | „Już w pierwszej kopii tytuł do udostępnień: B” / „Test dwóch wersji? Pamięć podręczna? Nie ustalono.” | „Co ciekawe, tytuł do udostępnień od pierwszej kopii był wariantem B. Nie wiemy, dlaczego zapisano na przemian dwa nagłówki ani co zobaczył konkretny czytelnik.” | Obok osi kopii osobny pasek **og:title: B od 07:27 CEST**; na osi po **08:08** dopisek „08:10 CEST: kolejna kopia B”. Pytajniki przy dwóch hipotezach, bez ogłaszania testu A/B. |
| 5 / 43–55 s | „»Po« nie znaczy »z powodu«” / „UE: wniosek 5.03 → decyzja 27.03 → skutek 7.05” / „Źródła w opisie”. | „Wniosek o cofnięcie pozwolenia w Unii złożono już 5 marca. Sam nagłówek nie dowodzi przyczyny wycofania. Którą wersję wiadomości widzimy i kiedy?” | Zegar nagłówków zamraża się przy **07:27 / 07:33 / 07:39 / 08:08 CEST**; obok odrębna oś decyzji **UE**. Nie łączyć strzałką ryzyka zakrzepów z decyzją o pozwoleniu. |

## Co widz musi wiedzieć, żeby zrozumieć

- To **dwa nagłówki pod jednym adresem, widoczne na przemian w sprawdzonych kopiach**: A (06:27 BST), B (06:33), A (06:39), B (07:08); kolejna kopia z 07:10 również pokazuje B. Kopie nie mówią, kiedy dokładnie zmieniono stronę ani jak długo każda wersja była widoczna.
- Tytuł do udostępnień (`og:title`) już w kopii A z 06:27 miał wariant B. Nagłówek na stronie i metadane do udostępnień to dwa różne pola. Dane są zgodne zarówno z hipotezą testu wariantów, jak i z różnymi wersjami pamięci podręcznej; nie rozstrzygają mechanizmu.
- Oba nagłówki zawierają wzmiankę o rzadkim ryzyku; drugi nazywa je konkretniej. Wniosek AstraZeneca z 5 marca dotyczył cofnięcia **pozwolenia w UE**, a komunikat firmy o zakończeniu globalnej sprzedaży jest osobną sprawą. Rzadkie ryzyko TTS znano przed majem 2024.

## Czego nie twierdzimy

- Że redakcja celowo „wyostrzyła” nagłówek w jednej chwili, przeprowadziła potwierdzony test A/B, albo że znamy jej motyw i wpływ na czytelników.
- Że rzadkie zakrzepy odkryto w maju 2024 lub że były przyczyną wycofania produktu. Słowo „after” opisuje kolejność, nie dowodzi związku przyczynowego.
- Że archiwum pokazuje wszystkie odsłony artykułu lub że któryś wariant stale wyświetlano między chwilami wykonania kopii.

## Podstawa montażu i przed publikacją

- Artykuł: https://www.independent.co.uk/news/science/astrazeneca-covid-vaccine-withdraw-blood-clots-b2541291.html
- Kopia wariantu B z 07:10 BST: https://web.archive.org/web/20240508061007/https://www.independent.co.uk/news/science/astrazeneca-covid-vaccine-withdraw-blood-clots-b2541291.html
- Decyzja Komisji Europejskiej: https://ec.europa.eu/health/documents/community-register/2024/20240327162288/dec_162288_en.pdf
- EMA o rozpoznaniu bardzo rzadkiego TTS w 2021: https://www.ema.europa.eu/assets/en/annual-report/2021/covid-19-european-medicines-regulatory-networks-response-pandemic.html
- Pełna sekwencja kopii i pól `h1`/`og:title`: lokalny raport `data/checks/2024-05-07-vaxzevria-wycofanie.md`. Przed montażem trzeba otworzyć bezpośrednie linki do kopii A/B/A/B z raportu i sprawdzić oryginalne nagłówki oraz decyzję KE. Bez tej weryfikacji scenariusz pozostaje próbą, a animacja kart nie jest zrzutem ekranu.

W kartach nie zmieniono `sprawdzil`: **żadna relacja nie została tu oznaczona jako sprawdzona przez człowieka**.
