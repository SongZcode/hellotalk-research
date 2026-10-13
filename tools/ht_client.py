"""ht_client.py — HelloTalk ht_im/sock 独立协议客户端（PC 侧直连）

用途：不经过手机端 App，用抓包得到的 JWT 直接建立 WS 会话，收发协议帧。
  - 验证帧编解码是否正确
  - 拉取会话列表（找 test 目标）
  - 重放/新造打招呼帧，观察服务端配额错误码

用法:
  python tools\\ht_client.py login                  # 握手 + 打印 session_key/服务端首帧
  python tools\\ht_client.py inbox                  # 拉收件箱（packet_list）
  python tools\\ht_client.py pull                   # 拉消息（msgs）
  python tools\\ht_client.py send --to UID --text hi
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import ssl
import sys
import time
import uuid
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

import websockets  # noqa: E402

URL = "wss://api-cn.hellotalk8.com/ht_im/sock?userid={uid}"
UID = <UID>
JWT_FILE = pathlib.Path(r"<WORKDIR>\artifacts\mitm\jwt.txt")
LOG = pathlib.Path(r"<WORKDIR>\artifacts\mitm\client.log")

HELLO = {
    "jwt": "",
    "mobile_operator": "中国联通",
    "operator_country": "cn",
    "android_apk_signature": "75b0bcd304efdc70120131e22f24d850f708fe4fa50bbe32a72e87cdb6d408d41791724176",
    "app_version": "6.4.20(11674,google)",
    "background_reconnect": 0,
    "channel": "com.hellotalk.core.app.NihaotalkApplication",
    "client_lang": "Chinese",
    "current_version": 394260,
    "device_detail": "<DEVICE_MODEL>#1280X2772#394#394#520#n#6.8",
    "device_id": "<DEVICE_ID>",
    "is_version_update": 0,
    "install_type": 0,
    "net_type": 1,
    "os_lang": "zh",
    "os_version": "16",
    "terminal_type": 1,
}


def log(line: str):
    stamp = time.strftime("%H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")
    print(f"{stamp} {line}", flush=True)


def pack_plain(opcode: bytes, uid: int, obj) -> bytes:
    """明文帧（握手帧格式）：magic|opcode|uid | body_len(4) | body（无额外 4 字节长度字段）"""
    body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return HF.MAGIC_UP + opcode + uid.to_bytes(8, "little") + len(body).to_bytes(4, "little") + body


def load_hello() -> dict:
    """优先用抓包原样模板（字段不多不少），失败退回内置默认。"""
    tpl_file = pathlib.Path(r"<WORKDIR>\artifacts\mitm\hello_template.json")
    if tpl_file.exists():
        try:
            return json.loads(tpl_file.read_text(encoding="utf-8"))["hello"]
        except Exception as e:
            log(f"[warn] hello 模板读取失败: {e}")
    return dict(HELLO)


def load_jwt() -> str:
    if JWT_FILE.exists():
        tok = JWT_FILE.read_text(encoding="utf-8").strip()
        if tok.count(".") == 2:
            return tok
    raise SystemExit(f"no jwt at {JWT_FILE} — 先跑 tools/extract_jwt.py")


class Client:
    def __init__(self, jwt: str):
        self.jwt = jwt
        self.seq = 0
        self.ws = None
        self.session_key = None
        self.inbox: list = []

    def next_seq(self) -> int:
        self.seq = (self.seq + 1) & 0xFFFF
        return self.seq

    async def connect(self):
        # websockets 13.x 的旧客户端用 extra_headers
        ctx = ssl.create_default_context()
        extra = {k: v for k, v in {"User-Agent": "okhttp/5.3.2"}.items()}
        hdr_file = pathlib.Path(r"<WORKDIR>\artifacts\mitm\ws_headers.json")
        if hdr_file.exists():
            try:
                extra.update(json.loads(hdr_file.read_text(encoding="utf-8")))
            except Exception as e:
                log(f"[warn] headers 模板读取失败: {e}")
        # 保证 token 是最新的
        for k in list(extra):
            if k.lower() == "x-ht-token":
                extra[k] = "Bearer " + self.jwt
        extra.setdefault("Origin", "https://www.hellotalk.com")
        self.ws = await websockets.connect(
            URL.format(uid=UID),
            ssl=ctx,
            max_size=None,
            open_timeout=20,
            extra_headers=extra,
        )
        log(f"[conn] {URL.format(uid=UID)}")
        # 握手（优先复刻抓包原始帧，只替换 JWT；允许外部覆盖 hello 字段）
        hello = getattr(self, "hello_override", None) or load_hello()
        hello = dict(hello)
        hello["jwt"] = self.jwt
        seq = self.next_seq()
        op = HF.build_opcode(HF.OP["handshake"], seq)
        frame = pack_plain(op, UID, hello)

        orig = pathlib.Path(r"<WORKDIR>\artifacts\mitm\hello_orig.bin")
        if orig.exists():
            ob = orig.read_bytes()
            same = sum(1 for a, b in zip(ob, frame) if a == b)
            diffpos = [i for i, (a, b) in enumerate(zip(ob, frame)) if a != b]
            log(f"[hello] len={len(frame)} vs 原始 len={len(ob)} 相同={same}/{len(ob)} 差异位置={diffpos[:8]}")

        await self.ws.send(frame)
        log(f"[send] handshake seq={seq} len={len(frame)}")
        raw = await asyncio.wait_for(self.ws.recv(), timeout=20)
        info = HF.parse(raw)
        log(f"[recv raw] len={len(raw)} hex={bytes(raw)[:100].hex()}")
        log(f"[recv] handshake ack: {json.dumps(info.get('body'), ensure_ascii=False)[:400]}")
        data = (info.get("body") or {}).get("data") or {}
        self.session_key = data.get("session_key")
        if data.get("jwt"):
            self.jwt = data["jwt"]
        return info

    async def request(self, kind_up: int, payload, *, compress: bool = True, wait: tuple[int, ...] | None = None,
                      marker: int | None = None):
        """发一帧并按 op_type 等响应；返回响应列表"""
        want = wait or ((kind_up + 1) & 0xFF,)
        seq = self.next_seq()
        if marker is None:
            name = {v: k for k, v in HF.OP.items()}.get(kind_up, "")
            marker = HF.MARKER.get(name, 0x10)
        op = HF.build_opcode(kind_up, seq, marker)
        frame = HF.pack_json(op, UID, payload, compress=compress)
        await self.ws.send(frame)
        log(f"[send] op={op.hex()} {str(payload)[:160]}")
        got = []
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=max(0.2, deadline - time.time()))
            except asyncio.TimeoutError:
                break
            info = HF.parse(raw)
            body = info.get("body")
            log(f"[recv] op={info.get('opcode')} {json.dumps(body, ensure_ascii=False)[:300] if body else info.get('body_hex', '')[:80]}")
            if info.get("op_type") in want:
                got.append(info)
                break
            if info.get("op_type") == kind_up and info.get("body") is None:
                got.append(info)  # 服务端拒绝（echo 我们的 opcode + 4 字节 0）
                break
        return got

    # ---- 复刻 App 握手后的标准动作（顺序不能变，否则服务端不回包）----
    async def send_raw(self, raw: bytes, label: str = ""):
        await self.ws.send(raw)
        log(f"[send-raw] {label} len={len(raw)} op={raw[4:8].hex()}")

    def trace_frame(self, counter: int | None = None) -> bytes:
        """Trace 帧：8 字节体（uid + 自增计数器），App 每次连上都会发"""
        if counter is None:
            counter = int(time.time()) & 0xFFFFFFFF
        body = UID.to_bytes(4, "little") + counter.to_bytes(4, "little")
        op = HF.build_opcode(0x21, self.next_seq())
        return HF.pack(HF.MAGIC_UP, op, UID, body)

    async def post_handshake(self):
        """App 连上后的固定序列：pull_msg → pull_inbox → trace"""
        res = {}
        r1 = await self.request(HF.OP["pull_msg"], {"last_id": 0})
        res["pull_msg"] = r1[0]["body"] if r1 else None
        r2 = await self.request(HF.OP["pull_inbox"], {"last_id": 0})
        res["pull_inbox"] = r2[0]["body"] if r2 else None
        await self.send_raw(self.trace_frame(), "trace")
        # trace 的回包（22 类型）+ 可能的推送
        for _ in range(4):
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=3)
            except asyncio.TimeoutError:
                break
            info = HF.parse(raw)
            log(f"[push] op={info.get('opcode')} {json.dumps(info.get('body'), ensure_ascii=False)[:200] if info.get('body') else info.get('body_hex','')[:60]}")
        return res

    async def close(self):
        if self.ws:
            await self.ws.close()


async def amain():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["login", "session", "inbox", "pull", "send", "listen"])
    ap.add_argument("--to", type=int, default=0)
    ap.add_argument("--text", default="hi")
    ap.add_argument("--seconds", type=int, default=30)
    a = ap.parse_args()

    c = Client(load_jwt())
    await c.connect()
    if a.cmd == "login":
        log(f"[ok] session_key={c.session_key}")
    elif a.cmd == "session":
        res = await c.post_handshake()
        log(f"[session] pull_msg={json.dumps(res.get('pull_msg'), ensure_ascii=False)[:600]}")
        log(f"[session] pull_inbox={json.dumps(res.get('pull_inbox'), ensure_ascii=False)[:900]}")
    elif a.cmd == "inbox":
        res = await c.request(HF.OP["pull_inbox"], {"last_id": 0})
        log(f"[inbox] {json.dumps(res[0]['body'] if res else None, ensure_ascii=False)[:2000]}")
    elif a.cmd == "pull":
        res = await c.request(HF.OP["pull_msg"], {"last_id": 0})
        log(f"[pull] {json.dumps(res[0]['body'] if res else None, ensure_ascii=False)[:2000]}")
    elif a.cmd == "send":
        msg_id = str(uuid.uuid4())
        send_ts = int(time.time() * 1000)
        payload = HF.build_send_msg(msg_id, send_ts, a.text, a.to)
        res = await c.request(HF.OP["send_msg"], payload, wait=(HF.OP["send_msg_ack"], 0x22, 0x15))
        log(f"[send result] {json.dumps([r['body'] for r in res], ensure_ascii=False)[:1500]}")
    elif a.cmd == "listen":
        end = time.time() + a.seconds
        while time.time() < end:
            try:
                raw = await asyncio.wait_for(c.ws.recv(), timeout=max(0.2, end - time.time()))
            except asyncio.TimeoutError:
                break
            info = HF.parse(raw)
            body = info.get("body")
            log(f"[push] op={info.get('opcode')} {json.dumps(body, ensure_ascii=False)[:300] if body else info.get('body_hex', '')[:80]}")
    await c.close()


if __name__ == "__main__":
    asyncio.run(amain())
