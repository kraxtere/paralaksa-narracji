"""Regressions for the first report and operational failure modes."""
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from paralaksa import db
from paralaksa.aggregate.metrics import compute_daily_metrics, day_signals
from paralaksa.aggregate.package import build_data_package, known_article_ids
from paralaksa.aggregate.sample import publication_meta, sample_metadata
from paralaksa.config import Budget, Source, load_themes
from paralaksa.extract.signals import pending_articles, extract_pending
from paralaksa.ingest.dedup import mark_syndication
from paralaksa.ingest.http import PoliteClient, RobotsDisallowed
from paralaksa.ingest.rss import ingest_sources
from paralaksa.report.schema import ReportOutput
from paralaksa.report.validate import validate_report, sanitize_report
from seed import DAY, article, article_with, seed_sources, seed_alarm_convergence
from report_fixtures import valid_report


def package(conn, settings):
    return build_data_package(conn, DAY, settings, load_themes())


def evidence(pkg, aid):
    s = next(s for s in pkg['dowody'] if s['article_id'] == aid)
    return {k:s[k] for k in ('signal_id','article_id','theme_id','kraj','zrodlo')}


def test_147_poll_cannot_support_sanctions(conn, settings):
    seed_sources(conn)
    # Real failure shape: an existing elections article was used for a sanctions claim.
    conn.execute("INSERT INTO articles(id,source_id,title,url,url_hash,published_at,fetched_at,extracted) VALUES "
                 "(147,'uk1','Trump approval poll','https://test/147','147',?,?,1)",
                 (DAY+'T04:00:00+00:00',DAY+'T05:00:00+00:00'))
    from seed import signal
    signal(conn,147,theme='elections_politics')
    pkg = package(conn, settings)
    r = ReportOutput.model_validate({'slabe_sygnaly':[dict(tekst='Zniesienie sankcji w analizowanym przekazie.',
        theme_id='sanctions',article_ids=[147],dowody=[evidence(pkg,147)])]})
    assert any('poza tematem' in e for e in validate_report(r,pkg,{147}))
    assert not sanitize_report(r,pkg,{147}).slabe_sygnaly


def test_false_signal_metadata_and_wrong_country_rejected(conn,settings):
    seed_sources(conn)
    ids=seed_alarm_convergence(conn)
    pkg=package(conn,settings)
    r=ReportOutput.model_validate(valid_report(ids))
    r.wzorce_zbieznosci[0].kraje[0].dowody[0].kraj='CN'
    errors=validate_report(r,pkg,known_article_ids(conn,DAY))
    assert any('niezgodne ID, temat, kraj lub źródło' in e for e in errors)
    assert not sanitize_report(r,pkg,known_article_ids(conn,DAY)).wzorce_zbieznosci


@pytest.mark.parametrize('text',[
    'Niski JS wskazuje na częściowe pokrywanie się ram.',
    'Ramy są podobne (JS=0,05).',
])
def test_js_is_not_frame_similarity(conn,settings,text):
    seed_sources(conn); ids=seed_alarm_convergence(conn); pkg=package(conn,settings)
    r=ReportOutput.model_validate(valid_report(ids)); r.w_skrocie[0].tekst=text
    assert any('JS mierzy' in e for e in validate_report(r,pkg,known_article_ids(conn,DAY)))


def test_single_source_country_requires_name_and_low_confidence(conn,settings):
    seed_sources(conn); aid=article_with(conn,'qa1'); pkg=package(conn,settings)
    r=ReportOutput.model_validate({'w_skrocie':[dict(tekst='Media QA akcentują konflikt.',pewnosc='średni',
        theme_id='ukraine_war',article_ids=[aid],dowody=[evidence(pkg,aid)])]})
    errors=validate_report(r,pkg,{aid})
    assert any('niskiej pewności' in e for e in errors)
    assert any('podaj nazwę redakcji' in e for e in errors)


def test_initial_regular_late_unknown_future_and_utc_boundary(conn,settings):
    seed_sources(conn)
    article_with(conn,'pl1',day='2026-09-22')
    valid=article_with(conn,'pl1')
    late=article_with(conn,'pl2')
    unknown=article_with(conn,'pl2')
    future=article_with(conn,'pl2')
    conn.execute("UPDATE articles SET published_at='2026-09-08T00:00:00+00:00' WHERE id=?",(late,))
    conn.execute('UPDATE articles SET published_at=NULL WHERE id=?',(unknown,))
    conn.execute("UPDATE articles SET published_at='2026-09-24T01:00:00+00:00' WHERE id=?",(future,))
    meta=publication_meta(conn,DAY)
    assert meta['status']=='regularny' and meta['eligible_ids']==[valid]
    assert (meta['late_articles'],meta['missing_publication'],meta['future_publication'])==(1,1,1)
    assert {s.article_id for s in day_signals(conn,DAY)}=={valid}
    assert not meta['today_language_allowed']
    assert publication_meta(conn,'2026-09-22')['status']=='inicjalny'
    compute_daily_metrics(conn,DAY); before=compute_daily_metrics(conn,DAY)
    assert compute_daily_metrics(conn,DAY)==before


def test_initial_includes_old_and_missing_but_never_enters_baseline(conn,settings):
    seed_sources(conn)
    aid=article_with(conn,'pl1',day='2026-09-22')
    conn.execute("UPDATE articles SET published_at='2026-09-08T00:00:00+00:00' WHERE id=?",(aid,))
    compute_daily_metrics(conn,'2026-09-22')
    article_with(conn,'pl1')
    pkg=package(conn,settings)
    assert pkg['linia_bazowa']['dni_historii']['PL']==0
    meta=publication_meta(conn,'2026-09-22')
    assert meta['older_than_48h']==1 and meta['eligible_ids']==[aid]


def test_tenfold_publisher_changes_weighting(conn,settings):
    seed_sources(conn)
    for _ in range(10): article_with(conn,'pl1',theme='energy')
    article(conn,'pl2')
    item=next(t for t in package(conn,settings)['tematy'] if t['temat']=='energy')['kraje']['PL']
    assert item['udzial']==pytest.approx(10/11,abs=.001)
    assert item['udzial_rowne_redakcje']==.5 and item['wrazliwosc_wag']


def test_agency_reprint_does_not_make_two_independent_voices(conn,settings):
    seed_sources(conn)
    for country in ('pl','ua','de'):
        for n in (1,2):
            aid=article_with(conn,f'{country}{n}',theme='energy',stance='alarm')
            # Same content within each country, translated versions deliberately not guessed.
            conn.execute('UPDATE articles SET fulltext=? WHERE id=?',(' '.join([country]*90),aid))
    mark_syndication(conn)
    pkg=package(conn,settings)
    assert pkg['zbieznosc_kandydaci']==[]
    assert all(k['n_zrodel']==1 for k in pkg['zbieznosc_slabe'][0]['kraje'])


def test_same_publisher_two_feeds_deduplicated_including_repeat_ingest(conn,settings,make_source):
    source=Source.model_validate({**make_source().model_dump(), 'feeds':[{'url':'https://example.test/a'},{'url':'https://example.test/b'}]})
    xml=b'<rss version="2.0"><channel><item><title>Headline</title><link>https://example.test/one</link></item></channel></rss>'
    with PoliteClient('test',0,transport=httpx.MockTransport(lambda r:
        httpx.Response(404) if r.url.path=='/robots.txt' else httpx.Response(200,content=xml))) as client:
        first=ingest_sources(conn,client,[source],settings,fulltext=False)
        again=ingest_sources(conn,client,[source],settings,fulltext=False)
    assert first[0].new==1 and first[0].duplicates==1 and again[0].new==0
    row=conn.execute('SELECT published_at,genre FROM articles').fetchone()
    assert row['published_at'] is None and row['genre']=='unknown'


def test_round_robin_not_dominated_by_first_country(conn):
    seed_sources(conn)
    for _ in range(20): article(conn,'pl1',extracted=0)
    article(conn,'ua1',extracted=0)
    article(conn,'de1',extracted=0)
    assert {a.country for a in pending_articles(conn,3)}=={'PL','UA','DE'}
    with pytest.raises(ValueError): pending_articles(conn,0)


def test_pending_limit_counts_deferred(conn,settings):
    from fake_llm import FakeAnthropic
    from paralaksa.extract.llm_client import LLMClient
    seed_sources(conn)
    for _ in range(20): article(conn,'pl1',extracted=0)
    stats=extract_pending(conn,LLMClient(settings.pricing,client=FakeAnthropic()),settings,load_themes(),limit=2)
    assert stats.pending==20 and stats.deferred==18 and stats.done==2


def test_new_source_cannot_activate_with_partial_gate():
    with pytest.raises(ValidationError):
        Source(id='candidate',name='Candidate',country='US',language='en',type='private',
               feeds=[{'url':'https://example.test/rss'}],verification={'feed':True,'fresh':True})
    with pytest.raises(ValidationError): Budget(max_daily_usd=0)


def test_robots_network_failure_does_not_authorize_feed():
    def handler(request): raise httpx.ReadTimeout('offline')
    with PoliteClient('test',0,transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RobotsDisallowed): client.get('https://example.test/rss')


def test_robots_transient_failure_is_retried():
    calls = []
    def handler(request):
        calls.append(str(request.url))
        if request.url.path == '/robots.txt' and calls.count(str(request.url)) == 1:
            raise httpx.ReadTimeout('blip')
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /\n')
        return httpx.Response(200, text='ok')
    with PoliteClient('test',0,transport=httpx.MockTransport(handler)) as client:
        assert client.get('https://example.test/rss').status_code == 200
    assert calls.count('https://example.test/robots.txt') == 2


def test_robots_server_error_after_retries_blocks():
    def handler(request):
        return httpx.Response(503) if request.url.path == '/robots.txt' else httpx.Response(200)
    with PoliteClient('test',0,transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RobotsDisallowed): client.get('https://example.test/rss')


def test_missing_or_corrupt_state_is_not_initialized(tmp_path):
    import importlib.util
    spec=importlib.util.spec_from_file_location('db_state',Path(__file__).parents[1]/'scripts/db_state.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    missing=tmp_path/'missing.db'
    with pytest.raises(RuntimeError,match='Brak bazy'): module.validate(missing)
    assert not missing.exists()
    missing.write_text('not SQLite')
    with pytest.raises(Exception): module.validate(missing)
    source=tmp_path/'ok.db'; c=db.connect(source);db.init_db(c);seed_sources(c);article_with(c,'pl1');c.commit();c.close()
    target=tmp_path/'copy.db';module.snapshot(source,target)
    with db.connect(target) as c:
        assert c.execute('SELECT COUNT(*) FROM signals').fetchone()[0]==1


def test_portuguese_metadata_and_unicode_survive(conn,settings):
    source=Source(id='br',name='Agência',country='BR',language='pt',type='public',active=False)
    db.upsert_sources(conn,[source])
    db.insert_article(conn,db.ArticleRow('br','https://example.test/br','br','Cooperação e sanções',
        'Discussão sobre segurança','pt',DAY+'T04:00:00+00:00',DAY+'T05:00:00+00:00',section='mundo',genre='news'))
    row=sample_metadata(conn,DAY)[0]
    assert row['language']=='pt' and row['genres']=={'news':1}


def test_doubled_source_basket_budget_keeps_all_deferrals_visible(conn,settings):
    from fake_llm import FakeAnthropic
    from paralaksa.extract.llm_client import LLMClient
    sources=[Source(id=f's{i}',name=f'Source {i}',country='US' if i%2 else 'BR',language='en',
                    type='private',active=False) for i in range(20)]
    db.upsert_sources(conn,sources)
    for source in sources:
        for n in range(2): article(conn,source.id,extracted=0)
    settings.budget.max_daily_usd=.02
    stats=extract_pending(conn,LLMClient(settings.pricing,client=FakeAnthropic()),settings,load_themes())
    assert stats.budget_stopped and stats.pending==40
    assert stats.done+stats.failed+stats.deferred==40 and stats.deferred>0
    assert sum(r['pending'] for r in sample_metadata(conn,DAY))==stats.deferred


def test_direct_time_limit_leaves_pending_records(conn,settings,monkeypatch):
    from fake_llm import FakeAnthropic
    from paralaksa.extract.llm_client import LLMClient
    from paralaksa.extract import signals
    seed_sources(conn);article(conn,'pl1',extracted=0)
    settings.extract.max_runtime_s=.1
    ticks=iter([0,1])
    monkeypatch.setattr(signals.time,'monotonic',lambda:next(ticks))
    fake=FakeAnthropic()
    stats=extract_pending(conn,LLMClient(settings.pricing,client=fake),settings,load_themes())
    assert stats.deferred==1 and stats.done==0 and not fake.messages.calls


def test_synthesis_retry_is_not_sent_without_budget(conn,settings):
    from fake_llm import FakeAnthropic, message
    from paralaksa.extract.llm_client import LLMClient
    from paralaksa.report.synthesize import run_synthesis
    seed_sources(conn);ids=seed_alarm_convergence(conn);pkg=package(conn,settings)
    # The first (unusable) response consumes almost all budget; no unbudgeted correction call.
    fake=FakeAnthropic(lambda p:message('bad JSON',1_495_000,0))
    _,stats=run_synthesis(conn,LLMClient(settings.pricing,client=fake),settings,pkg,known_article_ids(conn,DAY),
                          now=datetime(2026,9,23,tzinfo=timezone.utc))
    assert len(fake.messages.calls)==1 and stats.warnings


def test_two_distinct_reprints_still_do_not_create_independent_publishers(conn,settings):
    seed_sources(conn)
    for source in ['pl1','pl2']:
        for n in [1,2]:
            aid=article_with(conn,source,theme='energy',stance='alarm')
            conn.execute('UPDATE articles SET fulltext=? WHERE id=?',(('wire'+str(n)+' ')*100,aid))
    mark_syndication(conn)
    assert compute_daily_metrics(conn,DAY)[0]['n_sources']==1


def test_llm_payload_is_compact_but_validator_keeps_full_registry(conn, settings):
    from paralaksa.report.synthesize import llm_payload
    seed_sources(conn); seed_alarm_convergence(conn)
    pkg = package(conn, settings)
    payload = llm_payload(pkg)
    text = json.dumps(payload, ensure_ascii=False)
    assert 'content_group' not in text and 'publisher_group' not in text
    assert payload['dowody']['kolumny'] == ['signal_id', 'article_id', 'theme_id', 'kraj', 'zrodlo']
    assert len(payload['dowody']['wiersze']) == len(pkg['dowody'])
    assert 'content_group' in pkg['dowody'][0]  # pakiet walidatora bez zmian
