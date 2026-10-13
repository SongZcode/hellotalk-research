"""list_https_api.py — 汇总已解密的 HelloTalk HTTP 接口（含参数与响应摘要）"""
import collections
import pathlib
import re

LOG = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\api.log")
RE_REQ = re.compile(r"\[(\d+)\] (GET|POST) (https://[^\s]+)")
RE_RESP = re.compile(r"RESP (.*)")


def main():
    text = LOG.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    eps = collections.OrderedDict()
    cur = None
    for ln in lines:
        m = RE_REQ.search(ln)
        if m:
            code, method, url = m.group(1), m.group(2), m.group(3)
            path = url.split("?")[0]
            qs = url.split("?", 1)[1] if "?" in url else ""
            eps[path] = eps.get(path, {"n": 0, "codes": set(), "sample_qs": qs[:400], "resp": None})
            eps[path]["n"] += 1
            eps[path]["codes"].add(code)
            cur = path
            continue
        if ln.strip().startswith("RESP") and cur:
            body = ln.strip()[5:]
            if eps[cur]["resp"] is None:
                printable = sum(1 for c in body[:200] if 32 <= ord(c) < 127) / max(1, len(body[:200]))
                eps[cur]["resp"] = ("明文: " + body[:160]) if printable > 0.85 else f"二进制/加密({len(body)}B)"
            continue
        if "WS " in ln:
            cur = None

    print(f"=== 已解密 HelloTalk 接口 {len(eps)} 个 ===\n")
    for p, v in eps.items():
        print(f"  x{v['n']:<3}  [{','.join(sorted(v['codes']))}]  {p}")
        print(f"        参数样例: {v['sample_qs'][:220]}")
        print(f"        响应: {v['resp']}")


if __name__ == "__main__":
    main()
