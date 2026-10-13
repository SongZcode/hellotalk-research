"""ws_replay_probe.py — 用抓包里的原始帧字节做对照实验，判断服务端握手到底要什么

试验序列（每条独立连接）:
  A. 原样重放抓包里的握手帧字节（不改任何字节）
  B. 只把 opcode 换成 25100001（从 1 开始计数）
  C. 握手前先发一条 http GET /ht_im/sock 同源探测？——不做，跳过
  D. 带 ?userid= 并加 devid 参数
"""
import asyncio
import json
import pathlib
import ssl
import sys

import websockets

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

UID = <UID>
ORIG = pathlib.Path(r"<WORKDIR>\artifacts\mitm\hello_orig.bin")


async def try_case(name: str, url: str, frame: bytes, headers: dict | None = None):
    print(f"\n=== {name} ===")
    print(f"    url={url} frame_len={len(frame)} head={frame[:12].hex()}")
    try:
        ctx = ssl.create_default_context()
        async with websockets.connect(
            url,
            ssl=ctx,
            max_size=None,
            open_timeout=15,
            extra_headers=headers or {"User-Agent": "okhttp/4.9.2"},
        ) as ws:
            await ws.send(frame)
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=8)
                print(f"    recv len={len(raw)} hex={bytes(raw)[:120].hex()}")
                info = HF.parse(raw)
                print(f"    parsed: op={info.get('opcode')} body={json.dumps(info.get('body'), ensure_ascii=False)[:300]}")
            except asyncio.TimeoutError:
                print("    recv TIMEOUT (no reply in 8s)")
    except Exception as e:
        print(f"    connect FAIL: {type(e).__name__}: {e}")


async def main():
    orig = ORIG.read_bytes()

    # A. 原样字节
    await try_case("A 原样重放抓包握手帧", f"wss://api-cn.hellotalk8.com/ht_im/sock?userid={UID}", orig)

    # B. 换 opcode 序列从 1 开始
    f2 = bytearray(orig)
    f2[4:8] = bytes([0x25, 0x10, 0x01, 0x00])
    await try_case("B opcode=25100100", f"wss://api-cn.hellotalk8.com/ht_im/sock?userid={UID}", bytes(f2))

    # C. 带额外 cookie/UA 头
    await try_case(
        "C 带常见 App 头",
        f"wss://api-cn.hellotalk8.com/ht_im/sock?userid={UID}",
        orig,
        headers={
            "User-Agent": "okhttp/4.9.2",
            "Origin": "https://www.hellotalk.com",
            "Accept-Encoding": "gzip",
            "HT-Token": "",
        },
    )

    # D. URL 带 device_id
    await try_case(
        "D url 加 devid",
        f"wss://api-cn.hellotalk8.com/ht_im/sock?userid={UID}&devid=<DEVICE_ID>",
        orig,
    )


if __name__ == "__main__":
    asyncio.run(main())
