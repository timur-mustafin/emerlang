import sys
from pathlib import Path
import typer

# Best-effort UTF-8 on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from .codebook import Codebook
from .encoder import encode as encode_core
from .decoder import decode as decode_core

app = typer.Typer(no_args_is_help=False, help="EmerLang — emergent-looking codec. Not crypto.")

def _read_text_any(path: str) -> str:
    data = Path(path).read_bytes()
    for enc in ("utf-8", "utf-8-sig", "utf-16-le", "utf-16-be"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")

@app.command()
def build(codebook_path: str = typer.Argument(..., help="Path to save codebook.json"),
          corpus: str = typer.Argument(..., help="Path to training corpus"),
          vocab: int = typer.Option(500, "--vocab", help="Vocab size"),
          seed: int = typer.Option(42, "--seed", help="Deterministic seed")):
    cb = Codebook.train(corpus_path=corpus, vocab_size=vocab, seed=seed, tokenizer="basic", ngram_max=1)
    cb.save(codebook_path)
    typer.echo(f"[OK] Codebook saved to {codebook_path} (vocab={vocab}, seed={seed})")

@app.command()
def encode(codebook_path: str = typer.Argument(..., help="Path to codebook.json"),
           infile: str = typer.Option(None, "--in", "--infile", help="Input text (file). If omitted, reads from stdin."),
           outfile: str = typer.Option(None, "--out", "--outfile", help="Output emergent file. If omitted, prints to stdout."),
           structure: float = typer.Option(0.2, "--structure", min=0.0, max=1.0),
           seed: int = typer.Option(42, "--seed")):
    cb = Codebook.load(codebook_path)
    if infile:
        text = _read_text_any(infile)
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        text = typer.prompt("Paste text")
    emergent = encode_core(text, cb, structure=structure, seed=seed)
    if outfile:
        Path(outfile).write_text(emergent, encoding="utf-8")
        typer.echo(f"[OK] Encoded → {outfile}")
    else:
        print(emergent)

@app.command()
def decode(codebook_path: str = typer.Argument(..., help="Path to codebook.json"),
           infile: str = typer.Option(None, "--in", "--infile", help="Input emergent (file). If omitted, reads from stdin."),
           outfile: str = typer.Option(None, "--out", "--outfile", help="Output plain text file. If omitted, prints to stdout.")):
    cb = Codebook.load(codebook_path)
    if infile:
        emergent = _read_text_any(infile)
    elif not sys.stdin.isatty():
        emergent = sys.stdin.read()
    else:
        emergent = typer.prompt("Paste emergent text")
    plain = decode_core(emergent, cb)
    if outfile:
        Path(outfile).write_text(plain, encoding="utf-8")
        typer.echo(f"[OK] Decoded → {outfile}")
    else:
        print(plain)

@app.command()
def interactive():
    typer.echo("🛰️ EmerLang interactive — not crypto; art/edu demo.\n")
    typer.echo("Choose: [1] build  [2] encode  [3] decode  [q] quit")
    while True:
        choice = typer.prompt("Your choice", default="q").strip().lower()
        if choice in ("q","quit","exit"):
            raise typer.Exit()
        elif choice == "1":
            codebook_path = typer.prompt("Save codebook to", default="codebook.json")
            vocab = int(typer.prompt("Vocab size", default="500"))
            seed = int(typer.prompt("Seed", default="42"))
            typer.echo("Paste corpus (end with empty line):")
            lines = []
            import sys as _sys
            while True:
                line = _sys.stdin.readline()
                if not line or line.strip() == "":
                    break
                lines.append(line.rstrip("\n"))
            corpus_text = "\n".join(lines) or typer.prompt("Or paste a single-line corpus")
            tmp = Path(".tmp_corpus.txt"); tmp.write_text(corpus_text, encoding="utf-8")
            cb = Codebook.train(str(tmp), vocab_size=vocab, seed=seed)
            cb.save(codebook_path)
            typer.echo(f"[OK] Codebook saved to {codebook_path}")
        elif choice == "2":
            codebook_path = typer.prompt("Path to codebook.json", default="codebook.json")
            structure = float(typer.prompt("Structure (0..1)", default="0.2"))
            seed = int(typer.prompt("Seed", default="42"))
            typer.echo("Paste text (end with empty line):")
            lines = []
            import sys as _sys
            while True:
                line = _sys.stdin.readline()
                if not line or line.strip() == "":
                    break
                lines.append(line.rstrip("\n"))
            text = "\n".join(lines) or typer.prompt("Or paste a single line")
            cb = Codebook.load(codebook_path)
            emergent = encode_core(text, cb, structure=structure, seed=seed)
            print("\n--- emergent ---\n"+emergent+"\n---------------\n")
        elif choice == "3":
            codebook_path = typer.prompt("Path to codebook.json", default="codebook.json")
            typer.echo("Paste emergent text (end with empty line):")
            lines = []
            import sys as _sys
            while True:
                line = _sys.stdin.readline()
                if not line or line.strip() == "":
                    break
                lines.append(line.rstrip("\n"))
            emergent = "\n".join(lines) or typer.prompt("Or paste a single line")
            cb = Codebook.load(codebook_path)
            plain = decode_core(emergent, cb)
            print("\n--- decoded ---\n"+plain+"\n--------------\n")
        else:
            typer.echo("Enter 1/2/3 or q")

if __name__ == "__main__":
    app()


# ==== Advanced commands with dialect/stego/crypto toggles ====
from .encoder import encode_with_dialect as _encode_with_dialect
from .stego.jsonsteg import encode_json as _json_encode, decode_json as _json_decode
from .stego.spacesteg import encode as _space_encode, decode as _space_decode
from .crypto import xor_stream as _xor_stream
import base64, json

@app.command("encode-adv")
def encode_adv(
    text: str = typer.Option("", "--text", help="Plain input text (if empty, read from stdin)"),
    codebook_path: Path = typer.Option(..., "--codebook", help="Path to codebook.json"),
    out_text: Path = typer.Option(None, "--out-text", help="Write emergent text here (if not using stego/xor)"),
    dialect_seed: int = typer.Option(None, "--dialect-seed", help="Apply dialect remap if provided"),
    # space-stego
    space_carrier_in: Path = typer.Option(None, "--space-in", help="Carrier text file for space-stego"),
    space_out: Path = typer.Option(None, "--space-out", help="Output text file with hidden payload"),
    # json-stego
    json_in: Path = typer.Option(None, "--json-in", help="Carrier JSON file"),
    json_out: Path = typer.Option(None, "--json-out", help="Output JSON file with hidden payload"),
    json_num_keys: str = typer.Option("", "--json-num-keys", help="Comma separated numeric keys"),
    json_str_keys: str = typer.Option("", "--json-str-keys", help="Comma separated string keys"),
    json_channel: str = typer.Option("order+zwsp+numeric", "--json-channel", help="Channels to use"),
    # xor "encryption"
    xor_key: str = typer.Option(None, "--xor-key", help="Toy XOR key (UTF-8). If set, write bytes."),
    xor_nonce: str = typer.Option("", "--xor-nonce", help="Toy XOR nonce (UTF-8)"),
    xor_out: Path = typer.Option(None, "--xor-out", help="Output file for XORed bytes"),
):
    cb = Codebook.load(codebook_path)
    content = text or sys.stdin.read()
    emergent = _encode_with_dialect(content, cb, dialect_seed=dialect_seed)

    # Apply routes in priority: JSON stego > space stego > XOR > plain text
    if json_in and json_out:
        nkeys = [k for k in json_num_keys.split(",") if k]
        skeys = [k for k in json_str_keys.split(",") if k]
        src = json_in.read_text(encoding="utf-8")
        out = _json_encode(src, emergent.encode("utf-8"), channel=json_channel, numeric_keys=nkeys, string_keys=skeys)
        json_out.write_text(out, encoding="utf-8")
        typer.echo(f"Wrote JSON with hidden payload: {json_out}")
        return

    if space_carrier_in and space_out:
        carrier = space_carrier_in.read_text(encoding="utf-8")
        out = _space_encode(carrier, emergent.encode("utf-8"))
        space_out.write_text(out, encoding="utf-8")
        typer.echo(f"Wrote space-stego file: {space_out}")
        return

    if xor_key and xor_out:
        data = emergent.encode("utf-8")
        out = _xor_stream(data, xor_key.encode("utf-8"), xor_nonce.encode("utf-8"))
        xor_out.write_bytes(out)
        typer.echo(f"Wrote XORed bytes: {xor_out}")
        return

    # fallback: just write text
    if out_text:
        out_text.write_text(emergent, encoding="utf-8")
        typer.echo(f"Wrote emergent text: {out_text}")
    else:
        sys.stdout.write(emergent)


@app.command("decode-adv")
def decode_adv(
    codebook_path: Path = typer.Option(..., "--codebook", help="Path to codebook.json"),
    # Sources (pick one)
    in_text: Path = typer.Option(None, "--in-text", help="File with emergent text (UTF-8)"),
    json_in: Path = typer.Option(None, "--json-in", help="JSON file with hidden payload"),
    space_in: Path = typer.Option(None, "--space-in", help="Text file with hidden payload"),
    # If using space-in: bytes length
    space_bytes: int = typer.Option(0, "--space-bytes", help="Number of bytes to extract from space-stego"),
    # If using XOR
    xor_key: str = typer.Option(None, "--xor-key", help="Toy XOR key (UTF-8)"),
    xor_nonce: str = typer.Option("", "--xor-nonce", help="Toy XOR nonce (UTF-8)"),
):
    cb = Codebook.load(codebook_path)

    payload: bytes | None = None
    if json_in:
        src = json_in.read_text(encoding="utf-8")
        payload = _json_decode(src)
        text = payload.decode("utf-8", errors="replace")
        plain = decode_core(text, cb)
        sys.stdout.write(plain)
        return

    if space_in and space_bytes > 0:
        carrier = space_in.read_text(encoding="utf-8")
        payload = _space_decode(carrier, space_bytes * 8)
        text = payload.decode("utf-8", errors="replace")
        plain = decode_core(text, cb)
        sys.stdout.write(plain)
        return

    if in_text:
        emergent = in_text.read_text(encoding="utf-8")
    else:
        emergent = sys.stdin.read()

    if xor_key:
        b = bytes(emergent, "utf-8", "replace")
        b = _xor_stream(b, xor_key.encode("utf-8"), xor_nonce.encode("utf-8"))
        emergent = b.decode("utf-8", errors="replace")

    plain = decode_core(emergent, cb)
    sys.stdout.write(plain)


# === Backward-compatible encode/decode with new flags ===
# These override earlier command definitions with the same names.
from .encoder import encode_with_dialect as _enc_dialect
from .stego.spacesteg import encode as _sp_encode, decode as _sp_decode
from .stego.jsonsteg import encode_json as _js_encode, decode_json as _js_decode
from .crypto import xor_stream as _xor_stream

@app.command("encode")
def encode_cmd(
    text: str = typer.Option("", "--text", help="Plain input text (if empty, read from stdin)"),
    codebook: Path = typer.Option(..., "--codebook", help="Path to codebook.json"),
    out_text: Path = typer.Option(None, "--out-text", help="Write emergent text (default: stdout)"),
    # new options
    dialect_seed: int = typer.Option(None, "--dialect-seed", help="Apply dialect remap if provided"),
    space_in: Path = typer.Option(None, "--space-in", help="Carrier text file for space-stego"),
    space_out: Path = typer.Option(None, "--space-out", help="Output text file with hidden payload"),
    json_in: Path = typer.Option(None, "--json-in", help="Carrier JSON file"),
    json_out: Path = typer.Option(None, "--json-out", help="Output JSON file with hidden payload"),
    json_num_keys: str = typer.Option("", "--json-num-keys", help="Comma list of numeric keys"),
    json_str_keys: str = typer.Option("", "--json-str-keys", help="Comma list of string keys"),
    json_channel: str = typer.Option("order+zwsp+numeric", "--json-channel"),
    xor_key: str = typer.Option(None, "--xor-key", help="Toy XOR key (UTF-8); if set, write bytes"),
    xor_nonce: str = typer.Option("", "--xor-nonce", help="Toy XOR nonce (UTF-8)"),
    xor_out: Path = typer.Option(None, "--xor-out", help="Output file for XORed bytes"),
):
    cb = Codebook.load(codebook)
    content = text or sys.stdin.read()
    emergent = (_enc_dialect(content, cb, dialect_seed=dialect_seed)
                if dialect_seed is not None and _enc_dialect else
                encode_core(content, cb))

    # Routes: JSON > Space > XOR > plain
    if json_in and json_out:
        nkeys = [k for k in json_num_keys.split(",") if k]
        skeys = [k for k in json_str_keys.split(",") if k]
        src = json_in.read_text(encoding="utf-8")
        out = _js_encode(src, emergent.encode("utf-8"), channel=json_channel, numeric_keys=nkeys, string_keys=skeys)
        json_out.write_text(out, encoding="utf-8")
        return

    if space_in and space_out:
        carrier = space_in.read_text(encoding="utf-8")
        out = _sp_encode(carrier, emergent.encode("utf-8"))
        space_out.write_text(out, encoding="utf-8")
        return

    if xor_key and xor_out:
        data = emergent.encode("utf-8")
        out = _xor_stream(data, xor_key.encode("utf-8"), xor_nonce.encode("utf-8"))
        xor_out.write_bytes(out)
        return

    if out_text:
        out_text.write_text(emergent, encoding="utf-8")
    else:
        sys.stdout.write(emergent)


@app.command("decode")
def decode_cmd(
    codebook: Path = typer.Option(..., "--codebook", help="Path to codebook.json"),
    in_text: Path = typer.Option(None, "--in-text", help="Plain emergent text file (default: stdin)"),
    json_in: Path = typer.Option(None, "--json-in", help="JSON file with hidden payload"),
    space_in: Path = typer.Option(None, "--space-in", help="Text file with hidden payload"),
    space_bytes: int = typer.Option(0, "--space-bytes", help="Hidden bytes to read for space-stego"),
    xor_key: str = typer.Option(None, "--xor-key", help="Toy XOR key (UTF-8)"),
    xor_nonce: str = typer.Option("", "--xor-nonce", help="Toy XOR nonce (UTF-8)"),
):
    cb = Codebook.load(codebook)

    if json_in:
        src = json_in.read_text(encoding="utf-8")
        payload = _js_decode(src)
        emergent = payload.decode("utf-8", "replace")
        plain = decode_core(emergent, cb)
        sys.stdout.write(plain)
        return

    if space_in:
        carrier = space_in.read_text(encoding="utf-8")
        bits = space_bytes * 8 if space_bytes > 0 else len(carrier) * 8
        payload = _sp_decode(carrier, bits)
        emergent = payload.decode("utf-8", "replace")
        plain = decode_core(emergent, cb)
        sys.stdout.write(plain)
        return

    emergent = in_text.read_text(encoding="utf-8") if in_text else sys.stdin.read()
    if xor_key:
        b = _xor_stream(emergent.encode("utf-8", "replace"),
                        xor_key.encode("utf-8"),
                        xor_nonce.encode("utf-8"))
        emergent = b.decode("utf-8", "replace")
    plain = decode_core(emergent, cb)
    sys.stdout.write(plain)
