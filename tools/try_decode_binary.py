"""try_decode_binary.py — 尝试解开 ht/binary 响应（gzip / zlib / 明文）"""
import gzip
import json
import pathlib
import zlib
import sys

from mitmproxy import io as mio

ROOT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")


def main():
    kw = sys.argv[1] if len(sys.argv) > 1 else "rewarded_advert"
    for p in sorted(ROOT.glob("*.mitm"), key=lambda x: x.stat().st_mtime):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if kw not in flow.request.pretty_url or not flow.response:
                        continue
                    raw = flow.response.content
                    print(f"\n### {p.name} {kw}  长度={len(raw)}  头={dict(flow.response.headers).get('content-type')}")
                    print(f"    前 32B: {raw[:32].hex()}")
                    for name, fn in (
                        ("gzip", gzip.decompress),
                        ("zlib", lambda b: zlib.decompressobj().decompress(b)),
                        ("raw-deflate", lambda b: zlib.decompressobj(-15).decompress(b)),
                    ):
                        try:
                            out = fn(raw)
                            print(f"  [{name}] OK {len(out)}B: {out[:300]!r}")
                        except Exception as e:
                            print(f"  [{name}] fail {type(e).__name__}")
                    # XOR 试探常见前缀（看是否为已知明文的异或）
                    for probe in (b'{"', b'{"status"', b'\x1f\x8b'):
                        x = bytes(a ^ b for a, b in zip(raw[:len(probe)], probe))
                        if len(set(x)) <= 2:
                            print(f"  [xor] 密钥疑似 {x.hex()} (针对 {probe!r})")
        except Exception as e:
            print(f"[warn] {p.name}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
