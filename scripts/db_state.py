"""Validate or take a consistent SQLite snapshot. Never initialize a missing state implicitly."""
import argparse
from pathlib import Path
import sqlite3


def validate(path):
    if not path.is_file():
        raise RuntimeError('Brak bazy: przywróć zaszyfrowany backup; nie uruchamiaj init-db.')
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Uszkodzona baza SQLite')
        for table in ('schema_version','sources','articles','signals','daily_metrics','api_usage','reports'):
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                raise RuntimeError(f'Brak tabeli {table}')
        if conn.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('Naruszona spójność kluczy obcych')


def summary(path):
    """Counts to compare against the last successful run after a restore."""
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as conn:
        version = conn.execute('SELECT version FROM schema_version').fetchone()[0]
        arts, first, last, pending = conn.execute(
            'SELECT COUNT(*), MIN(fetched_at), MAX(fetched_at), COALESCE(SUM(extracted=0),0) FROM articles').fetchone()
        signals = conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        reports = [r[0] for r in conn.execute('SELECT date FROM reports ORDER BY date')]
    return (f'schemat v{version}; artykuły {arts} (nieekstrahowane {pending}), pobrane {first} — {last}; '
            f'sygnały {signals}; raporty {len(reports)}: {", ".join(reports[-5:])}')


def snapshot(source, target):
    validate(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    validate(target)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    p.add_argument('--snapshot', type=Path)
    args = p.parse_args()
    if args.snapshot:
        snapshot(args.source, args.snapshot)
    else:
        validate(args.source)
    print('SQLite: integralność i schemat OK')
    print(summary(args.snapshot or args.source))
