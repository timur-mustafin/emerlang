import os
from emerlang.crypto import xor_stream, chacha20_xor

def test_xor_roundtrip():
    data = b"hello world" * 100
    key = b"key123"
    nonce = b"nonce"
    enc = xor_stream(data, key, nonce)
    dec = xor_stream(enc, key, nonce)
    assert dec == data

def test_chacha_roundtrip():
    data = b"\x00\x01\x02\x03" * 256
    key = b"k"*32
    nonce = b"n"*12
    enc = chacha20_xor(data, key, nonce, counter=7)
    dec = chacha20_xor(enc, key, nonce, counter=7)
    assert dec == data
