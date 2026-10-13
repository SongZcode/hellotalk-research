"""probe_sweep.py — 扫描 opcode 第二字节：找出服务端真正接受的请求编码

对 pull_inbox(0x45) 帧，遍历第二字节 0x10/0x40/0x75/... 看哪个能得到正常 ack（97 字节）
而不是 24 字节的 echo 拒绝。
"""
import asyncio
import json
import pathlib
import ssl
import sys
import zlib

import websockets

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

ROOT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")
UID = <UID>
URL = f"wss://api-cn.hellotalk8.com/ht_im/sock?userid={UID}"


def headers():
    hdr = {"User-Agent": "okhttp/5.3.2"}
    f = ROOT / "ws_headers.json"
    if f.exists():
        hdr.update(json.loads(f.read_text(encoding="utf-8")))
    for k in list(hdr):
        if k.lower() == "x-ht-token":
            hdr[k] = "Bearer " + (ROOT / "jwt.txt").read_text(encoding="utf-8").strip()
    return hdr


async def probe(second_byte: int, counter: int, hello: bytes):
    op = bytes([0x45, second_byte, counter & 0xFF, (counter >> 8) & 0xFF])
    body = zlib.compress(json.dumps({"last_id": 0}, separators=(",", ":")).encode())
    frame = HF.pack(HF.MAGIC_UP, op, UID, body)
    ctx = ssl.create_default_context()
    try:
        async with websockets.connect(URL, ssl=ctx, max_size=None, extra_headers=headers(), open_timeout=15) as ws:
            await ws.send(hello)
            ack = await asyncio.wait_for(ws.recv(), timeout=8)
            if len(ack) < 30:
                return f"hello rejected ({len(ack)}B)"
            await ws.send(frame)
            raw = await asyncio.wait_for(ws.recv(), timeout=6)
            info = HF.parse(raw)
            body_txt = json.dumps(info.get("body"), ensure_ascii=False) if info.get("body") else info.get("body_hex", "")
            return f"len={len(raw)} op={info.get('opcode')} {body_txt[:80]}"
    except asyncio.TimeoutError:
        return "TIMEOUT (no reply)"
    except Exception as e:
        return f"ERR {type(e).__name__}: {str(e)[:60]}"


async def main():
    hello = (ROOT / "hello_orig.bin").read_bytes()
    for sb in (0x10, 0x40, 0x75, 0x61, 0x26, 0x00, 0x50):
        res = await probe(sb, 0x1000 + sb, hello)
        print(f"  2nd byte 0x{sb:02x} -> {res}")
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
