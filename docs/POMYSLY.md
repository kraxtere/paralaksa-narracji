# Pomysły i drobiazgi do zrobienia zbiorczo

Lista właściciela (od 2026-10-17). Dopisujemy hasło od ręki, robimy partiami. Zrobione: `[x]` + data + commit.

- [x] 2026-10-17 **Wybór kraju także na dole strony kraju** (`D/kraje.html`, `#KRAJ`). Ten sam pasek pod treścią, po przełączeniu
  lądujemy na początku nowego kraju. Opcjonalnie przycisk „następny kraj →".
- [x] 2026-10-17 **Przycisk „udostępnij"** (`aria-label`, `src/paralaksa/site/assets/pasek.js`). Okno systemowe na telefonie,
  kopiowanie linku + „Skopiowano" tam, gdzie go nie ma. Decyzja 2026-10-17: udostępniamy zawsze **widok do tego miejsca
  na naszej stronie** (kotwica), nigdy bezpośrednio oryginał; do oryginału przechodzi się już od nas. Przycisk
  **subtelny**, przy pojedynczym artykule (np. artykuły z Polski) oraz w pasku obok logo (bieżąca strona; na stronie
  głównej = cała Paralaksa, opis: „Paralaksa narracji: jak prasa z 17 krajów opisuje to samo wydarzenie. Codzienny
  przegląd w obrazkach.").
- [x] 2026-10-17 **Oś czasu kraju: przycisk „zobacz całą oś czasu" jest słabo widoczny.** Zrobić go wyraźniejszym, okrągłym,
  zachęcającym (zdarzenia w kraju, `kraje/KRAJ.html`, `scripts/v2/kraje.py`).
- [x] 2026-10-17 **Oś czasu: etykieta ciągu/tematu na karcie wygląda na nieklikalną** (a klika się w nią, żeby filtrować, tak jak
  w „chmurkę" u góry). Powiększyć, zaokrąglić, nadać bąbelkowy wygląd klikalnego elementu (kolor/obrys, kursor, hover,
  fokus), kolory tylko przez zmienne CSS, estetycznie i spójnie z chmurką filtrów.
- [x] 2026-10-17 **Archiwum (wyszukiwarka artykułów): kolorystyka odstaje od reszty strony.** Dopasować do palety strony.
- [x] 2026-10-17 **Powitanie i przewodnik po zakładkach** (powitanie raz, spotlight + panel przy dolnej krawędzi na telefonie, flaga
  `plx-przewodnik-v1` w `localStorage`, stały link „O Paralaksie"). Teksty chmurek i uwagi wdrożeniowe: wynik burzy
  mózgów Codex (gpt-6.1-sol) z 2026-10-17, `docs/PRZEWODNIK_BURZA_MOZGOW.md`. **Kolejność kroków (decyzja właściciela):**
  1) „Dzień po dniu" (oś czasu: najważniejsze zdarzenie dzień po dniu), 2) „Tego dnia" (tematy dnia, o czym pisało się
  najwięcej), 3) reszta: „Tonacje", „Autoportret", „Czym żyją kraje", „Archiwum". Nazwy w chmurkach tylko takie, jak na
  stronie. Opisujemy przekaz, nie fakty; zastrzeżenia w „O Paralaksie".
