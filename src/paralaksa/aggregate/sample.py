"""Explicit publication cohorts and observable sample denominators (UTC)."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json


def publication_meta(conn, day):
    first = conn.execute("SELECT MIN(substr(fetched_at,1,10)) FROM articles").fetchone()[0]
    initial = first == day
    start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc) - timedelta(days=1)
    end = start + timedelta(days=2)
    rows = conn.execute("SELECT id,published_at,fetched_at FROM articles WHERE substr(fetched_at,1,10)=?", (day,)).fetchall()
    dates, eligible, late, missing, future, old24, old48 = [], [], [], [], [], [], []
    for r in rows:
        try:
            pub = datetime.fromisoformat(r['published_at']).astimezone(timezone.utc)
        except (ValueError, TypeError):
            missing.append(r['id'])
            if initial:
                eligible.append(r['id'])
            continue
        dates.append(pub.isoformat())
        fetched = datetime.fromisoformat(r['fetched_at']).astimezone(timezone.utc)
        if fetched - pub > timedelta(hours=24):
            old24.append(r['id'])
        if fetched - pub > timedelta(hours=48):
            old48.append(r['id'])
        if pub >= end or pub > fetched + timedelta(minutes=5):
            future.append(r['id'])
        elif initial or pub >= start:
            eligible.append(r['id'])
        else:
            late.append(r['id'])
    return dict(status='inicjalny' if initial else 'regularny',
                fetched_day_utc=day, publication_window_start=start.isoformat(),
                publication_window_end_exclusive=end.isoformat(),
                published_min=min(dates, default=None), published_max=max(dates, default=None),
                fetched_articles=len(rows), eligible_ids=eligible, late_articles=len(late),
                late_share=len(late)/max(1,len(rows)), missing_publication=len(missing),
                future_publication=len(future), older_than_24h=len(old24), older_than_48h=len(old48),
                today_language_allowed=bool(dates) and not missing and all(d[:10] == day for d in dates))


def sample_articles(conn, day):
    eligible = set(publication_meta(conn, day)['eligible_ids'])
    return [dict(r) for r in conn.execute('''SELECT a.*, s.country, s.name, s.metadata
        FROM articles a JOIN sources s ON s.id=a.source_id
        WHERE substr(a.fetched_at,1,10)=?''', (day,)) if r['id'] in eligible]


def sample_metadata(conn, day):
    rows = conn.execute('''SELECT a.*,s.country,s.name,s.metadata FROM articles a
        JOIN sources s ON s.id=a.source_id WHERE substr(a.fetched_at,1,10)=?''', (day,)).fetchall()
    eligible = set(publication_meta(conn, day)['eligible_ids'])
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['source_id']].append(r)
    out = []
    for sid, arts in sorted(grouped.items()):
        meta = json.loads(arts[0]['metadata'])
        genres = Counter(a['genre'] for a in arts)
        out.append(dict(source_id=sid, name=arts[0]['name'], country=arts[0]['country'],
                        language=meta.get('language'), ownership=meta.get('ownership', 'niezweryfikowane'),
                        scope=meta.get('channel_scope'), sections=sorted({a['section'] or 'unknown' for a in arts}),
                        articles=len(arts), eligible=sum(a['id'] in eligible for a in arts),
                        fulltext=sum(bool(a['fulltext']) for a in arts), lead_only=sum(not a['fulltext'] for a in arts),
                        pending=sum(a['extracted']==0 for a in arts), failed=sum(a['extracted']==2 for a in arts),
                        genres=dict(genres), genre_shares={k:v/len(arts) for k,v in genres.items()}))
    return out


def independence_count(signals):
    """Conservatively merge publisher groups linked by identical content within a segment.

    Shared wire material is not evidence for independent editorial voices. This can
    undercount publishers which also carry original reporting; expose the raw names too.
    """
    parents = {}
    content_owner = {}
    def root(x):
        parents.setdefault(x,x)
        if parents[x] != x:
            parents[x] = root(parents[x])
        return parents[x]
    for s in signals:
        source = s.publisher_group or s.source_id
        content = s.content_group or str(s.article_id)
        root(source)
        if content in content_owner:
            parents[root(source)] = root(content_owner[content])
        else:
            content_owner[content] = source
    return len({root(s) for s in parents})
