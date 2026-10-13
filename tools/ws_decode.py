"""ws_decode.py — 从 mitmproxy dump 里把所有 hellotalk WS 帧导出为原始字节，
并尝试按疑似协议头切分 + zlib 解压，输出可读的 WS 协议解码结果。

用法:
  python tools\ws_decode.py artifacts\mitm\flows2.mitm [--raw out.bin] [--tail 200]
"""
import argparse
import io
import json
import pathlib
import re
import sys
import zlib

from mitmproxy import io as mio
from mitmproxy.exceptions import FlowReadException


def is_zlib(data: bytes) -> bool:
    return len(data) > 2 and data[0] == 0x78


def try_zlib(data: bytes):
    """尝试 zlib 解压；允许尾部多余字节（真实帧里 4 字节长度头是服务器塞的）。"""
    for cut in range(0, min(len(data), 12)):
        chunk = data[cut:]
        try:
            d = zlib.decompressobj()
            out = d.decompress(chunk)
            out += d.flush()
            if out:
                return cut, out
        except zlib.error:
            continue
    return None


def split_frames(blob: bytes, max_frame: int = 8192):
    """原始 TCP 字节流按疑似头切分：头看起来像 04 00 ... ，用 78 9c 起点做启发式。"""
    frames = []
    for m in re.finditer(rb"\x78[\x01\x9c\xda]", blob):
        pass
    return frames


def dump_flows(path: pathlib.Path):
    with open(path, "rb") as fh:
        reader = mio.FlowReader(fh)
        try:
            for flow in reader.stream():
                yield flow
        except FlowReadException as e:
            print(f"[warn] flow read stopped: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--out", default=None)
    ap.add_argument("--tail", type=int, default=50)
    ap.add_argument("--jsonl", default=None, help="把解码结果写成 jsonl")
    args = ap.parse_args()

    path = pathlib.Path(args.dump)
    events = []
    for flow in dump_flows(path):
        if not flow.websocket:
            continue
        url = flow.request.pretty_url
        for m in flow.websocket.messages:
            events.append(
                {
                    "t": m.timestamp,
                    "dir": "SEND" if m.from_client else "RECV",
                    "len": len(m.content),
                    "raw": bytes(m.content),
                    "url": url,
                }
            )

    print(f"[i] {path.name}: {len(events)} ws messages")
    outp = pathlib.Path(args.out) if args.out else path.with_suffix(".wsbin")
    with open(outp, "wb") as fh:
        for i, e in enumerate(events):
            fh.write(e["raw"])
    print(f"[i] raw concat -> {outp} ({outp.stat().st_size} bytes)")

    # 逐帧分析
    recs = []
    for i, e in enumerate(events):
        raw = e["raw"]
        rec = {"i": i, "t": e["t"], "dir": e["dir"], "len": len(raw), "head": raw[:16].hex()}
        z = try_zlib(raw)
        if z:
            cut, out = z
            rec["zlib_cut"] = cut
            rec["text"] = out.decode("utf-8", "replace")
        else:
            rec["text"] = None
            rec["hex"] = raw.hex()
        recs.append(rec)

    if args.jsonl:
        with open(args.jsonl, "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("\n===== decode summary =====")
    zok = sum(1 for r in recs if r["text"])
    print(f"zlib-decodable: {zok}/{len(recs)}")
    for r in recs[-args.tail:]:
        tag = f"{r['dir']:<4} len={r['len']:<5}"
        if r["text"]:
            print(f"[{r['i']}] {tag} zlib(cut={r.get('zlib_cut')}): {r['text'][:300]}")
        else:
            print(f"[{r['i']}] {tag} hex: {r['hex'][:200]}")


if __name__ == "__main__":
    main()
