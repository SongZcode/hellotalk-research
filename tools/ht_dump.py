"""ht_dump.py — 打印指定抓包文件里所有可解帧的完整明文（UTF-8 安全输出到文件+控制台）

用法: python tools\ht_dump.py artifacts\mitm\flows.mitm [--grep say_hi] [--out artifacts\mitm\flows.dec.txt]
"""
import argparse
import json
import pathlib
import struct
import sys
import zlib

from mitmproxy import io as mio


def inflate(raw: bytes):
    for i in range(0, min(len(raw), 64)):
        if raw[i : i + 2] in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
            try:
                d = zlib.decompressobj()
                return d.decompress(raw[i:]) + d.flush()
            except zlib.error:
                return None
    return None


def hdr(raw):
    if len(raw) < 24:
        return {}
    return {
        "op": raw[4:8].hex(),
        "uid": struct.unpack_from("<Q", raw, 8)[0],
        "blen": struct.unpack_from("<I", raw, 20)[0],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--grep", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--maxlen", type=int, default=4000)
    args = ap.parse_args()

    path = pathlib.Path(args.dump)
    lines = []
    with open(path, "rb") as fh:
        frames = []
        try:
            for flow in mio.FlowReader(fh).stream():
                if not flow.websocket:
                    continue
                for m in flow.websocket.messages:
                    frames.append((m.timestamp, m.from_client, bytes(m.content)))
        except Exception as e:
            lines.append(f"[warn] {e}")

    for i, (ts, up, raw) in enumerate(frames):
        h = hdr(raw)
        body = inflate(raw)
        if body:
            try:
                txt = body.decode("utf-8")
            except UnicodeDecodeError:
                txt = "<non-utf8>"
        else:
            txt = "BIN " + raw[24:80].hex()
        line = f"[{i:>3}] {'UP' if up else 'DN'} op={h.get('op')} blen={h.get('blen')} ts={ts:.3f} | {txt[:args.maxlen]}"
        if args.grep and args.grep not in line:
            continue
        lines.append(line)

    text = "\n".join(lines)
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
        print(f"[i] written {len(lines)} lines -> {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)


if __name__ == "__main__":
    main()
