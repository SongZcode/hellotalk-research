"""search_bodies.py — 在所有抓包 dump 的请求/响应体里搜关键词

用法: python tools\\search_bodies.py sayhi
"""
import gzip
import pathlib
import sys
import zlib

from mitmproxy import io as mio

ROOT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")


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
    p = sum(1 for c in raw[:300] if 32 <= c < 127) / max(1, len(raw[:300]))
    return raw.decode("utf-8", "replace") if p > 0.85 else ""


def main():
    key = (sys.argv[1] if len(sys.argv) > 1 else "sayhi").lower()
    n = 0
    for p in sorted(ROOT.glob("*.mitm"), key=lambda x: x.stat().st_mtime):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    for tag, msg in (("REQ", flow.request), ("RESP", flow.response)):
                        if msg is None:
                            continue
                        t = body_text(msg)
                        if key in t.lower():
                            n += 1
                            print(f"\n### {p.name} {tag} {flow.request.pretty_url.split('?')[0][:90]}")
                            i = t.lower().find(key)
                            print("   ", t[max(0, i - 250):i + 350].replace("\n", " ")[:600])
                            if n >= 15:
                                return 0
        except Exception as e:
            print(f"[warn] {p.name}: {e}")
    print(f"\n[i] 命中 {n} 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())
