"""extract_hello.py — 从抓包 dump 里抽一条「原样 hello 帧模板」（握手后 JWT 换成最新的）

产出 artifacts/mitm/hello_template.json:
  {"opcode": "2510xxxx", "uid": <UID>, "hello": {...字段原样...}, "jwt": "最新JWT"}
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

OUT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\hello_template.json")
JWT_OUT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\jwt.txt")
TOKEN_RE = re.compile(rb'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}')


def main():
    from mitmproxy import io as mio

    paths = [pathlib.Path(x) for x in sys.argv[1:]] or sorted(
        pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm").glob("*.mitm"), key=lambda p: p.stat().st_mtime
    )
    hello_obj = None
    newest_jwt = None
    tpl = None
    for p in paths:
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    for m in flow.websocket.messages:
                        if not m.from_client:
                            continue
                        raw = bytes(m.content)
                        if raw[:4] != b"\xf0\x04\x00\x01" or raw[4] != 0x25:
                            continue  # 只看客户端握手帧
                        body = HF.body_of(raw)
                        if not body:
                            continue
                        try:
                            obj = json.loads(body.decode("utf-8"))
                        except Exception:
                            continue
                        if "jwt" in obj:
                            hello_obj = obj
                            tpl = {"opcode": raw[4:8].hex(), "uid": int.from_bytes(raw[8:16], "little")}
                        tok = TOKEN_RE.search(body)
                        if tok:
                            newest_jwt = tok.group(0).decode()
        except Exception as e:
            print(f"[warn] {p.name}: {e}")

    if not hello_obj:
        print("[FAIL] 没找到 hello 帧")
        return 1
    if newest_jwt:
        hello_obj["jwt"] = newest_jwt
        JWT_OUT.write_text(newest_jwt, encoding="utf-8")

    fields = [k for k in hello_obj]
    print(f"[OK] hello 模板字段数={len(fields)}: {fields}")
    print(f"     jwt claims 已写入 {JWT_OUT}")
    tpl = dict(tpl or {})
    tpl["hello"] = hello_obj
    OUT.write_text(json.dumps(tpl, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] 模板 -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
