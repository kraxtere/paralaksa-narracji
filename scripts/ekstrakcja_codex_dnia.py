"""Ekstrakcja sygnałów przez Codex (domyślnie Luna) wsadami, zamiast DeepSeek: lokalnie, na wskazanej bazie.

Wybiera artykuły z articles.extracted w (0, 2) pobrane w podanych dniach UTC, zostawia tylko te z okna publikacji dnia
(`publication_meta`, jak `skip_out_of_window`), reszta dostaje extracted=3. Wsady po N artykułów (kilka naraz), walidacja
jak w produkcji (`parse_extraction` z dosłownym evidence_span), ponowienie raz dla artykułów bez poprawnych sygnałów,
zapis `save_signals` (extracted=1; pusta lista też jest poprawnym wynikiem). Trwała porażka po ponowieniu: extracted=2.
Błąd API / brak wpisu w odpowiedzi: stan bez zmian (można puścić ponownie, skrypt jest idempotentny).

  python scripts/ekstrakcja_codex_dnia.py --db data/prod.db --dni 2026-10-06 2026-10-07            # SUCHA PRÓBA (bez zapisu)
  python scripts/ekstrakcja_codex_dnia.py --db data/prod.db --dni 2026-10-06 --zapisz               # zapis do bazy
Opcje: --model codex:gpt-6-luna:medium  --wsad 25  --rownolegle 0 (bez limitu, start co 10 s)  --dodatek scripts/v2/prompt_luna_v3.md  --limit N (próba)
Nigdy effort „ultra”. Prompt produkcyjny DeepSeek (prompts/extract_signals.md) nie jest zmieniany: reguły dla Codexa to
poprawka tematu relewantności w pamięci + plik dodatku.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from dotenv import load_dotenv  # noqa: E402

from paralaksa import db  # noqa: E402
from paralaksa.aggregate.sample import publication_meta  # noqa: E402
from paralaksa.config import load_settings, load_themes  # noqa: E402
from paralaksa.extract import signals as S  # noqa: E402
from paralaksa.extract.codex_client import CodexClient  # noqa: E402
from paralaksa.extract.llm_client import LLMRequest, build_client  # noqa: E402
from paralaksa.extract.schema import parse_extraction  # noqa: E402

THROTTLE_RE = re.compile(r"\b429\b|rate.?limit|usage limit|too many requests|disconnect|connection (?:reset|closed|refused)|stream (?:closed|error)", re.I)
OLD = "Jeśli artykuł nie dotyczy geopolityki ani stosunków międzynarodowych, zwróć pustą listę."
NEW = ("Artykuł o polityce, wyborach, protestach, budżecie, podatkach lub gospodarce DOWOLNEGO państwa (także kraju źródła, "
       "także gdy kraj zdarzenia jest inny niż kraj źródła) jest relewantny i ma dostać sygnały. Pustą listę zwróć tylko dla tematów "
       "naprawdę niepolitycznych (plotki, celebryci, zdrowie, przyroda, lifestyle), także zagranicznych.")
FORMAT = ('\n\nStosuj wszystkie zasady OSOBNO do każdego artykułu. Zwróć wyłącznie JSON: {"results": [{"article_id": N, '
          '"signals": [ ...sygnały jak wyżej... ]}]} z jednym wpisem na każdy podany article_id (pusta lista signals, jeśli brak).\n\n')


def build_head(run: "S._Run", dodatek: Path | None) -> str:
    head = run.template.split("\n---\n")[0].replace("{themes}", run.themes_text)
    head = head.replace("Otrzymujesz jeden artykuł prasowy (dane źródła i treść na końcu tego promptu)",
                        "Otrzymujesz kilka artykułów prasowych (dane źródła i treść każdego poniżej)")
    assert OLD in head, "prompt produkcyjny się zmienił: sprawdź regułę relewantności"
    head = head.replace(OLD, NEW)
    if dodatek:
        head = head.replace("Zwróć 0–5 sygnałów.", "Zwróć 0–5 sygnałów na artykuł.")
        head = head.replace("Zwróć wyłącznie JSON:", dodatek.read_text(encoding="utf-8") + "\nZwróć wyłącznie JSON:", 1)
        assert "DODATKOWE ZASADY" in head
    return head


def block(a, max_words: int) -> str:
    text = " ".join(a.fulltext.split()[:max_words]) if a.fulltext else "(niedostępny)"
    return (f"=== ARTYKUŁ article_id={a.id} ===\nKraj źródła: {a.country}\nTyp źródła: {a.source_type}\n"
            f"Materiał: {S.MATERIAL_NOTES[a.source_depth]}\nTytuł: {a.title}\nLead: {a.lead or '(brak)'}\nTekst: {text}\n")


def parse_batch(text: str) -> dict[int, list]:
    """{article_id: signals}; przy zepsutym JSON-ie wyłuskuje kolejne obiekty {"article_id"...} osobno."""
    import re
    txt = text.strip().removeprefix("```json").removesuffix("```").strip()
    try:   # raw_decode toleruje śmieci po obiekcie (np. znacznik </final>)
        data, _ = json.JSONDecoder().raw_decode(txt[txt.index("{"):])
        return {int(r["article_id"]): r.get("signals", []) for r in data["results"]}
    except Exception:
        got = {}
        for m in re.finditer(r'\{\s*"article_id"', txt):
            try:
                r, _ = json.JSONDecoder().raw_decode(txt, m.start())
                got[int(r["article_id"])] = r.get("signals", [])
            except Exception:
                pass
        return got


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--dni", nargs="+", required=True, help="dni pobrania UTC, np. 2026-10-06")
    ap.add_argument("--model", default="codex:gpt-6-luna:medium")
    ap.add_argument("--wsad", type=int, default=25)
    ap.add_argument("--rownolegle", type=int, default=0, help="max procesów naraz; 0 = bez limitu (wsady co 10 s)")
    ap.add_argument("--dodatek", default="scripts/v2/prompt_luna_v3.md", help="plik dodatkowych reguł dla Codexa ('' = brak)")
    ap.add_argument("--limit", type=int, default=None, help="tylko N pierwszych artykułów (próba)")
    ap.add_argument("--zapisz", action="store_true", help="zapisz do bazy (domyślnie sucha próba)")
    args = ap.parse_args()
    if "ultra" in args.model.lower():
        sys.exit("effort ultra jest zabroniony")

    load_dotenv()
    settings, themes = load_settings(ROOT / "config"), load_themes(ROOT / "config")
    conn = db.connect(args.db)
    db.init_db(conn)
    client = CodexClient(timeout_s=1800) if args.model.startswith("codex") else build_client(args.model, settings.pricing, 5, 1)
    run = S._Run(conn, client, settings, themes, S.DEFAULT_PROMPT, db.utc_now())
    dodatek = Path(args.dodatek) if args.dodatek else None
    head = build_head(run, dodatek)
    version = f"codex-batch@{hashlib.sha256(head.encode()).hexdigest()[:12]}"

    todo_ids: list[int] = []
    skip_ids: list[int] = []
    for day in args.dni:
        eligible = set(publication_meta(conn, day)["eligible_ids"])
        for (i,) in conn.execute("SELECT id FROM articles WHERE extracted IN (0, 2) AND substr(fetched_at,1,10) = ? ORDER BY id", (day,)):
            (todo_ids if i in eligible else skip_ids).append(i)
    if args.limit:
        todo_ids = todo_ids[:args.limit]
    wanted = set(todo_ids)
    arts = {a.id: a for a in _load(conn, todo_ids)}
    order = [i for i in todo_ids if i in arts]
    batches = [order[k:k + args.wsad] for k in range(0, len(order), args.wsad)]
    print(f"baza {args.db} | dni {args.dni} | do ekstrakcji {len(order)} | poza oknem {len(skip_ids)} | wsadów {len(batches)} po {args.wsad}"
          f" | model {args.model} | rownolegle {args.rownolegle} | prompt {version}")
    if not args.zapisz:
        print("SUCHA PRÓBA: bez wywołań modelu i bez zapisu. Dodaj --zapisz.")
        return 0

    if skip_ids:
        conn.executemany("UPDATE articles SET extracted = ?, extract_error = ? WHERE id = ?",
                         [(S.SKIPPED_OUT_OF_WINDOW, S.SKIP_NOTE, i) for i in skip_ids])
        conn.commit()

    def call(ids: list[int]):
        prompt = head + FORMAT + "\n".join(block(arts[i], settings.ingest.max_fulltext_words) for i in ids)
        t = time.time()
        res = client.complete(LLMRequest(custom_id="b", model=args.model, max_tokens=60000,
                                         messages=[{"role": "user", "content": prompt}]))
        return ids, res, time.time() - t

    stats = dict(ok=0, puste=0, bledy_czesciowe=0, ponowienie=0, trwale=0, bez_zmiany=0, sygnaly=0, odrzucone_sygnaly=0,
                 throttle=0, szczyt_procesow=0)
    t0 = time.time()

    def handle(ids, res, final, retry):
        """Wynik jednego wsadu -> zapis w bazie (tylko z głównego wątku)."""
        got = parse_batch(res.text) if res.ok else {}
        for i in ids:
            a = arts[i]
            if i not in got:
                if final:
                    stats["bez_zmiany"] += 1
                else:
                    retry.append(i)
                continue
            out = parse_extraction(json.dumps({"signals": got[i]}, ensure_ascii=False), run.theme_ids, run.source_text(a))
            stats["odrzucone_sygnaly"] += len(out.errors)
            if out.errors and not out.signals:
                if final:
                    S.mark_article(conn, i, 2, "walidacja po ponowieniu: " + "; ".join(out.errors)[:900])
                    stats["trwale"] += 1
                else:
                    retry.append(i)
                continue
            note = ("częściowo odrzucone: " + "; ".join(out.errors))[:1000] if out.errors else None
            S.save_signals(conn, a, out.signals, args.model, version, run.now, note)
            stats["ok"] += 1; stats["sygnaly"] += len(out.signals)
            stats["puste"] += not out.signals; stats["bledy_czesciowe"] += bool(out.errors)
        conn.commit()

    def pass_(batch_list: list[list[int]], final: bool) -> tuple[list[int], bool]:
        """Jak paski.run_all: wszystkie wsady w kolejce, każdy w osobnym procesie, start co `gap` s, bez sztywnego limitu
        (--rownolegle 0). Po pierwszym 429/usage limit/zerwaniu połączenia: max 4 naraz co 20 s i ponowienie tego wsadu raz;
        powtórka przy 4 naraz: czyste przerwanie (gotowe wsady zapisane, reszta czeka na ponowne uruchomienie).
        Zwraca (artykuły do ponowienia, czy przerwano)."""
        import queue as _q
        import threading
        state = dict(width=args.rownolegle or 10**6, gap=10, slowed=False, stop=False)
        todo = [(b, 0) for b in batch_list]
        done: _q.Queue = _q.Queue()
        running = 0
        retry: list[int] = []
        last = 0.0

        def work(ids, tries):
            try:
                _ids, res, dt = call(ids)
            except BaseException as e:   # nie gubić wsadu przy wyjątku wątku
                from paralaksa.extract.llm_client import LLMResult
                res, dt = LLMResult(custom_id="b", model=args.model, mode="direct"), 0.0
                res.error = f"wyjątek: {e}"
            done.put((ids, tries, res, dt))

        while todo or running:
            while not done.empty():
                ids, tries, res, dt = done.get()
                running -= 1
                err = (res.error or "") if not res.ok else ""
                if err and THROTTLE_RE.search(err):
                    stats["throttle"] += 1
                    print(f"  THROTTLE ({err[-160:].strip()!r}) wsad {len(ids)} art.", flush=True)
                    if state["slowed"]:
                        state["stop"] = True
                        retry.extend(i for b, _ in todo for i in b)
                        todo.clear()
                    else:
                        state.update(width=min(state["width"], 4), gap=20, slowed=True)
                        if tries == 0:
                            todo.append((ids, 1))
                            continue
                    if state["stop"]:
                        retry.extend(ids)
                    continue
                print(f"  wsad {len(ids)} art. {dt:.0f}s ok={res.ok}" + (f" błąd: {err[-120:].strip()!r}" if err else ""), flush=True)
                handle(ids, res, final, retry)
            if state["stop"]:
                if not running:
                    break
                time.sleep(1)
                continue
            if todo and running < state["width"] and time.time() - last >= state["gap"]:
                ids, tries = todo.pop(0)
                threading.Thread(target=work, args=(ids, tries), daemon=True).start()
                running += 1
                stats["szczyt_procesow"] = max(stats["szczyt_procesow"], running)
                last = time.time()
            else:
                time.sleep(1)
        return retry, state["stop"]

    retry, stopped = pass_(batches, final=False)
    if retry and not stopped:
        stats["ponowienie"] = len(retry)
        print(f"ponowienie {len(retry)} artykułów (wsady po 20)", flush=True)
        _, stopped = pass_([retry[k:k + 20] for k in range(0, len(retry), 20)], final=True)
    n = conn.execute("SELECT COUNT(*) FROM articles WHERE extracted IN (0,2) AND id IN (%s)" % ",".join(map(str, wanted or [0]))).fetchone()[0]
    print(json.dumps(dict(wall_s=round(time.time() - t0), zostalo_do_ponowienia=n, przerwano=stopped, **stats), ensure_ascii=False))
    return 3 if stopped else 0


def _load(conn, ids: list[int]):
    if not ids:
        return []
    q = ",".join(map(str, ids))
    rows = conn.execute(f"""SELECT a.id, a.source_id, s.country, s.type, a.title, a.lead, a.fulltext
        FROM articles a JOIN sources s ON s.id = a.source_id WHERE a.id IN ({q})""").fetchall()
    return [S.ArticleForExtraction(*r) for r in rows]


if __name__ == "__main__":
    sys.exit(main())
