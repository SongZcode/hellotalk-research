"""replay_session.py — 把抓包里 App 的整段 WS 会话逐帧原样重放（对照实验）

用法: python tools\replay_session.py artifacts\mitm\flows_run1.mitm
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
URL = f"wss://api-cn.hellotalk8.com/ht_im/sock?userid={UID}"
HDR = pathlib.Path(r"<WORKDIR>\artifacts\mitm\ws_headers.json")


def load_frames(dump: pathlib.Path):
    from mitmproxy import io as mio

    ups = []
    with open(dump, "rb") as fh:
        for flow in mio.FlowReader(fh).stream():
            if not flow.websocket:
                continue
            for m in flow.websocket.messages:
                if m.from_client:
                    ups.append(bytes(m.content))
    return ups


async def main():
    dump = pathlib.Path(sys.argv[1])
    ups = load_frames(dump)
    print(f"载入 {len(ups)} 条上行帧")
    headers = {"User-Agent": "okhttp/5.3.2"}
    if HDR.exists():
        headers.update(json.loads(HDR.read_text(encoding="utf-8")))

    ctx = ssl.create_default_context()
    async with websockets.connect(URL, ssl=ctx, max_size=None, extra_headers=headers, open_timeout=20) as ws:
        for i, frame in enumerate(ups):
            op = frame[4:8].hex()
            kind = frame[4]
            label = {
                0x25: "handshake",
                0x0F: "pull_msg",
                0x45: "pull_inbox",
                0x21: "trace",
                0x01: "send_msg",
                0x15: "report_id",
                0x17: "presence",
            }.get(kind, f"op{kind:02x}")
            # 每帧都换成新 seq（保持 16 位自增，模拟客户端）
            await ws.send(frame)
            print(f"[{i}] SEND {label} op={op} len={len(frame)}")
            try:
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=4)
                    info = HF.parse(raw)
                    body = info.get("body")
                    txt = json.dumps(body, ensure_ascii=False)[:220] if body else info.get("body_hex", "")[:70]
                    print(f"      RECV op={info.get('opcode')} len={len(raw)} {txt}")
                    break
            except asyncio.TimeoutError:
                print("      RECV timeout(4s) —— 服务端没回")
            await asyncio.sleep(0.4)


if __name__ == "__main__":
    asyncio.run(main())
