"""greet_probe.py — 打招呼配额探测（用真实收件人）

流程:
  1. 握手 + 连接后固定动作（pull_msg / pull_inbox / trace）
  2. 读取目标 uid（artifacts/mitm/target_uid.txt）
  3. 先发一条普通消息做基准，确认能拿到正常 ack（含 remaining_new_chat_count）
  4. 连续发 new_sticker 招呼，逐条打印服务端应答（含错误码），观察第 N 次是否被拦

用法: python tools\greet_probe.py [--n 12] [--text Hello]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_client as HC  # noqa: E402
import ht_frame as HF  # noqa: E402

UID = HC.UID
ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
TARGET = ROOT / "target_uid.txt"


def payload_for(kind: str, text: str) -> dict:
    """按实测抓包的真实字段格式构造发送体（注意 new_sticker 内部是 snake_case）"""
    ext = json.dumps({"trace_id": uuid.uuid4().hex}, separators=(",", ":"))
    base = {
        "msg_id": str(uuid.uuid4()),
        "send_ts": int(time.time() * 1000),
        "chat_follow_notify": 0,
        "correction_gift_notify": 0,
        "cost_diamonds": 0,
        "pay_chat_cost_virtual_val": 0,
        "pay_chat_switch": 0,
        "recv_diamonds": 0,
        "source": "Chat List",
        "to_payer": False,
        "valid_time": 0,
        "bubble": {"id": 0},
        "ext": ext,
    }
    if kind == "text":
        base["msg_type"] = "text"
        base["text"] = {"reportIndex": 0, "reportText": "", "text": text}
    else:
        # 与实测帧逐字段一致（source 改成打招呼入口标记 All Hand）
        base["msg_type"] = "new_sticker"
        base["source"] = "All Hand"
        base["sub_source"] = "en"
        base["new_sticker"] = {
            "hasStartedAnim": False,
            "hello_msg": 1,
            "image_id": 11,
            "image_url": "https://ali-global-cdn.hellotalk8.com/prod/application/attachment/"
                         "1e7ff6ec65b6c6be8aac9d8ff5f2f967.webp",
            "product_id": 1,
        }
    return {"msg": base, "version": 394260, "client_lang": "Chinese"}


async def send(c: HC.Client, to_uid: int, kind: str, text: str, index: int):
    body = payload_for(kind, text)
    body["msg"]["to_uid"] = to_uid
    seq = c.next_seq()
    op = HF.build_opcode(0x01, seq, 0x40)
    frame = HF.pack_json(op, UID, body)
    await c.ws.send(frame)
    print(f"\n[{index}] -> {to_uid} kind={kind} op={op.hex()} frame_len={len(frame)}")
    frames = []
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            raw = await asyncio.wait_for(c.ws.recv(), timeout=max(0.2, deadline - time.time()))
        except asyncio.TimeoutError:
            break
        info = HF.parse(raw)
        frames.append(info)
        body_txt = json.dumps(info.get("body"), ensure_ascii=False) if info.get("body") else info.get("body_hex", "")
        print(f"     <- op={info.get('opcode')} len={info['raw_len']} {body_txt[:300]}")
        if info.get("op_type") in (0x02, 0x17):
            break
    return frames


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--text", default="Hello")
    ap.add_argument("--skip-text", action="store_true")
    a = ap.parse_args()

    if not TARGET.exists():
        print(f"[FAIL] 缺少目标 uid 文件：{TARGET}（写入一个聊天对象的 uid 即可）")
        return 1
    to_uid = int(TARGET.read_text(encoding="utf-8").strip())
    print(f"[i] 目标 uid = {to_uid}")

    c = HC.Client(HC.load_jwt())
    await c.connect()
    print(f"[conn] session_key={c.session_key}")
    try:
        await c.post_handshake()
    except Exception as e:
        print(f"[warn] post_handshake: {type(e).__name__}: {e}")

    if not a.skip_text:
        await send(c, to_uid, "text", "protocol baseline", 0)
        await asyncio.sleep(1.5)

    for i in range(1, a.n + 1):
        await send(c, to_uid, "new_sticker", a.text, i)
        await asyncio.sleep(1.2)
    await c.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
