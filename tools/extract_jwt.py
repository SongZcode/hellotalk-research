"""extract_jwt.py — 从抓包 dump / api.log 里抽出最新的客户端 JWT 存到 artifacts/mitm/jwt.txt

用法: python tools\extract_jwt.py [dump文件...]
"""
import json
import pathlib
import re
import sys
import zlib

OUT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\jwt.txt")
DUMP_DIR = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")

TOKEN_RE = re.compile(rb'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}')


def from_dumps(paths):
    from mitmproxy import io as mio

    best = None
    for p in paths:
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    for m in flow.websocket.messages:
                        raw = bytes(m.content)
                        body = raw
                        z = raw.find(b"\x78\x9c")
                        if z >= 0:
                            try:
                                body = zlib.decompressobj().decompress(raw[z:])
                            except zlib.error:
                                body = raw
                        if b'"jwt"' in body:
                            tok = TOKEN_RE.search(body)
                            if tok:
                                best = tok.group(0).decode()
        except Exception as e:
            print(f"[warn] {p.name}: {e}")
    return best


def from_logs():
    best = None
    for p in sorted(DUMP_DIR.glob("*.txt")):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in TOKEN_RE.finditer(text.encode("utf-8", "replace")):
            best = m.group(0).decode()
    return best


def main():
    dumps = [pathlib.Path(x) for x in sys.argv[1:]]
    if not dumps:
        dumps = sorted(DUMP_DIR.glob("*.mitm"), key=lambda p: p.stat().st_mtime)
    tok = from_dumps(dumps) or from_logs()
    if not tok:
        print("[FAIL] 没找到 JWT")
        return 1
    OUT.write_text(tok, encoding="utf-8")
    import base64

    def b64d(s):
        s += "=" * (-len(s) % 4)
        return json.loads(base64.urlsafe_b64decode(s.encode()))

    parts = tok.split(".")
    claims = {}
    try:
        claims = b64d(parts[1])
    except Exception as e:
        claims = {"err": str(e)}
    print(f"[OK] JWT -> {OUT}")
    print(f"     claims: {claims}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
