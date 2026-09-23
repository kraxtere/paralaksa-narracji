"""A valid synthesis answer for the `seed_alarm_convergence` data."""

from __future__ import annotations

import copy
import json


def valid_report(ids: dict[str, list[int]], trend: str = "brak linii bazowej") -> dict:
    line = lambda c, k: {"kraj": k, "n_zrodel": 2, "rama": "zagrożenie ze wschodu", "stance": "alarm",  # noqa: E731
                         "article_ids": ids[c]}
    return {
        "w_skrocie": [{"tekst": "Media czterech krajów przedstawiają Rosję jako zagrożenie.",
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


def as_text(report: dict) -> str:
    return "```json\n" + json.dumps(report, ensure_ascii=False) + "\n```"


def mutate(report: dict, fn) -> dict:
    r = copy.deepcopy(report)
    fn(r)
    return r
