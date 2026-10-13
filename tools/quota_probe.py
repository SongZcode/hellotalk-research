"""quota_probe.py — 配额来源实验：打招呼限制到底绑在「账号」还是「设备」上

实验设计（同一账号、同一配额耗尽的时刻）：
  A. 正常握手（用抓包原始 device_id）→ 发一条打招呼帧 → 看返回 notice_type
  B. 改 device_id / device_detail / mobile_operator 后重建会话 → 发同样打招呼帧
  C. 额外：把 source 从 "All Hand" 换成别的入口值，看配额是否分桶

判定：
  - 若 A 与 B 都是 notice_type=18 → 配额绑账号（且与入口无关），设备轮换无效
  - 若 B 不再报 18 → 配额绑设备 → 存在真实绕过路径（轮换 device_id）
  - 若 C 不报 18 → 不同入口配额分桶 → 多入口可叠加
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import time
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_client as HC  # noqa: E402
import ht_frame as HF  # noqa: E402

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
EV = json.loads((ROOT / "greet_evidence.json").read_text(encoding="utf-8"))
GREET_BODY = EV["greet_up"]["body"]


def build_greet(*, msg_id: str | None = None, source: str = "All Hand", with_to: int | None = None) -> dict:
    body = json.loads(json.dumps(GREET_BODY))  # deep copy
    msg = body["msg"]
    msg["msg_id"] = msg_id or str(uuid.uuid4())
    msg["send_ts"] = int(time.time() * 1000)
    msg["source"] = source
    if with_to is not None:
        msg["to_uid"] = with_to
    return body


async def attempt(label: str, *, mutate_hello: dict | None = None, source: str = "All Hand",
                  with_to: int | None = None):
    hello = HC.load_hello()
    if mutate_hello:
        hello = dict(hello)
        hello.update(mutate_hello)
    c = HC.Client(HC.load_jwt())
    c.hello_override = hello  # 供 connect 使用
    await c.connect()
    print(f"\n=== {label} ===")
    print(f"    hello.device_id = {hello.get('device_id')}")
    body = build_greet(source=source, with_to=with_to)
    seq = c.next_seq()
    op = HF.build_opcode(0x01, seq, 0x40)
    frame = HF.pack_json(op, HC.UID, body)
    await c.ws.send(frame)
    res = []
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            raw = await asyncio.wait_for(c.ws.recv(), timeout=max(0.2, deadline - time.time()))
        except asyncio.TimeoutError:
            break
        info = HF.parse(raw)
        if info.get("body"):
            print(f"    <- op={info.get('opcode')} {json.dumps(info['body'], ensure_ascii=False)[:400]}")
            res.append(info["body"])
        else:
            print(f"    <- op={info.get('opcode')} BIN {info.get('body_hex','')[:60]}")
        if info.get("op_type") in (0x02, 0x17):
            break
    await c.close()
    return res


async def main():
    # A: 原样（原始 device_id）
    await attempt("A 原始 device_id / source=All Hand")

    # B: 轮换 device_id + device_detail
    await attempt(
        "B 轮换 device_id",
        mutate_hello={
            "device_id": uuid.uuid4().hex,
            "device_detail": "<DEVICE_MODEL>#1280X2772#394#394#520#n#6.8",
        },
    )

    # C: 换入口 source
    await attempt("C source=Chat List", source="Chat List")

    # D: 显式带 to_uid（看是否改变判定）
    await attempt("D source=Nearby", source="Nearby")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
