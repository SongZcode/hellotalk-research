"""probe_min.py — 最小可用实验：握手(原样帧) → 发一帧 → 打印所有回包"""
import asyncio
import json
import pathlib
import ssl
import sys

import websockets

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

UID = <UID>
ROOT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")


def headers(jwt: str | None = None):
    hdr = {"User-Agent": "okhttp/5.3.2"}
    f = ROOT / "ws_headers.json"
    if f.exists():
        hdr.update(json.loads(f.read_text(encoding="utf-8")))
    tok = jwt or (ROOT / "jwt.txt").read_text(encoding="utf-8").strip()
    for k in list(hdr):
        if k.lower() == "x-ht-token":
            hdr[k] = "Bearer " + tok
    return hdr


async def drain(ws, n=6, timeout=6):
    for i in range(n):
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        except asyncio.TimeoutError:
            print(f"    [drain] timeout after {i} frames")
            return
        info = HF.parse(raw)
        body = info.get("body")
        txt = json.dumps(body, ensure_ascii=False)[:200] if body else info.get("body_hex", "")[:60]
        print(f"    [drain] len={len(raw)} op={info.get('opcode')} {txt}")


async def main():
    orig = (ROOT / "hello_orig.bin").read_bytes()
    ctx = ssl.create_default_context()
    url = f"wss://api-cn.hellotalk8.com/ht_im/sock?userid={UID}"
    async with websockets.connect(url, ssl=ctx, max_size=None, extra_headers=headers(), open_timeout=20) as ws:
        await ws.send(orig)
        r = await asyncio.wait_for(ws.recv(), timeout=10)
        print(f"[1] 握手(旧JWT) ack len={len(r)}")
        if len(r) < 30:
            print(f"    REJECTED: {bytes(r).hex()}")
            return
        info = HF.parse(r)
        fresh = ((info.get("body") or {}).get("data") or {}).get("jwt")
        print(f"    服务端下发的新 JWT: {str(fresh)[:50]}...")

    # 第二轮：用服务端刚下发的新 JWT 重新握手（hello + header 都用它）
    if fresh:
        async with websockets.connect(url, ssl=ctx, max_size=None, extra_headers=headers(fresh), open_timeout=20) as ws:
            hello = json.loads(orig[20:].decode("utf-8"))
            hello["jwt"] = fresh
            frame = HF.MAGIC_UP + bytes([0x25, 0x10, 0x01, 0x00]) + UID.to_bytes(8, "little") + \
                json.dumps(hello, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            frame = frame[:16] + len(frame[16:]).to_bytes(4, "little") + frame[16:]
            await ws.send(frame)
            r2 = await asyncio.wait_for(ws.recv(), timeout=10)
            print(f"[2] 握手(新JWT) ack len={len(r2)}")
            if len(r2) < 30:
                print(f"    REJECTED: {bytes(r2).hex()}")
                return
            for name, frame in (
                ("pull_msg", HF.pack_json(bytes([0x0F, 0x10, 0x0A, 0x00]), UID, {"last_id": 0})),
                ("pull_inbox", HF.pack_json(bytes([0x45, 0x10, 0x0B, 0x00]), UID, {"last_id": 0})),
            ):
                print(f"[3] send {name} len={len(frame)}")
                await ws.send(frame)
                await drain(ws, n=3, timeout=6)
            print("[4] trace")
            trace = HF.pack(HF.MAGIC_UP, bytes([0x21, 0x10, 0x0C, 0x00]), UID,
                            UID.to_bytes(4, "little") + (0x2B41C922).to_bytes(4, "little"))
            await ws.send(trace)
            await drain(ws, n=3, timeout=6)


if __name__ == "__main__":
    asyncio.run(main())
