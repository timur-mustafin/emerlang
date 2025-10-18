import sys, json, typer
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

app = typer.Typer(help="Emerlang extra tools: stego & crypto (educational).")

@app.command("stego-json-encode")
def stego_json_encode(
    infile: Path = typer.Option(..., "--in", help="Input JSON file"),
    outfile: Path = typer.Option(..., "--out", help="Output JSON file"),
    payload: str = typer.Option(..., "--payload", help="Bytes to hide (UTF-8)"),
    channel: str = typer.Option("order+zwsp+numeric", "--channel"),
    num_keys: str = typer.Option("", "--num-keys", help="Comma list of numeric keys"),
    str_keys: str = typer.Option("", "--str-keys", help="Comma list of string keys"),
):
    from .stego.jsonsteg import encode_json
    txt = infile.read_text(encoding="utf-8")
    nkeys = [k for k in num_keys.split(",") if k] if num_keys else []
    skeys = [k for k in str_keys.split(",") if k] if str_keys else []
    out = encode_json(txt, payload.encode("utf-8"), channel=channel,
                      numeric_keys=nkeys, string_keys=skeys)
    outfile.write_text(out, encoding="utf-8")
    typer.echo(f"Written {outfile}")

@app.command("stego-json-decode")
def stego_json_decode(
    infile: Path = typer.Option(..., "--in", help="JSON file with hidden data"),
):
    from .stego.jsonsteg import decode_json
    txt = infile.read_text(encoding="utf-8")
    data = decode_json(txt)
    sys.stdout.write(data.decode("utf-8", errors="replace"))

@app.command("stego-space-encode")
def stego_space_encode(
    infile: Path = typer.Option(..., "--in", help="Input text file"),
    outfile: Path = typer.Option(..., "--out", help="Output text file"),
    payload: str = typer.Option(..., "--payload", help="Bytes to hide (UTF-8)"),
):
    from .stego.spacesteg import encode as sencode
    text = infile.read_text(encoding="utf-8")
    out = sencode(text, payload.encode("utf-8"))
    outfile.write_text(out, encoding="utf-8")
    typer.echo(f"Written {outfile}")

@app.command("stego-space-decode")
def stego_space_decode(
    infile: Path = typer.Option(..., "--in", help="Text file with hidden data"),
    bytes_len: int = typer.Option(..., "--bytes", help="Number of hidden bytes to read"),
):
    from .stego.spacesteg import decode as sdecode
    text = infile.read_text(encoding="utf-8")
    data = sdecode(text, bytes_len*8)
    sys.stdout.write(data.decode("utf-8", errors="replace"))

@app.command("crypto-xor")
def crypto_xor(
    infile: Path = typer.Option(..., "--in", help="Input file (bytes)"),
    outfile: Path = typer.Option(..., "--out", help="Output file"),
    key: str = typer.Option(..., "--key", help="Key (UTF-8)"),
    nonce: str = typer.Option("", "--nonce", help="Nonce (UTF-8)"),
):
    from .crypto import xor_stream
    data = infile.read_bytes()
    out = xor_stream(data, key.encode("utf-8"), nonce.encode("utf-8"))
    outfile.write_bytes(out)
    typer.echo(f"Written {outfile}")

if __name__ == "__main__":
    app()
