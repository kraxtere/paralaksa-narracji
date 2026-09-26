"""BigQuery access to the public GDELT dataset: every query is dry-run first and refused above the byte limit."""
from __future__ import annotations

import os
import re
from datetime import date
from typing import Any

GKG = "`gdelt-bq.gdeltv2.gkg_partitioned`"
DEFAULT_MAX_GB = 5.0
# nagłówki w Extras są zakodowane encjami HTML (także cyrylica, arabski, chiński)
UNESCAPE_UDF = r"""CREATE TEMP FUNCTION unesc(s STRING) RETURNS STRING LANGUAGE js AS r'''
  if (!s) return s;
  return s.replace(/&#x([0-9a-fA-F]+);/g, (m, h) => String.fromCodePoint(parseInt(h, 16)))
          .replace(/&#(\d+);/g, (m, d) => String.fromCodePoint(parseInt(d, 10)))
          .replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
          .replace(/&amp;/g, '&');
''';
"""
TITLE = r"unesc(REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>'))"
LANG = r"IFNULL(REGEXP_EXTRACT(TranslationInfo, r'srclc:(\w+)'), 'eng')"
ENTITIES = "CONCAT(IFNULL(V2Persons, ''), ';', IFNULL(V2Organizations, ''))"

LANG_PL = {
    "eng": "angielski", "pol": "polski", "rus": "rosyjski", "ukr": "ukraiński", "deu": "niemiecki", "fra": "francuski",
    "spa": "hiszpański", "ita": "włoski", "por": "portugalski", "tur": "turecki", "ara": "arabski", "heb": "hebrajski",
    "fas": "perski", "zho": "chiński", "jpn": "japoński", "kor": "koreański", "hin": "hindi", "lit": "litewski",
    "lav": "łotewski", "est": "estoński", "ces": "czeski", "slk": "słowacki", "hun": "węgierski", "ron": "rumuński",
    "bul": "bułgarski", "srp": "serbski", "hrv": "chorwacki", "bos": "bośniacki", "slv": "słoweński", "ell": "grecki",
    "nld": "niderlandzki", "swe": "szwedzki", "nor": "norweski", "dan": "duński", "fin": "fiński", "sqi": "albański",
    "mkd": "macedoński", "bel": "białoruski", "kat": "gruziński", "hye": "ormiański", "axe": "azerski", "aze": "azerski",
    "urd": "urdu", "ben": "bengalski", "ind": "indonezyjski", "vie": "wietnamski", "tha": "tajski", "cat": "kataloński",
}


def day_literal(value: str | date) -> str:
    """Validated YYYY-MM-DD for SQL (never interpolate unchecked text)."""
    return date.fromisoformat(str(value)).isoformat()


def sql_string(text: str) -> str:
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def phrase_regex(part: str) -> str:
    """Case-insensitive literal for RE2 inside a raw SQL string (quotes become 'any character')."""
    return re.escape(part.lower().strip()).replace("'", ".").replace('"', ".")


class BigQueryRunner:
    def __init__(self, project: str | None = None, max_gb: float = DEFAULT_MAX_GB):
        self.project = project or os.environ.get("GCP_PROJECT")
        if not self.project:
            raise RuntimeError("brak projektu Google Cloud: ustaw GCP_PROJECT w .env albo podaj --projekt")
        try:
            from google.cloud import bigquery
        except ImportError as e:
            raise RuntimeError('brak biblioteki BigQuery: pip install -e ".[gdelt]"') from e
        self._bq = bigquery
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", self.project)   # bez ostrzeżenia google.auth
        self.client = bigquery.Client(project=self.project)
        self.max_bytes = int(max_gb * 1e9)
        self.scanned = 0

    def run(self, sql: str) -> list[dict[str, Any]]:
        dry = self.client.query(sql, job_config=self._bq.QueryJobConfig(dry_run=True, use_query_cache=False))
        if dry.total_bytes_processed > self.max_bytes:
            raise RuntimeError(f"zapytanie przeszukałoby {dry.total_bytes_processed / 1e9:.1f} GB, limit "
                               f"{self.max_bytes / 1e9:.1f} GB (--max-gb)")
        job = self.client.query(sql, job_config=self._bq.QueryJobConfig(maximum_bytes_billed=self.max_bytes))
        rows = [dict(r) for r in job.result()]
        self.scanned += job.total_bytes_processed or 0
        return rows
