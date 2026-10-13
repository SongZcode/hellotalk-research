r"""vip_cover.py — mitmproxy addon：把「VIP 状态不一致上报」伪装成一致

背景（实测）：
  App 启动/进会员页时会 POST /safety/v1/vip_status_report：
    {"app_version":"...","device_id":"...","os_type":1,
     "client_vip_status":2147483647,      ← 本地被 patch 的值（0x7FFFFFFF）
     "server_vip_status":1790022926}      ← 服务端 vip_expire
  这是反篡改埋点：把「客户端说自己 VIP / 服务端说不是」的差异报给服务端。

本 addon 做的事：把请求体里的 client_vip_status 改写成 server_vip_status，
使上报看起来一致（不阻断请求，避免行为异常）。

用法: mitmdump -p 8080 -s tools/ht_live.py -s tools/vip_cover.py -w ...
"""
import json
import pathlib
import time

from mitmproxy import http

LOG = pathlib.Path(r"<WORKDIR>\artifacts\mitm\vip_cover.log")
TARGET = "/safety/v1/vip_status_report"


def _w(msg: str) -> None:
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(time.strftime("%H:%M:%S ") + msg + "\n")


def request(flow: http.HTTPFlow) -> None:
    if TARGET not in flow.request.path:
        return
    try:
        body = flow.request.get_text(strict=False) or ""
        if not body.strip().startswith("{"):
            return
        obj = json.loads(body)
        before = obj.get("client_vip_status")
        srv = obj.get("server_vip_status")
        if before == srv:
            _w(f"[cover] 本来就一致 ({before}) 无需改写")
            return
        obj["client_vip_status"] = srv
        new = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        flow.request.set_text(new)
        flow.request.headers["content-length"] = str(len(new.encode("utf-8")))
        _w(f"[cover] 改写 client_vip_status: {before} -> {srv}")
    except Exception as e:
        _w(f"[cover] 改写失败: {type(e).__name__}: {e}")
