"""Read-only technical source audit. Rights and translation quality require human review.

Usage: python scripts/check_sources.py --output data/source-checks.json
Never activates sources and never stores article bodies in the audit output.
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from paralaksa import db
from paralaksa.config import load_sources, load_settings
from paralaksa.ingest.http import PoliteClient
from paralaksa.ingest.rss import parse_feed


def check(source):
    cfg = load_settings().ingest
    result = {'source': source.id, 'checked_at': db.to_iso(db.utc_now()), 'feeds': []}
    with PoliteClient(cfg.user_agent, cfg.per_domain_delay_s, 12) as client:
        for feed in source.feeds:
            row = {'url': feed.url}
            try:
                response = client.get(feed.url)
                entries = parse_feed(response.content)
                dated = [e for e in entries if e.published]
                recent = [e for e in dated if timedelta(0) <= db.utc_now()-e.published <= timedelta(hours=48)]
                row.update(http=response.status_code, robots=True, entries=len(entries), fresh_48h=len(recent),
                           latest=max((db.to_iso(e.published) for e in dated), default=None),
                           lead_lengths=[len(e.lead or '') for e in entries[:5]])
            except Exception as exc:
                row['error'] = f'{type(exc).__name__}: {exc}'[:350]
            result['feeds'].append(row)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', action='append')
    args = parser.parse_args()
    sources = [s for s in load_sources() if (s.id in args.source if args.source else bool(s.verification))]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(check, sources))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    for r in results:
        print(r['source'], [(f.get('entries'),f.get('fresh_48h'),f.get('error')) for f in r['feeds']])
