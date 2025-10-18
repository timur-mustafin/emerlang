"""
Toy crypto helpers (NOT secure) — educational use only.

This module provides a simple XOR stream "cipher" and a pure-Python ChaCha20-like
keystream generator. Both are **NOT SECURE** and should never be used to protect
real secrets. They are here for reversible transforms and demos.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Iterable

BLOCK = 64  # bytes per keystream block

def _blake_keystream(key: bytes, nonce: bytes, counter: int) -> bytes:
    """Derive a pseudorandom BLOCK-sized chunk using BLAKE2b.
    Not cryptographically secure as used here; for demos only.
    """
    h = blake2b(digest_size=BLOCK)
    h.update(key)
    h.update(b"|")
    h.update(nonce)
    h.update(b"|")
    h.update(counter.to_bytes(8, "little"))
    return h.digest()


def xor_stream(data: bytes, key: bytes, nonce: bytes = b"", start_counter: int = 0) -> bytes:
    """XOR data with a deterministic BLAKE-derived keystream.
    Reversibility: xor_stream(xor_stream(data, k, n), k, n) == data
    NOT secure.
    """
    out = bytearray()
    counter = start_counter
    i = 0
    while i < len(data):
        ks = _blake_keystream(key, nonce, counter)
        chunk = data[i:i + BLOCK]
        out.extend((c ^ ks[j]) for j, c in enumerate(chunk))
        i += len(chunk)
        counter += 1
    return bytes(out)


# Minimal, pure-Python ChaCha20 keystream (slow; demo only)
def _rotl32(x: int, n: int) -> int:
    return ((x << n) & 0xffffffff) | (x >> (32 - n))


def _qr(state, a, b, c, d):
    state[a] = (state[a] + state[b]) & 0xffffffff; state[d] ^= state[a]; state[d] = _rotl32(state[d], 16)
    state[c] = (state[c] + state[d]) & 0xffffffff; state[b] ^= state[c]; state[b] = _rotl32(state[b], 12)
    state[a] = (state[a] + state[b]) & 0xffffffff; state[d] ^= state[a]; state[d] = _rotl32(state[d], 8)
    state[c] = (state[c] + state[d]) & 0xffffffff; state[b] ^= state[c]; state[b] = _rotl32(state[b], 7)


def _chacha_block(key: bytes, counter: int, nonce: bytes) -> bytes:
    const = b"expand 32-byte k"
    assert len(key) == 32 and len(nonce) == 12
    def w32(b): return int.from_bytes(b, "little")
    state = [
        w32(const[0:4]), w32(const[4:8]), w32(const[8:12]), w32(const[12:16]),
        w32(key[0:4]), w32(key[4:8]), w32(key[8:12]), w32(key[12:16]),
        w32(key[16:20]), w32(key[20:24]), w32(key[24:28]), w32(key[28:32]),
        counter & 0xffffffff,
        w32(nonce[0:4]), w32(nonce[4:8]), w32(nonce[8:12]),
    ]
    working = state[:]
    for _ in range(10):  # 20 rounds (10 double rounds)
        _qr(working, 0, 4, 8, 12)
        _qr(working, 1, 5, 9, 13)
        _qr(working, 2, 6, 10, 14)
        _qr(working, 3, 7, 11, 15)
        _qr(working, 0, 5, 10, 15)
        _qr(working, 1, 6, 11, 12)
        _qr(working, 2, 7, 8, 13)
        _qr(working, 3, 4, 9, 14)
    out = [(working[i] + state[i]) & 0xffffffff for i in range(16)]
    return b"".join(x.to_bytes(4, "little") for x in out)  # 64 bytes


def chacha20_xor(data: bytes, key: bytes, nonce: bytes, counter: int = 0) -> bytes:
    """XOR with ChaCha20 keystream (pure-Python, slow; NOT for real security)."""
    if len(key) != 32 or len(nonce) != 12:
        raise ValueError("key must be 32 bytes, nonce must be 12 bytes")
    out = bytearray()
    i = 0
    ctr = counter
    while i < len(data):
        ks = _chacha_block(key, ctr, nonce)
        chunk = data[i:i+64]
        out.extend((c ^ ks[j]) for j, c in enumerate(chunk))
        i += len(chunk)
        ctr += 1
    return bytes(out)
