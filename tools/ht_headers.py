"""ht_headers.py — 从抓包里抽出 WS 升级请求头，生成 ht_client 用的 headers 模板

产出 artifacts/mitm/ws_headers.json（x-ht-token 里的 JWT 会被替换成最新 jwt.txt）
"""
import json
import pathlib
import re
import sys

from mitmproxy import io as mio

OUT = pathlib.Path(r"<WORKDIR>\artifacts\mitm\ws_headers.json")
JWT = pathlib.Path(r"<WORKDIR>\artifacts\mitm\jwt.txt")
SKIP = {"upgrade", "connection", "sec-websocket-key", "sec-websocket-version", "sec-websocket-extensions",
        "host", "accept-encoding", "x-b3-spanid", "x-b3-traceid", "x-b3-sampled"}


def main():
    paths = [pathlib.Path(x) for x in sys.argv[1:]] or sorted(
        pathlib.Path(r"<WORKDIR>\artifacts\mitm").glob("*.mitm"), key=lambda p: p.stat().st_mtime
    )
    headers = None
    for p in reversed(paths):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    if "ht_im/sock" not in flow.request.pretty_url:
                        continue
                    headers = {k: v for k, v in flow.request.headers.items() if k.lower() not in SKIP}
                    break
        except Exception as e:
            print(f"[warn] {p.name}: {e}")
        if headers:
            break

    if not headers:
        print("[FAIL] 没找到 WS 升级请求头")
        return 1

    jwt = JWT.read_text(encoding="utf-8").strip() if JWT.exists() else ""
    if jwt:
        for k in list(headers):
            if k.lower() == "x-ht-token":
                headers[k] = "Bearer " + jwt
    print("[OK] headers:")
    for k, v in headers.items():
        print(f"     {k}: {v[:90]}")
    OUT.write_text(json.dumps(headers, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
