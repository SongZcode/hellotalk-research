"""ht_ws.py — HelloTalk ht_im/sock WS 帧解码器（已实测帧结构）

帧结构（mitmproxy 抓到的完整 WS message，含 4 字节 proto 掩码前缀）:
  offset 0       4B   f0/f1/f5 04 00 01 …  (proto 头)
  offset 4       4B   序号（帧号，小端）
  offset 8       8B   时间戳（两个 u32，设备/服务端）
  offset 16      4B   保留 00000000（RECV 帧）
  offset 20      4B   载荷长度 u32（小端）
  offset 24      N    zlib 压缩载荷（78 9c…），部分帧尾部有 4B 校验

用法:
  python tools\ht_ws.py artifacts\mitm\flows2.mitm [--tail 200] [--jsonl out.jsonl]
"""
import argparse
import json
import pathlib
import struct
import sys
import zlib

from mitmproxy import io as mio
from mitmproxy.exceptions import FlowReadException

ZLIB_MAGIC = (b"\x78\x01", b"\x78\x9c", b"\x78\xda")


def find_zlib(raw: bytes) -> int:
    for i in range(0, min(len(raw), 64)):
        if raw[i : i + 2] in ZLIB_MAGIC:
            return i
    return -1


def inflate(data: bytes):
    """从 zlib 流起点解压，容忍尾部 4 字节校验/垃圾。"""
    d = zlib.decompressobj()
    try:
        out = d.decompress(data)
        out += d.flush()
        return out, d.unused_data
    except zlib.error as e:
        return None, str(e)


def parse_header(raw: bytes):
    if len(raw) < 24:
        return None
    return {
        "magic": raw[0:4].hex(),
        "seq": struct.unpack_from("<I", raw, 4)[0],
        "ts_a": struct.unpack_from("<I", raw, 8)[0],
        "ts_b": struct.unpack_from("<I", raw, 12)[0],
        "rsv": struct.unpack_from("<I", raw, 16)[0],
        "declared_len": struct.unpack_from("<I", raw, 20)[0],
    }


def decode(raw: bytes):
    hdr = parse_header(raw)
    if hdr is None:
        return None, None
    zoff = find_zlib(raw)
    if zoff < 0:
        return hdr, None
    out, unused = inflate(raw[zoff:])
    return hdr, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--tail", type=int, default=200)
    ap.add_argument("--jsonl", default=None)
    ap.add_argument("--show-raw", action="store_true")
    args = ap.parse_args()

    path = pathlib.Path(args.dump)
    msgs = []
    with open(path, "rb") as fh:
        reader = mio.FlowReader(fh)
        try:
            for flow in reader.stream():
                if not flow.websocket:
                    continue
                for m in flow.websocket.messages:
                    msgs.append((m.timestamp, m.from_client, bytes(m.content)))
        except FlowReadException as e:
            print(f"[warn] {e}", file=sys.stderr)

    recs = []
    for i, (ts, from_client, raw) in enumerate(msgs):
        hdr, body = decode(raw)
        rec = {
            "i": i,
            "t": ts,
            "dir": "UP" if from_client else "DN",
            "len": len(raw),
            "hdr": hdr,
            "body": body.decode("utf-8", "replace") if body else None,
        }
        if body is None:
            rec["raw_hex"] = raw.hex()
        recs.append(rec)

    ok = sum(1 for r in recs if r["body"])
    print(f"[i] {path.name}: {len(recs)} frames, inflate ok: {ok}\n")

    if args.jsonl:
        with open(args.jsonl, "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    for r in recs[-args.tail :]:
        h = r["hdr"] or {}
        tag = f"[{r['i']:>3}] {r['dir']} len={r['len']:<5} seq={h.get('seq')} dl={h.get('declared_len')}"
        if r["body"]:
            print(f"{tag} | {r['body'][:400]}")
        else:
            print(f"{tag} | RAW {r['raw_hex'][:180]}")


if __name__ == "__main__":
    main()
