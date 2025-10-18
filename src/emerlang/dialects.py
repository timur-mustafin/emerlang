"""
Seeded symbol palettes ("dialects") for alternative renderings.
Useful for generating consistent but varied symbol sets.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence
import random

ASCII = list("abcdefghijklmnopqrstuvwxyz")
ASCII_UP = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITS = list("0123456789")
UNICODE_DOTS = list("∙∘•◦·⋅")
UNICODE_BLOCKS = list("░▒▓█▁▂▃▄▅▆▇")
EMOJI_SIMPLE = ["✦","✧","★","☆","♦","♣","♠","❤","☀","☁","☂","☃","☄"]

PALETTES = {
    "ascii": ASCII,
    "ascii_up": ASCII_UP,
    "digits": DIGITS,
    "dots": UNICODE_DOTS,
    "blocks": UNICODE_BLOCKS,
    "emoji": EMOJI_SIMPLE,
}

@dataclass(frozen=True)
class Dialect:
    name: str
    symbols: Sequence[str]
    seed: int

    def map_index(self, idx: int) -> str:
        """Map an integer index to a symbol in this dialect (deterministic)."""
        return self.symbols[idx % len(self.symbols)]

def build_dialect(seed: int, styles: Sequence[str] = ("ascii","digits","dots","blocks","emoji")) -> Dialect:
    rng = random.Random(seed)
    style = rng.choice(list(styles))
    symbols = list(PALETTES[style])
    rng.shuffle(symbols)  # seed-specific permutation
    return Dialect(style, tuple(symbols), seed)

def palette_from_seed(seed: int, palette: str) -> List[str]:
    rng = random.Random(seed)
    base = list(PALETTES[palette])
    rng.shuffle(base)
    return base
