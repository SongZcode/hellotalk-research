"""ht_bin.py — 破解 f1/f5 二进制专有帧（protobuf 风格），给出字段号+类型+值的原始解码

用法: python tools\ht_bin.py artifacts\mitm\flows.mitm artifacts\mitm\flows_run1.mitm
"""
import pathlib
import struct
import sys
import zlib

from mitmproxy import io as mio

WT = {0: "varint", 1: "fixed64", 2: "bytes", 5: "fixed32"}


def rd_varint(buf: bytes, i: int):
    shift = 0
    val = 0
    while i < len(buf):
        b = buf[i]
        val |= (b & 0x7F) << shift
        i += 1
        if not b & 0x80:
            return val, i
        shift += 7
        if shift > 63:
            break
    return None, i


def pb_decode(buf: bytes, indent: int = 0, maxdepth: int = 4):
    """极简 protobuf 扫描器：输出 (字段号, 类型, 值) 列表，不追求完备。"""
    out = []
    i = 0
    while i < len(buf):
        try:
            key, i = rd_varint(buf, i)
        except Exception:
            break
        if key is None:
            break
        field, wt = key >> 3, key & 7
        if field == 0:
            out.append((0, "raw", buf[i:].hex()))
            break
        if wt == 0:
            v, i = rd_varint(buf, i)
            out.append((field, "varint", v))
        elif wt == 2:
            ln, i = rd_varint(buf, i)
            if ln is None or i + ln > len(buf):
                out.append((field, "bad_len", f"ln={ln} rest={len(buf)-i}"))
                break
            sub = buf[i : i + ln]
            i += ln
            printable = all(32 <= c < 127 for c in sub) and len(sub) > 0
            nested = None
            if not printable and len(sub) >= 2 and indent < maxdepth:
                nested = pb_decode(sub, indent + 1, maxdepth)
            out.append((field, "bytes", sub.hex() if not printable else sub.decode(), nested))
        elif wt == 5:
            v = struct.unpack_from("<I", buf, i)[0]
            i += 4
            out.append((field, "fixed32", v))
        elif wt == 1:
            v = struct.unpack_from("<Q", buf, i)[0]
            i += 8
            out.append((field, "fixed64", v))
        else:
            out.append((field, f"wt={wt}", buf[i:].hex()))
            break
    return out


def show(nodes, depth=0):
    for f, t, v, *rest in nodes:
        pad = "  " * depth
        if t == "bytes" and rest and rest[0]:
            print(f"{pad}f{f} {t}: <nested {len(str(v))}>")
            show(rest[0], depth + 1)
        else:
            s = str(v)
            print(f"{pad}f{f} {t}: {s[:110]}")


def main():
    seen = set()
    for p in [pathlib.Path(x) for x in sys.argv[1:]]:
        if not p.exists():
            continue
        print(f"\n########## {p.name} ##########")
        with open(p, "rb") as fh:
            frames = []
            try:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    for m in flow.websocket.messages:
                        frames.append((m.from_client, bytes(m.content)))
            except Exception as e:
                print(f"[warn] {e}")
        for i, (up, raw) in enumerate(frames):
            if len(raw) < 28:
                continue
            magic = raw[0:3]
            if magic not in (b"\xf1\x04\x00", b"\xf5\x04\x01"):
                continue
            body = raw[24:]
            key = (magic, body[:6].hex()[:8], len(body))
            if key in seen:
                continue
            seen.add(key)
            print(f"\n--- frame {i} {'UP' if up else 'DN'} magic={magic.hex()} op={raw[4:8].hex()} bodylen={len(body)}")
            print(f"    raw: {body.hex()}")
            show(pb_decode(body))


if __name__ == "__main__":
    main()
