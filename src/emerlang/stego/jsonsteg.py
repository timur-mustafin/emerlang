"""
JSON steganography channels:
- key-order channel (uses stable dict insertion order)
- numeric-params epsilon tweaks on whitelisted keys
- zero-width spaces embedded into string values

**Caveats:** JSON parsers that re-order keys will destroy the key-order channel.
Zero-width embedding mutates visible strings (still visually identical). Use responsibly.
"""
from __future__ import annotations
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Tuple, Optional
import json
import math

ZWSP = "\u200b"  # zero-width space

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

# ---------- Key-order channel ----------

def encode_key_order(obj: Dict[str, Any], bits: List[int]) -> Tuple[OrderedDict, int]:
    """Encode bits by pairwise swapping adjacent keys whenever bit==1.
    Capacity ≈ len(keys)-1 bits.
    Returns new OrderedDict and number of bits consumed.
    """
    keys = list(obj.keys())
    new_items = list(obj.items())
    consumed = 0
    for i in range(0, len(keys)-1):
        if consumed >= len(bits):
            break
        if bits[consumed] == 1:
            # swap positions i and i+1
            new_items[i], new_items[i+1] = new_items[i+1], new_items[i]
        consumed += 1
    return OrderedDict(new_items), consumed

def decode_key_order(obj: Dict[str, Any], original_keys: List[str], bit_len: int) -> List[int]:
    """Recover bits by checking if adjacent pairs are swapped relative to original order."""
    current_keys = list(obj.keys())
    bits = []
    for i in range(0, min(len(original_keys)-1, bit_len)):
        swapped = int(current_keys[i] != original_keys[i])
        bits.append(swapped)
        # If swapped, the object now has original_keys[i+1] at position i
        # adjust expected sequence virtually (skip ahead)
    return bits

# ---------- Numeric epsilon channel ----------

def encode_numeric(obj: Dict[str, Any], bits: List[int], keys_whitelist: List[str], epsilon: float = 1e-6) -> int:
    """Encode bits by applying ±epsilon to numeric values at whitelisted keys in iteration order."""
    consumed = 0
    for k in keys_whitelist:
        if k in obj and isinstance(obj[k], (int, float)):
            if consumed >= len(bits):
                break
            b = bits[consumed]
            if b == 1:
                obj[k] = float(obj[k]) + epsilon
            else:
                obj[k] = float(obj[k])
            consumed += 1
    return consumed

def decode_numeric(obj: Dict[str, Any], keys_whitelist: List[str], bit_len: int, epsilon: float = 1e-6) -> List[int]:
    bits = []
    for i, k in enumerate(keys_whitelist):
        if len(bits) >= bit_len:
            break
        v = obj.get(k, None)
        if isinstance(v, (int, float)):
            bits.append(1 if (abs(float(v) - int(v)) >= epsilon/2) else 0)
    return bits

# ---------- Zero-width string channel ----------

def encode_zwsp(obj: Dict[str, Any], bits: List[int], keys_whitelist: List[str]) -> int:
    consumed = 0
    for k in keys_whitelist:
        if consumed >= len(bits):
            break
        if k in obj and isinstance(obj[k], str):
            obj[k] = obj[k] + (ZWSP if bits[consumed] == 1 else "")
            consumed += 1
    return consumed

def decode_zwsp(obj: Dict[str, Any], keys_whitelist: List[str], bit_len: int) -> List[int]:
    bits = []
    for k in keys_whitelist:
        if len(bits) >= bit_len:
            break
        v = obj.get(k, None)
        if isinstance(v, str):
            bits.append(1 if v.endswith(ZWSP) else 0)
    return bits

# ---------- High-level helpers ----------

def encode_json(json_text: str, payload: bytes, *, channel: str = "order+zwsp+numeric",
                numeric_keys: Optional[List[str]] = None, string_keys: Optional[List[str]] = None) -> str:
    obj = json.loads(json_text, object_pairs_hook=OrderedDict)
    bits = _bytes_to_bits(payload)

    # Keep original order for decoding reference
    original_keys = list(obj.keys())

    consumed_total = 0
    if "order" in channel and isinstance(obj, OrderedDict):
        new_obj, used = encode_key_order(obj, bits[consumed_total:])
        obj = new_obj
        consumed_total += used

    if "zwsp" in channel and string_keys:
        used = encode_zwsp(obj, bits[consumed_total:], string_keys)
        consumed_total += used

    if "numeric" in channel and numeric_keys:
        used = encode_numeric(obj, bits[consumed_total:], numeric_keys)
        consumed_total += used

    # Store meta to aid decoding
    obj["_steg_meta"] = {
        "bit_len": consumed_total,
        "channel": channel,
        "orig_keys": original_keys,
        "num_keys": numeric_keys or [],
        "str_keys": string_keys or [],
    }
    return json.dumps(obj, ensure_ascii=False)


def decode_json(json_text: str) -> bytes:
    obj = json.loads(json_text, object_pairs_hook=OrderedDict)
    meta = obj.get("_steg_meta", {})
    bit_len = int(meta.get("bit_len", 0))
    channel = meta.get("channel", "")
    orig_keys = meta.get("orig_keys", [])
    num_keys = meta.get("num_keys", [])
    str_keys = meta.get("str_keys", [])

    bits_collected: List[int] = []
    if "order" in channel and orig_keys:
        bits_collected += decode_key_order(obj, orig_keys, bit_len - len(bits_collected))
    if "zwsp" in channel and str_keys and len(bits_collected) < bit_len:
        rem = bit_len - len(bits_collected)
        bits_collected += decode_zwsp(obj, str_keys, rem)
    if "numeric" in channel and num_keys and len(bits_collected) < bit_len:
        rem = bit_len - len(bits_collected)
        bits_collected += decode_numeric(obj, num_keys, rem)

    return _bits_to_bytes(bits_collected)
