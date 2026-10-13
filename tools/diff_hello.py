"""diff_hello.py — 逐字节对比 hello 模板与抓包原始帧，定位差异位置（支持 --set-jwt）"""
import argparse
import json
import pathlib
import sys

T = pathlib.Path(r"<WORKDIR>\artifacts\mitm\hello_template.json")
O = pathlib.Path(r"<WORKDIR>\artifacts\mitm\hello_orig.bin")
J = pathlib.Path(r"<WORKDIR>\artifacts\mitm\jwt.txt")


def first_diff(a: bytes, b: bytes):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n if len(a) != len(b) else -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set-jwt", action="store_true", help="用 jwt.txt 覆盖模板 jwt 后再对比")
    a = ap.parse_args()

    tpl = json.loads(T.read_text(encoding="utf-8"))
    hello = tpl["hello"]
    if a.set_jwt:
        hello = dict(hello)
        hello["jwt"] = J.read_text(encoding="utf-8").strip()

    body_t = json.dumps(hello, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    orig = O.read_bytes()
    body_o = orig[20:]

    print(f"template body = {len(body_t)} bytes")
    print(f"original  body = {len(body_o)} bytes")
    i = first_diff(body_t, body_o)
    print(f"first diff at byte {i}")
    if i >= 0:
        print(f"  template: ...{body_t[max(0,i-60):i+80]!r}")
        print(f"  original: ...{body_o[max(0,i-60):i+80]!r}")

    # 字段级对比
    try:
        o = json.loads(body_o.decode("utf-8"))
        tk = set(o) - set(hello)
        hk = set(hello) - set(o)
        print(f"only in original: {sorted(tk)}")
        print(f"only in template: {sorted(hk)}")
        for k in sorted(set(hello) & set(o)):
            if hello[k] != o[k]:
                print(f"  diff field {k}: template={str(hello[k])[:60]!r} original={str(o[k])[:60]!r}")
    except Exception as e:
        print(f"orig parse fail: {e}")


if __name__ == "__main__":
    main()
