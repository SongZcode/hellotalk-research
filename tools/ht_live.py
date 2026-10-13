r"""ht_live.py — mitmproxy addon：实时解码 HelloTalk 的 WS 帧（zlib JSON）与 HTTP 明文

用法:
  mitmdump -p 8080 --set block_global=false -s tools/ht_live.py -w artifacts/mitm/flows.mitm

输出:
  artifacts/mitm/api.log    —— 人类可读时间线（HTTP 摘要 + WS 明文 JSON + 十六进制兜底）
  artifacts/mitm/ws.jsonl   —— 每条 WS 帧一行 JSON（含 seq/opcode/body），便于后续统计

帧结构（已实测 2026-10-11）:
  magic(4B) | opcode(4B) | uid(8B) | hdrlen(4B) | bodylen(4B) | body
  body 若以 78 9c 开头 = zlib 压缩的 JSON；f5 开头为二进制专属帧（另有编码）
"""
from __future__ import annotations

import json
import pathlib
import struct
import time
import zlib

from mitmproxy import http

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
LOG = ROOT / "api.log"
JSONL = ROOT / "ws.jsonl"
SKIP_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".m4a", ".ttf", ".otf", ".zip", ".apk")
ZLIB_MAGIC = (b"\x78\x01", b"\x78\x9c", b"\x78\xda")


def _w(line: str) -> None:
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(time.strftime("%H:%M:%S ") + line + "\n")


def _jsonl(rec: dict) -> None:
    with open(JSONL, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def decode_frame(raw: bytes):
    """返回 (header dict, body bytes|None)"""
    hdr = {}
    if len(raw) >= 24:
        hdr["magic"] = raw[0:4].hex()
        hdr["opcode"] = raw[4:8].hex()
        hdr["uid"] = struct.unpack_from("<Q", raw, 8)[0]
        hdr["hdr_len"] = struct.unpack_from("<I", raw, 16)[0]
        hdr["body_len"] = struct.unpack_from("<I", raw, 20)[0]
    zoff = -1
    for i in range(0, min(len(raw), 64)):
        if raw[i : i + 2] in ZLIB_MAGIC:
            zoff = i
            break
    if zoff < 0:
        return hdr, None
    try:
        out = zlib.decompressobj().decompress(raw[zoff:])
        return hdr, out
    except zlib.error:
        return hdr, None


def response(flow: http.HTTPFlow) -> None:
    url = flow.request.pretty_url
    if any(url.lower().split("?")[0].endswith(e) for e in SKIP_EXT):
        return
    code = flow.response.status_code if flow.response else 0
    _w(f"[{code}] {flow.request.method} {url}")
    if "hellotalk" not in url:
        return
    try:
        req = flow.request.get_text(strict=False) or ""
        resp = flow.response.get_text(strict=False) or "" if flow.response else ""
    except Exception:
        return
    if req:
        _w("   REQ  " + " ".join(req.split())[:600])
    if resp:
        _w("   RESP " + " ".join(resp.split())[:600])


def websocket_message(flow: http.HTTPFlow) -> None:
    try:
        m = flow.websocket.messages[-1]
    except Exception:
        return
    raw = bytes(m.content)
    direction = "SEND" if m.from_client else "RECV"
    hdr, body = decode_frame(raw)
    # jsonl 里始终保存原始十六进制（便于字节级复刻/重放）
    rec = {"t": m.timestamp, "dir": direction, "len": len(raw), "hdr": hdr, "raw_hex": raw.hex()}
    if body is not None:
        text = body.decode("utf-8", "replace")
        rec["body"] = text
        _w(f"   WS {direction} op={hdr.get('opcode')} seq-> {text[:900]}")
    else:
        _w(f"   WS {direction} len={len(raw)} op={hdr.get('opcode')} BIN {raw[:64].hex()}")
    _jsonl(rec)
