"""ht_frame.py — HelloTalk ht_im/sock 帧编解码库（已实测）

帧格式:
  magic(4) | opcode(4) | uid(8,LE) | hdr_len(4,LE) | body_len(4,LE) | body

body:
  - zlib.compress(json)                        → 普通业务帧
  - 明文 JSON（不压缩）                        → 握手帧
  - 二进制控制帧（原样透传）

magic:
  f0 04 00 01  客户端上行
  f1 04 00 01  服务端下行
  f5 04 01 00  服务端推送
"""
from __future__ import annotations

import json
import struct
import zlib

MAGIC_UP = b"\xf0\x04\x00\x01"
MAGIC_DN = b"\xf1\x04\x00\x01"
MAGIC_PUSH = b"\xf5\x04\x01\x00"

# 消息类型（opcode 第 1 字节）：UP = 请求，DN = 响应
OP = {
    "handshake": 0x25,
    "handshake_ack": 0x26,
    "pull_msg": 0x0F,
    "pull_msg_ack": 0x10,
    "pull_inbox": 0x45,
    "pull_inbox_ack": 0x46,
    "send_msg": 0x01,
    "send_msg_ack": 0x02,
    "report_id": 0x15,
    "report_id_ack": 0x16,
    "presence": 0x17,
    "trace": 0x21,
    "trace_ack": 0x22,
}


def build_opcode(kind: int, seq: int, marker: int = 0x10) -> bytes:
    """opcode = [type, marker, counter_lo, counter_hi]
    marker 按消息类型固定（实测）：0x10=握手、0x20=轨迹/存在、0x40=收件箱与发送、0x75=消息拉取
    """
    return bytes([kind, marker, seq & 0xFF, (seq >> 8) & 0xFF])


# 各请求类型的 marker 表（来自抓包统计）
MARKER = {
    "handshake": 0x10,
    "pull_msg": 0x75,
    "pull_inbox": 0x40,
    "send_msg": 0x40,
    "trace": 0x20,
    "report_id": 0x40,
    "presence": 0x40,
}


def pack(magic: bytes, opcode: bytes, uid: int, body: bytes) -> bytes:
    """帧 = magic(4) + opcode(4) + uid(8) + body_len(4) + body；body_len 位于 offset 16。"""
    return magic + opcode + struct.pack("<Q", uid) + struct.pack("<I", len(body)) + body


def dumps_ht(obj) -> bytes:
    """HelloTalk 客户端的 JSON 序列化方式（实测反推）：
    紧凑分隔符 + **斜杠转义**（`/` → `\\/`）。
    验证：打招呼帧用此方式序列化 + zlib level 6 → 压缩体 439 字节，与抓包 459 字节帧完全一致。
    """
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("/", "\\/").encode("utf-8")


def pack_json(opcode: bytes, uid: int, obj, *, compress: bool = True, magic: bytes = MAGIC_UP) -> bytes:
    raw = dumps_ht(obj)
    body = zlib.compress(raw) if compress else raw
    return pack(magic, opcode, uid, body)


def body_off(raw: bytes) -> int:
    """帧体起点固定为 20（offset 16 的 u32 是 body_len）。"""
    return 20


def body_of(raw: bytes, off: int = 20) -> bytes | None:
    body = raw[off:]
    if body[:1] == b"{":
        return body
    if body[:2] in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
        try:
            d = zlib.decompressobj()
            return d.decompress(body) + d.flush()
        except zlib.error:
            return None
    return None


def parse(raw: bytes) -> dict:
    out = {"raw_len": len(raw)}
    if len(raw) < 24:
        out["error"] = "too short"
        return out
    out["magic"] = raw[0:4].hex()
    out["opcode"] = raw[4:8].hex()
    out["op_type"] = raw[4]
    out["uid"] = struct.unpack_from("<Q", raw, 8)[0]
    out["hdr_len"] = struct.unpack_from("<I", raw, 16)[0]
    out["body_len"] = struct.unpack_from("<I", raw, 20)[0]
    off = body_off(raw)
    out["body_off"] = off
    body = raw[off:]
    if body[:1] == b"{":
        try:
            out["body"] = json.loads(body.decode("utf-8"))
            out["body_raw"] = body.decode("utf-8")
            return out
        except Exception:
            pass
    if body[:2] in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
        try:
            d = zlib.decompressobj()
            txt = (d.decompress(body) + d.flush()).decode("utf-8")
            out["body"] = json.loads(txt)
            out["body_raw"] = txt
            return out
        except Exception as e:
            out["inflate_error"] = str(e)
    out["body"] = None
    out["body_hex"] = body.hex()
    return out


def build_send_msg(msg_id: str, send_ts_ms: int, text: str, to_uid: int, *, source: str = "Chat List") -> dict:
    """构造发消息 body（打招呼走同一通道，text 由调用方决定）"""
    return {
        "msg": {
            "msg_id": msg_id,
            "send_ts": send_ts_ms,
            "msg_type": "text",
            "text": {"reportIndex": 0, "reportText": "", "text": text},
            "chat_follow_notify": 0,
            "correction_gift_notify": 0,
            "cost_diamonds": 0,
            "pay_chat_cost_virtual_val": 0,
            "pay_chat_switch": 0,
            "recv_diamonds": 0,
            "source": source,
            "to_payer": False,
            "valid_time": 0,
            "bubble": {"id": 0},
            "to_uid": to_uid,
        },
        "version": 394260,
        "client_lang": "Chinese",
    }


if __name__ == "__main__":
    import sys

    for path in sys.argv[1:]:
        data = open(path, "rb").read()
        print(json.dumps(parse(data), ensure_ascii=False, indent=1)[:4000])
