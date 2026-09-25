---
# Karta zdarzenia: „Jedno zdarzenie. Dwie opowieści.”
# Jednostką jest zdarzenie; relacje dopinamy w miarę poszukiwań. Wypełnia człowiek po lekturze.
# Pełnych tekstów tu nie kopiujemy: nagłówek maks. 15 słów, reszta własnymi słowami.
id: RRRR-MM-DD-krotka-nazwa
tytul: neutralny opis zdarzenia
status: kandydat           # kandydat | w_pracy | gotowy | opublikowany | odrzucony
powod_odrzucenia: null     # gdy odrzucony: dlaczego (to też wiedza na przyszłość)
droga: od_zdarzenia        # od_wiadomosci | od_zdarzenia
dziedzina: []              # np. bezpieczenstwo, gospodarka, rolnictwo, energetyka, zdrowie
forma: dwie_opowiesci      # dwie_opowiesci | kilka_perspektyw | os_czasu

fakt:                      # tylko to, co potwierdza źródło pierwotne
  czas: null               # ISO 8601 ze strefą, np. 2026-01-09T14:00+01:00
  opis: null
  zrodlo_pierwotne: null   # komunikat, dokument, oficjalne dane

stan_wiedzy_zmienial_sie: false
os_czasu: []               # gdy true: [{czas: ..., co_wiadomo: ..., zrodlo: r1}]

watki: []                  # opowieści: od czego zaczyna nagłówek, np. [{id: w1, nazwa: 'Partnerzy, nie rywale', opis: '...'}]
                           # strona (plx site) układa relacje w kolumny wątków; każda relacja ma jedno pole watek

relacje:
  - id: r1
    kraj: null
    kto: null
    typ: null              # państwowe | publiczne | prorządowe | prywatne | emigracyjne (null, gdy nieustalony)
    rola: redakcja         # redakcja | agencja | strona_sprawy (rząd, firma, organizacja)
    gatunek: null          # wiadomosc | relacja_na_zywo | wywiad | analiza | komentarz | przeglad | komunikat
    link: null
    publikacja: null       # ISO 8601 ze strefą
    aktualizacja: null     # ISO 8601 ze strefą, jeśli redakcja ją podaje
    porownywana_wersja: null   # której wersji dotyczy opis: publikacja / aktualizacja z godziną
    archiwum: {link: null, wykonano: null}   # kopia późniejsza niż porównywana wersja nic nie dowodzi
    naglowek: null         # oryginał, maks. 15 słów
    tlumaczenie: null
    zostawia_z: null       # jedno zdanie: z jaką myślą zostaje odbiorca
    watek: null            # id z listy watki
    sprawdzil: null        # kto otworzył link i przeczytał; bez tego relacja nie idzie do odcinka

kontrasty:                 # jedno zdarzenie może mieć kilka kontrastów między różnymi parami
  - miedzy: [r1, r2]
    rodzaj: null           # rozne_interesy | kolejnosc_informacji | dobor_slow | czyj_glos | pominiecie
    opis: null
    zastrzezenia: null     # np. „te liczby dotyczą różnych rzeczy”, „B to komunikat strony sprawy”

jak_szukano: []            # nasza baza, GDELT, wyszukiwarka + języki
---

## Fakt
Co się stało, tylko według źródła pierwotnego. Bez ocen i bez skutków, które dopiero ktoś przewiduje.

## Przekaz
Jakie perspektywy są w relacjach: co na pierwszym planie, jakie słowa, czyj głos, jaki kontekst dodano i jakiego brakuje,
w którym momencie opis zaczyna budować spokój, lęk, oburzenie albo nadzieję. Przy stronie sprawy (rząd, firma)
nazywamy to wprost: to stanowisko zainteresowanej strony, nie relacja redakcji.

## Hipoteza odbioru
Pokazywana widzowi do oceny: „A może zostawić odbiorcę z myślą…, B z myślą…”.
Czego nie twierdzimy: nie przypisujemy redakcjom intencji i nie rozstrzygamy, która wersja jest prawdziwa.

## Ilustracja
Co pokazują nasze kadry lub rysunki. To ilustracja perspektywy, a nie dowód skutków zdarzenia; w odcinku oznaczona jako ilustracja.
Bez fotorealistycznych „zdjęć” z wydarzenia.

## Uczciwość odcinka
- [ ] Porównujemy wersje z tym samym stanem wiedzy albo pokazujemy godziny i korekty (forma `os_czasu`).
- [ ] Widać, ile relacji znaleziono; wybrane dwie to skrajne wydźwięki, nie „typowe”.
- [ ] Ten sam gatunek (nie depesza przeciw felietonowi) albo różnica nazwana wprost; rola strony sprawy nazwana.
- [ ] Każda liczba sprawdzona: do czego się odnosi (np. pracownicy bezpośredni vs łańcuch dostaw).
- [ ] Linki do wszystkich relacji w opisie odcinka. Bez źródeł objętych sankcjami UE.

## Notatki z pilota
- Czas pracy:
- Co było najbardziej żmudne (kandydat do automatyzacji):
- Czego zabrakło w karcie:
