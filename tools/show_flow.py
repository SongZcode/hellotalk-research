"""show_flow.py — 从 dump 里按 URL 关键字打印完整请求/响应（含响应头与解压后的 body）

用法: python tools\\show_flow.py vip_info [--all] [--dump artifacts\\mitm\\flows_https.mitm]
"""
import argparse
import gzip
import json
import pathlib
import sys
import zlib

from mitmproxy import io as mio

ROOT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")


def body_text(msg) -> str:
    """尽量还原 body：自动处理 gzip/deflate/br"""
    try:
        raw = msg.get_content(strict=False)
    except Exception:
        raw = msg.content
    if isinstance(raw, str):
        return raw
    for name, fn in (
        ("gzip", lambda b: gzip.decompress(b)),
        ("deflate", lambda b: zlib.decompressobj().decompress(b)),
        ("raw-deflate", lambda b: zlib.decompressobj(-15).decompress(b)),
    ):
        try:
            out = fn(raw)
            if out:
                return f"[{name}] " + out.decode("utf-8", "replace")
        except Exception:
            pass
    printable = sum(1 for c in raw[:300] if 32 <= c < 127) / max(1, len(raw[:300]))
    if printable > 0.85:
        return raw.decode("utf-8", "replace")
    return f"[binary {len(raw)}B] {raw[:120].hex()}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword")
    ap.add_argument("--dump", default=str(ROOT / "flows_https.mitm"))
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    dump = pathlib.Path(a.dump)
    n = 0
    with open(dump, "rb") as fh:
        for flow in mio.FlowReader(fh).stream():
            url = flow.request.pretty_url
            if a.keyword.lower() not in url.lower():
                continue
            n += 1
            print(f"\n{'='*90}")
            print(f"{flow.request.method} {url}")
            print(f"--- 请求头 ---")
            for k, v in flow.request.headers.items():
                print(f"  {k}: {v[:160]}")
            rb = body_text(flow.request)
            if rb.strip():
                print(f"--- 请求体 ---\n{rb[:800]}")
            if flow.response:
                print(f"--- 响应 {flow.response.status_code} ---")
                for k, v in flow.response.headers.items():
                    print(f"  {k}: {v[:160]}")
                print(f"--- 响应体 ---\n{body_text(flow.response)[:2000]}")
            else:
                print("--- 无响应 ---")
            if not a.all and n >= 3:
                break
    print(f"\n[i] 匹配 {n} 条")


if __name__ == "__main__":
    main()
