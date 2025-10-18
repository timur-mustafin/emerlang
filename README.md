# 🛰️ EmerLang (emerlang)

**Not cryptography.** Educational art-tool that turns text into an “emergent-looking” protocol.

## Install (dev)
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -e .
```

## CLI
```bash
# 1) Build a codebook
emerlang build codebook.json examples/corpora/mini_en.txt --vocab 300 --seed 42

# 2) Encode
emerlang encode codebook.json --in examples/corpora/mini_en.txt --out out.em --structure 0.2

# 3) Decode
emerlang decode codebook.json --in out.em --out roundtrip.txt
```

Stdin/Stdout (Windows-safe if your console is UTF-8):
```powershell
'Hello' | emerlang encode codebook.json > out.em
Get-Content out.em -Raw | emerlang decode codebook.json > roundtrip.txt
```

## GUI
```bash
emerlang-gui
# or:
python -m emerlang.gui.emerlang_gui
```
**Demo tab** animates two encoded messages on the top row (A/B) and reveals their decoded forms on the bottom row after ~2s. The output reflects the actual codebook & structure/seed you choose.

## Preview

![Build Tab](./docs/buildtab.png)
![Encode Tab](./docs/encodetab.png)
![Decode Tab](./docs/decodetab.png)
![Demo Tab](./docs/demotab.png)

## TODO
- GUI update for XOR, dialects and stego

## Notes
- Input file decoding is tolerant (UTF-8 / UTF-8 BOM / UTF-16 LE/BE).
- Decoder understands both glyph blocks (⟦…~cc⟧) and Greek+digits tokens (e.g., Πε13).
- This is an art/education demo, **not** secure encryption.


## Extra tools (stego & crypto)

After installing in editable mode:

```bash
emerlang-extra --help
emerlang-stego-json stego-json-encode --in demo.json --out out.json --payload "secret" --num-keys a,b --str-keys c,d
emerlang-stego-json stego-json-decode --in out.json
emerlang-stego-space stego-space-encode --in demo.txt --out out.txt --payload "Hi"
emerlang-stego-space stego-space-decode --in out.txt --bytes 2
emerlang-crypto crypto-xor --in file.bin --out enc.bin --key test --nonce n
```
