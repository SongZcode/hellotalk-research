"""probe_send.py — 发送帧实验：把服务端对「发送」的全部回包原样打出来（判断 ack / 拒绝）"""
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import greet_test as GT  # noqa: E402
import ht_client as HC  # noqa: E402
import ht_frame as HF  # noqa: E402


async def main():
    c = HC.Client(HC.load_jwt())
    await c.connect()
    print(f"[conn] session_key={c.session_key}")
    body = GT.build_send("text", "text", {"reportIndex": 0, "reportText": "", "text": "protocol probe"})
    body["msg"]["to_uid"] = HC.UID

    seq = c.next_seq()
    op = HF.build_opcode(0x01, seq, 0x40)
    frame = HF.pack_json(op, HC.UID, body)
    print(f"[send] op={op.hex()} len={frame.len if hasattr(frame,'len') else len(frame)}")
    await c.ws.send(frame)

    for i in range(6):
        try:
            raw = await asyncio.wait_for(c.ws.recv(), timeout=6)
        except asyncio.TimeoutError:
            print("  (no more frames)")
            break
        print(f"  [{i}] len={len(raw)} hex={bytes(raw).hex()}")
        info = HF.parse(raw)
        print(f"       parsed op={info.get('opcode')} body_off={info.get('body_off')} body={json.dumps(info.get('body'), ensure_ascii=False)[:200] if info.get('body') else info.get('body_hex','')[:60]}")
    await c.close()


if __name__ == "__main__":
    asyncio.run(main())
