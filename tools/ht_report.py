"""ht_report.py — 汇总所有抓包文件里的 HelloTalk WS 帧：opcode 表 + 明文内容 + 握手/JWT + f5 二进制帧

用法: python tools\ht_report.py artifacts\mitm\flows.mitm artifacts\mitm\flows2.mitm
"""
import base64
import json
import pathlib
import struct
import sys
import zlib

from mitmproxy import io as mio

MAGIC_UP = "f0040001"
MAGIC_DN = "f1040001"
MAGIC_BIN = "f5040100"


def b64d(s: str):
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())


def jwt_parts(tok: str):
    p = tok.split(".")
    out = {}
    for name, idx in (("header", 0), ("payload", 1)):
        try:
            out[name] = json.loads(b64d(p[idx]))
        except Exception as e:
            out[name] = f"<{e}>"
    return out


def inflate(raw: bytes):
    for i in range(0, min(len(raw), 64)):
        if raw[i : i + 2] in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
            try:
                d = zlib.decompressobj()
                return d.decompress(raw[i:]) + d.flush()
            except zlib.error:
                return None
    return None


def load(path: pathlib.Path):
    frames = []
    with open(path, "rb") as fh:
        try:
            for flow in mio.FlowReader(fh).stream():
                if not flow.websocket:
                    continue
                for m in flow.websocket.messages:
                    frames.append(
                        {
                            "t": m.timestamp,
                            "up": m.from_client,
                            "raw": bytes(m.content),
                        }
                    )
        except Exception as e:
            print(f"[warn] {path.name}: {e}")
    return frames


def hdr(raw):
    if len(raw) < 24:
        return {}
    return {
        "magic": raw[0:4].hex(),
        "opcode": raw[4:8].hex(),
        "uid": struct.unpack_from("<Q", raw, 8)[0],
        "hdr_len": struct.unpack_from("<I", raw, 16)[0],
        "body_len": struct.unpack_from("<I", raw, 20)[0],
    }


def main():
    paths = [pathlib.Path(p) for p in (sys.argv[1:] or [r"F:\hellotalk-mitm\artifacts\mitm\flows2.mitm"])]
    all_frames = []
    for p in paths:
        if p.exists():
            fs = load(p)
            print(f"[i] {p.name}: {len(fs)} frames")
            all_frames += fs

    print(f"\n===== 总帧数 {len(all_frames)} =====")
    ops = {}
    for f in all_frames:
        h = hdr(f["raw"])
        key = (h.get("magic"), h.get("opcode"))
        ops.setdefault(key, []).append(f)

    print("\n===== opcode 表 (magic, opcode) -> 方向/次数/载荷样例 =====")
    for (mg, op), fs in sorted(ops.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or "")):
        ups = sum(1 for f in fs if f["up"])
        body = inflate(fs[0]["raw"])
        sample = body.decode("utf-8", "replace")[:110] if body else fs[0]["raw"][24:40].hex()
        print(f"  {mg} {op}  x{len(fs):<3} (UP={ups},DN={len(fs)-ups})  {sample}")

    print("\n===== 握手明文 =====")
    for f in all_frames[:2]:
        body = inflate(f["raw"])
        if not body:
            continue
        obj = json.loads(body)
        if "jwt" in obj:
            obj["jwt_claims"] = jwt_parts(obj["jwt"])
            obj["jwt"] = obj["jwt"][:36] + "..."
        print(json.dumps(obj, ensure_ascii=False, indent=1)[:2200])
        print()

    print("\n===== 明文 JSON 帧全量（按序）=====")
    for i, f in enumerate(all_frames):
        body = inflate(f["raw"])
        h = hdr(f["raw"])
        if body:
            try:
                txt = body.decode("utf-8")
                isjson = txt.lstrip().startswith("{")
            except Exception:
                isjson = False
            if isjson:
                print(f"[{i:>3}] {'UP' if f['up'] else 'DN'} op={h.get('opcode')} {txt[:260]}")
        elif h.get("magic") == MAGIC_BIN:
            print(f"[{i:>3}] DN op={h.get('opcode')} BIN len={h.get('body_len')} {f['raw'][24:64].hex()}")


if __name__ == "__main__":
    main()
