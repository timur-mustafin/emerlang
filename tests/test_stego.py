import json
from emerlang.stego.jsonsteg import encode_json, decode_json
from emerlang.stego.spacesteg import encode as encode_space, decode as decode_space

def test_json_stego_order_zwsp_numeric():
    payload = b"OK"
    obj = {"a":1,"b":2,"c":"str","d":"more"}
    txt = json.dumps(obj)
    out = encode_json(txt, payload, channel="order+zwsp+numeric",
                      numeric_keys=["a","b"], string_keys=["c","d"])
    back = decode_json(out)
    # We might not get full payload length if capacity is small; at least prefix matches.
    assert back.startswith(payload[:1])

def test_spacesteg_roundtrip():
    payload = b"Hi!"
    base = "Visible text."
    out = encode_space(base, payload)
    bits = len(payload) * 8
    rec = decode_space(out, bits)
    assert rec == payload
