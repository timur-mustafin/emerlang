"""
Structural markers and probabilistic templates.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence, Tuple, Any, Dict
import random

@dataclass(frozen=True)
class Markers:
    start: str
    end: str
    sep: str = "|"

def make_markers(seed: int) -> Markers:
    rng = random.Random(seed)
    # Pick some unicode-ish delimiters deterministically
    starts = ["<<", "[[", "{{", "⟪", "《", "«"]
    ends = [">>", "]]", "}}", "⟫", "》", "»"]
    seps = ["|", "·", "—", ":", "⋮"]
    return Markers(start=rng.choice(starts), end=rng.choice(ends), sep=rng.choice(seps))

def weighted_choice(items: Sequence[Tuple[Any, float]], seed: int) -> Any:
    """Deterministic weighted choice based on seed."""
    rng = random.Random(seed)
    values, weights = zip(*items)
    total = sum(weights)
    x = rng.random() * total
    upto = 0.0
    for v, w in items:
        if upto + w >= x:
            return v
        upto += w
    return values[-1]

def select_template(templates: Sequence[str], weights: Sequence[float], seed: int) -> str:
    return weighted_choice(list(zip(templates, weights)), seed)

def probabilistic_sequence(choices: Sequence[Tuple[str, float]], count: int, seed: int) -> List[str]:
    return [weighted_choice(choices, seed + i) for i in range(count)]
