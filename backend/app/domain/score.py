from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Weights:
    demand: float = 0.35
    gap: float = 0.25
    invest: float = 0.15
    underserved: float = 0.20
    already_funded: float = 0.15


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def priority_score(
    *,
    ticket_count: int,
    unique_voices: int,
    indicator_value: float | None,
    direction: str | None,
    is_aspirational: bool,
    already_funded_hint: float,
    weights: Weights = Weights(),
) -> dict:
    demand = clamp01((ticket_count * 0.6 + unique_voices * 0.4) / 12.0)
    if indicator_value is None:
        gap = 0.5
        gap_known = False
    else:
        gap_known = True
        norm = clamp01(indicator_value / 100.0)
        gap = 1.0 - norm if direction == "higher_better" else norm
    underserved = 1.0 if is_aspirational else 0.25
    invest = 0.4
    funded = clamp01(already_funded_hint)
    s = (
        weights.demand * demand
        + weights.gap * gap
        + weights.invest * invest
        + weights.underserved * underserved
        - weights.already_funded * funded
    )
    return {
        "score": round(s, 4),
        "features": {
            "demand": round(demand, 4),
            "gap": round(gap, 4),
            "gap_known": gap_known,
            "invest": invest,
            "underserved": underserved,
            "already_funded": funded,
            "ticket_count": ticket_count,
            "unique_voices": unique_voices,
            "indicator_value": indicator_value,
        },
        "weights": asdict(weights),
    }
