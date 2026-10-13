"""find_free_greet.py — 在所有抓包里找「免费打招呼次数」相关接口与字段

搜索关键词：free_sayhi / freeSayHi / sayhi / greet / exposure（曝光/打招呼相关）
"""
import gzip
import json
import pathlib
import re
import sys
import zlib

from mitmproxy import io as mio

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
KEYS = ("sayhi", "say_hi", "greet", "free_sayhi", "exposure", "new_chat")


def body_text(msg) -> str:
    try:
        raw = msg.get_content(strict=False)
    except Exception:
        raw = msg.content
    if isinstance(raw, str):
        return raw
    for fn in (gzip.decompress, lambda b: zlib.decompressobj().decompress(b)):
        try:
            out = fn(raw)
            if out:
                return out.decode("utf-8", "replace")
        except Exception:
            pass
    p = sum(1 for c in raw[:200] if 32 <= c < 127) / max(1, len(raw[:200]))
    return raw.decode("utf-8", "replace") if p > 0.85 else f"[bin {len(raw)}B]"


def main():
    hits = []
    for p in sorted(ROOT.glob("*.mitm"), key=lambda x: x.stat().st_mtime):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    url = flow.request.pretty_url
                    lu = url.lower()
                    if not any(k in lu for k in KEYS):
                        continue
                    resp = body_text(flow.response) if flow.response else ""
                    req = body_text(flow.request)
                    if any(k in (resp + req).lower() for k in ("sayhi", "say_hi", "greet", "free_")):
                        hits.append((p.name, url, req[:200], resp[:400]))
        except Exception as e:
            print(f"[warn] {p.name}: {e}")
    print(f"=== 命中 {len(hits)} 条 ===\n")
    seen = set()
    for name, url, req, resp in hits:
        key = url.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        print(f"### {name}  {key}")
        print(f"  REQ : {req}")
        print(f"  RESP: {resp}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
