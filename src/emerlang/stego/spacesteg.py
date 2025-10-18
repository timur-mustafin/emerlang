"""
Zero-width / whitespace-based steganography over plain text.

We append an invisible trailer that starts with a sentinel and then encodes bits
using a tiny alphabet of invisible characters.
"""
from __future__ import annotations
from typing import List

# Invisible alphabet
SENTINEL = "\u2063\u2063"  # invisible separator x2
ALPH = ["\u200b", "\u200c"]  # zero-width space, zero-width non-joiner

def _bytes_to_bits(data: bytes) -> List[int]:
    return [(b >> i) & 1 for b in data for i in range(8)]

def _bits_to_bytes(bits: List[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte |= (bits[i + j] & 1) << j
        out.append(byte)
    return bytes(out)

def encode(text: str, payload: bytes) -> str:
    bits = _bytes_to_bits(payload)
    trail = "".join(ALPH[b] for b in bits)
    return text + SENTINEL + trail

def decode(text: str, bit_len: int) -> bytes:
    pos = text.rfind(SENTINEL)
    if pos == -1:
        return b""
    enc = text[pos + len(SENTINEL):]
    bits = []
    for ch in enc[:bit_len]:
        bits.append(1 if ch == ALPH[1] else 0)
    return _bits_to_bytes(bits)
