from typing import List
import random
from .tokenize import tokenize_basic, is_word, normalize
from .utils import crc8, smart_join

def _encode_fallback(word: str, codebook) -> str:
    data = word.encode("utf-8")
    hex_str = data.hex()
    glyphs = "".join(codebook.hex2glyph.get(ch, "α") for ch in hex_str)
    cc = crc8(data)
    return f"⟦{glyphs}~{cc:02x}⟧"

def encode(text: str, codebook, structure: float = 0.2, seed: int = 42) -> str:
    text = normalize(text, "NFKC")
    toks = tokenize_basic(text)
    out: List[str] = []
    for t in toks:
        if is_word(t):
            key = t.lower()
            if key in codebook.word2em:
                out.append(codebook.word2em[key])
            else:
                out.append(_encode_fallback(key, codebook))
        else:
            out.append(t)
    if structure and structure > 0:
        rnd = random.Random(seed)
        salted = []
        for tok in out:
            salted.append(tok)
            if rnd.random() < structure:
                salted.append(rnd.choice(["::","∴","⇔"]))
        out = salted
    return smart_join(out)


# --- Optional dialect mapping (non-breaking extension) ---
try:
    from .dialects import build_dialect
except Exception:
    build_dialect = None

def encode_with_dialect(text: str, codebook, structure: float = 0.2, seed: int = 42, dialect_seed: int | None = None) -> str:
    """Wraps core encode() and then remaps visible ASCII letters via a seeded palette.
    If dialect_seed is None or dialects module missing, behaves like encode().
    """
    emergent = encode(text, codebook, structure=structure, seed=seed)
    if dialect_seed is None or build_dialect is None:
        return emergent
    d = build_dialect(dialect_seed)
    # simple remap: letters a-z/A-Z replaced by palette symbols deterministically by ord
    out = []
    for ch in emergent:
        o = ord(ch)
        if 65 <= o <= 90:   # A-Z
            out.append(d.map_index(o - 65))
        elif 97 <= o <= 122:  # a-z
            out.append(d.map_index(o - 97))
        else:
            out.append(ch)
    return "".join(out)
