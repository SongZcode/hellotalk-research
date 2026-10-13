"""probe_verbatim.py — 原样重放「握手 + 后续N帧」（字节完全一致），验证 seq 是否关键

步骤：
 1. 用 hello_orig.bin 原样握手
 2. 依次发送抓包里紧跟握手的若干上行帧（字节原样）
 3. 打印每帧后收到的所有回包

用法: python tools\probe_verbatim.py [--n 4] [--dump artifacts\mitm\flows_run1.mitm]
"""
import argparse
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


def headers():
    hdr = {"User-Agent": "okhttp/5.3.2"}
    f = ROOT / "ws_headers.json"
    if f.exists():
        hdr.update(json.loads(f.read_text(encoding="utf-8")))
    for k in list(hdr):
        if k.lower() == "x-ht-token":
            hdr[k] = "Bearer " + (ROOT / "jwt.txt").read_text(encoding="utf-8").strip()
    return hdr


def load_up_frames(dump: pathlib.Path):
    from mitmproxy import io as mio

    ups, downs = [], []
    with open(dump, "rb") as fh:
        for flow in mio.FlowReader(fh).stream():
            if not flow.websocket:
                continue
            for m in flow.websocket.messages:
                (ups if m.from_client else downs).append(bytes(m.content))
    return ups, downs


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--dump", default=str(ROOT / "flows_run1.mitm"))
    a = ap.parse_args()

    ups, _ = load_up_frames(pathlib.Path(a.dump))
    hello = (ROOT / "hello_orig.bin").read_bytes()
    follow = [f for f in ups if f[:5] != b"\xf0\x04\x00\x01\x25"][: a.n]
    print(f"将原样发送：握手 1 帧 + 后续 {len(follow)} 帧")

    ctx = ssl.create_default_context()
    url = f"wss://api-cn.hellotalk8.com/ht_im/sock?userid={UID}"
    async with websockets.connect(url, ssl=ctx, max_size=None, extra_headers=headers(), open_timeout=20) as ws:
        await ws.send(hello)
        r = await asyncio.wait_for(ws.recv(), timeout=10)
        print(f"[hello] ack len={len(r)} ok={len(r) > 30}")
        for i, f in enumerate(follow):
            info = HF.parse(f)
            print(f"[{i}] send op={f[4:8].hex()} len={len(f)} body={json.dumps(info.get('body'), ensure_ascii=False)[:90]}")
            await ws.send(f)
            got = 0
            while got < 3:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=4)
                except asyncio.TimeoutError:
                    print("      (no more)")
                    break
                ri = HF.parse(raw)
                body = ri.get("body")
                print(f"      recv op={ri.get('opcode')} len={len(raw)} {json.dumps(body, ensure_ascii=False)[:160] if body else ri.get('body_hex','')[:60]}")
                got += 1
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
