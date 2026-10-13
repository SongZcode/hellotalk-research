"""show_f7s.py — 解析 f7s 接口反射结果，打印 method → url → 参数模型"""
import json
import pathlib
import re
import sys

P = pathlib.Path(r"<WORKDIR>\artifacts\f7s_iface.json")


def main():
    raw = P.read_bytes()
    # PowerShell 重定向会写成 UTF-16LE，去掉 NUL 后按 UTF-8 解
    t = raw.replace(b"\x00", b"").decode("utf-8", "replace")
    t = t[t.find("{"):]
    try:
        d = json.loads(t)
    except Exception as e:
        print("parse fail:", e)
        print(t[:800])
        return 1
    for m in d.get("res", []):
        print(f"  {m['method']:<4} {m['url'][:66]:<68} params={m.get('params')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
