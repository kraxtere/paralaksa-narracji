"""Pure statistics used by aggregation: z-score, Jensen–Shannon divergence, coarse stance direction."""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, Literal

Direction = Literal["negatywny", "pozytywny", "neutralny"]

STANCES = ("alarm", "krytyka", "neutralny", "uspokojenie", "poparcie")
# Zgrubny kierunek zamiast embeddingów etykiet ram (SPEC §9.3; embeddingi w KM4 razem z emergent.py).
DIRECTIONS: dict[str, Direction] = {
    "alarm": "negatywny", "krytyka": "negatywny",
    "poparcie": "pozytywny", "uspokojenie": "pozytywny",
    "neutralny": "neutralny",
}


def coarse_direction(stance: str) -> Direction:
    return DIRECTIONS.get(stance, "neutralny")


def z_score(today: float, history: list[float], min_history: int) -> float | None:
    """(today - mean) / sample std of `history`; None without enough history or with zero variance."""
    if len(history) < max(min_history, 2):
        return None
    mean = sum(history) / len(history)
    var = sum((x - mean) ** 2 for x in history) / (len(history) - 1)
    if var <= 1e-12:
        return None
    return (today - mean) / math.sqrt(var)


def distribution(values: Iterable[str], keys: Iterable[str] = STANCES) -> dict[str, float]:
    """Relative frequencies over `keys` (all keys present, zeros included)."""
    counts = Counter(values)
    total = sum(counts[k] for k in keys)
    return {k: (counts[k] / total if total else 0.0) for k in keys}


def js_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    """Jensen–Shannon divergence with log base 2 (0 = identical, 1 = disjoint)."""
    keys = set(p) | set(q)

    def kl(a: dict[str, float], m: dict[str, float]) -> float:
        return sum(a.get(k, 0.0) * math.log2(a.get(k, 0.0) / m[k]) for k in keys if a.get(k, 0.0) > 0)

    m = {k: (p.get(k, 0.0) + q.get(k, 0.0)) / 2 for k in keys}
    return max(0.0, 0.5 * kl(p, m) + 0.5 * kl(q, m))
