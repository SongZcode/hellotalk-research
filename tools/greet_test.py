"""greet_test.py — 打招呼（new_sticker）配额实验器

能力：
  1. self-test  ：给自己发一条普通消息，验证协议编码与响应链路
  2. scan       ：拉取消息/收件箱，统计收到的 new_sticker（别人给我的打招呼）与相关计数
  3. greet      ：对指定 uid 发 new_sticker 打招呼帧，打印服务端应答（含错误码/剩余次数）
  4. greet-many ：对多个 uid 连续发，观察第 N 次是否出现「超限」错误码

用法:
  python tools\\greet_test.py self-test
  python tools\\greet_test.py scan
  python tools\\greet_test.py greet --to UID [--text Hello]
  python tools\\greet_test.py greet-many --uids 1,2,3
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


def build_send(msg_type: str, payload_key: str, payload: dict, extra: dict | None = None) -> dict:
    """构造发送帧 body；payload_key 形如 'text' / 'new_sticker'"""
    msg = {
        "msg_id": str(uuid.uuid4()),
        "send_ts": int(time.time() * 1000),
        "msg_type": msg_type,
        payload_key: payload,
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
    }
    if extra:
        msg.update(extra)
    return {"msg": msg, "version": 394260, "client_lang": "Chinese"}


async def cmd_self_test(c: "HC.Client"):
    body = build_send("text", "text", {"reportIndex": 0, "reportText": "", "text": "protocol self-test"})
    body["msg"]["to_uid"] = UID  # 发给自己
    res = await c.request(HF.OP["send_msg"], body, wait=(0x02, 0x17, 0x15))
    print("[self-test] 应答:", json.dumps([r["body"] for r in res], ensure_ascii=False)[:900])


async def cmd_scan(c: "HC.Client"):
    """先做连接后固定动作，再拉消息，统计 new_sticker"""
    await c.post_handshake()
    r = await c.request(HF.OP["pull_msg"], {"last_id": 0})
    msgs = []
    for item in r:
        data = (item.get("body") or {}).get("data") or {}
        if data.get("msgs"):
            msgs = data["msgs"]
    print(f"[scan] 拉到 {len(msgs)} 条消息")
    kinds = {}
    for m in msgs:
        mt = m.get("msg_type", "?")
        kinds[mt] = kinds.get(mt, 0) + 1
        print(f"   {m.get('msg_id','')[:8]} type={mt} from={m.get('from_uid')} to={m.get('to_uid')} "
              f"text={json.dumps(m.get('text') or m.get('new_sticker') or {}, ensure_ascii=False)[:80]}")
    print(f"[scan] 类型统计: {kinds}")


async def cmd_greet(c: "HC.Client", to_uid: int, text: str):
    payload = {"helloMsg": 1, "productId": 1, "imageId": 11, "text": text}
    body = build_send("new_sticker", "new_sticker", payload)
    body["msg"]["to_uid"] = to_uid
    body["msg"]["source"] = "New Chat"
    print(f"[greet] -> uid={to_uid} body={json.dumps(body, ensure_ascii=False)[:300]}")
    res = await c.request(HF.OP["send_msg"], body, wait=(0x02, 0x17, 0x15, 0x10))
    for item in res:
        print("[greet] 应答:", json.dumps(item.get("body"), ensure_ascii=False)[:900])


async def cmd_greet_many(c: "HC.Client", uids: list[int], text: str):
    for i, uid in enumerate(uids, 1):
        print(f"\n===== 第 {i} 次 → {uid} =====")
        await cmd_greet(c, uid, text)
        await asyncio.sleep(2)


async def amain():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["self-test", "scan", "greet", "greet-many"])
    ap.add_argument("--to", type=int, default=UID)
    ap.add_argument("--uids", default="")
    ap.add_argument("--text", default="Hi")
    a = ap.parse_args()

    c = HC.Client(HC.load_jwt())
    await c.connect()
    print(f"[conn] session_key={c.session_key}")

    if a.cmd == "self-test":
        await cmd_self_test(c)
    elif a.cmd == "scan":
        await cmd_scan(c)
    elif a.cmd == "greet":
        await cmd_greet(c, a.to, a.text)
    elif a.cmd == "greet-many":
        uids = [int(x) for x in a.uids.split(",") if x.strip()]
        await cmd_greet_many(c, uids, a.text)
    await c.close()


if __name__ == "__main__":
    asyncio.run(amain())
