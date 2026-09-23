"""A valid synthesis answer for the `seed_alarm_convergence` data."""

from __future__ import annotations

import copy
import json


def valid_report(ids: dict[str, list[int]], trend: str = "brak linii bazowej") -> dict:
    line = lambda c, k: {"kraj": k, "n_zrodel": 2, "rama": "zagrożenie ze wschodu", "stance": "alarm",  # noqa: E731
                         "article_ids": ids[c]}
    report = {
        "w_skrocie": [{"tekst": "Analizowane źródła z PL i UA przedstawiają Rosję jako zagrożenie.",
                       "pewnosc": "średni", "article_ids": ids["pl"] + ids["ua"]}],
        "wzorce_zbieznosci": [{
            "temat": "security_defense", "kierunek": "alarm i zbrojenia",
            "kraje": [line("pl", "PL"), line("ua", "UA"), line("de", "DE"), line("uk", "UK")],
            "wspolny_kierunek": "przekaz sugeruje rosnące poczucie zagrożenia",
            "sygnaly_przeciwne": {"tekst": "Brytyjskie medium akcentuje odstraszanie.", "article_ids": ids["counter"]},
            "pewnosc": {"poziom": "średni", "uzasadnienie": "4 kraje, 8 źródeł, 8 artykułów"},
            "trend": trend,
        }],
        "rozbieznosci": [],
        "autoobraz": [],
        "co_sie_przesuwa": [],
        "nieobecne_w_polsce": [],
        "slabe_sygnaly": [{"tekst": "Pojedynczy sygnał uspokajający w UK.", "article_ids": ids["counter"]}],
    }

    mapping = {}
    for c in ('pl','ua','de','uk'):
        for n, aid in enumerate(ids[c],1):
            mapping[aid] = (c.upper(), f'{c}{n}')
    for aid in ids['counter']:
        mapping[aid] = ('UK','uk2')
    def add(obj):
        if isinstance(obj, dict):
            if 'article_ids' in obj:
                obj['dowody'] = [dict(signal_id=aid, article_id=aid, theme_id='security_defense',
                    kraj=mapping[aid][0], zrodlo=mapping[aid][1]) for aid in obj['article_ids']]
                if 'tekst' in obj:
                    obj['theme_id'] = 'security_defense'
            for value in list(obj.values()):
                add(value)
        elif isinstance(obj,list):
            for value in obj:
                add(value)
    add(report)
    return report


def as_text(report: dict) -> str:
    return "```json\n" + json.dumps(report, ensure_ascii=False) + "\n```"


def mutate(report: dict, fn) -> dict:
    r = copy.deepcopy(report)
    fn(r)
    return r
