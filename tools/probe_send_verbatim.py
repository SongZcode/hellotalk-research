"""probe_send_verbatim.py — 原样重放 App 的发送帧，验证发送链路是否可用（对照）"""
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_client as HC  # noqa: E402
import ht_frame as HF  # noqa: E402

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")


def load_send_frames():
    from mitmproxy import io as mio

    out = []
    for p in sorted(ROOT.glob("*.mitm")):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    for m in flow.websocket.messages:
                        raw = bytes(m.content)
                        if m.from_client and raw[4] == 0x01:
                            out.append((p.name, raw))
        except Exception as e:
            print(f"[warn] {p.name}: {e}")
    return out


async def main():
    frames = load_send_frames()
    print(f"抓到 {len(frames)} 条发送帧")
    for name, f in frames[:3]:
        body = HF.body_of(f)
        print(f"  {name} op={f[4:8].hex()} len={len(f)} {body.decode('utf-8','replace')[:100] if body else f[20:36].hex()}")

    if not frames:
        return
    c = HC.Client(HC.load_jwt())
    await c.connect()
    _, frame = frames[-1]
    print(f"[replay] 原样重发 len={len(frame)} op={frame[4:8].hex()}")
    await c.ws.send(frame)
    for i in range(5):
        try:
            raw = await asyncio.wait_for(c.ws.recv(), timeout=6)
        except asyncio.TimeoutError:
            print("  (no more)")
            break
        info = HF.parse(raw)
        print(f"  [{i}] len={len(raw)} op={info.get('opcode')} "
              f"{json.dumps(info.get('body'), ensure_ascii=False)[:200] if info.get('body') else info.get('body_hex','')[:60]}")
    await c.close()


if __name__ == "__main__":
    asyncio.run(main())
