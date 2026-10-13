"""probe_fair.py — 公平对照：同一握手帧、同一 JWT，只改「帧计数器」

对照组:
  A. 计数器用抓包里的值（7846/7847...）
  B. 计数器用我自己的小值（0x000a/0x000b...）
其余字节完全一致，看服务端是否回包。
"""
import asyncio
import json
import pathlib
import ssl
import sys

import websockets

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
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


async def run_case(name: str, hello: bytes, frames: list[bytes]):
    ctx = ssl.create_default_context()
    print(f"\n=== {name} ===")
    async with websockets.connect(URL, ssl=ctx, max_size=None, extra_headers=headers(), open_timeout=20) as ws:
        await ws.send(hello)
        r = await asyncio.wait_for(ws.recv(), timeout=10)
        print(f"  hello ack len={len(r)}")
        if len(r) < 30:
            print(f"  HELLO REJECTED {bytes(r).hex()}")
            return
        for i, f in enumerate(frames):
            await ws.send(f)
            print(f"  [{i}] send op={f[4:8].hex()} len={len(f)}")
            got = 0
            while got < 2:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=4)
                except asyncio.TimeoutError:
                    print("       (no reply)")
                    break
                info = HF.parse(raw)
                body = info.get("body")
                print(f"       recv op={info.get('opcode')} len={len(raw)} "
                      f"{json.dumps(body, ensure_ascii=False)[:120] if body else info.get('body_hex','')[:50]}")
                got += 1


async def main():
    hello = (ROOT / "hello_orig.bin").read_bytes()
    json_c = json.dumps({"last_id": 0}, ensure_ascii=False, separators=(",", ":")).encode()
    import zlib

    zc = zlib.compress(json_c)
    assert len(zc) == 21

    def frame(kind: int, counter: int) -> bytes:
        op = bytes([kind, 0x10, counter & 0xFF, (counter >> 8) & 0xFF])
        return HF.pack(HF.MAGIC_UP, op, UID, zc)

    # A: 抓包计数器（7846 起）
    await run_case("A 计数器=抓包值", hello, [frame(0x0F, 0x7846), frame(0x45, 0x7847)])
    # B: 小计数器
    await run_case("B 计数器=0x000a 起", hello, [frame(0x0F, 0x000A), frame(0x45, 0x000B)])
    # C: 计数器=0x7fff/0x8000
    await run_case("C 计数器=0x7fff 起", hello, [frame(0x0F, 0x7FFF), frame(0x45, 0x8000)])


if __name__ == "__main__":
    asyncio.run(main())
