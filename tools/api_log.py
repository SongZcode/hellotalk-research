"""api_log.py — HelloTalk 流量摘要（含时间戳，便于对齐"第11次打招呼"时刻）"""
import time
from mitmproxy import http

LOG = r"<WORKDIR>\artifacts\mitm\api.log"
SKIP_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".m4a", ".ttf", ".otf", ".zip", ".apk")

def _w(line: str) -> None:
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(time.strftime("%H:%M:%S ") + line + "\n")

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
        _w("   REQ  " + " ".join(req.split())[:400])
    if resp:
        _w("   RESP " + " ".join(resp.split())[:400])

def websocket_message(flow: http.HTTPFlow) -> None:
    try:
        m = flow.websocket.messages[-1]
    except Exception:
        return
    data = m.content
    txt = data.decode("utf-8", "replace") if isinstance(data, (bytes, bytearray)) else str(data)
    _w(f"   WS {'SEND' if m.from_client else 'RECV'} len={len(data)} " + " ".join(txt.split())[:120])