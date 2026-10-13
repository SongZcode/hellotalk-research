"""list_api_urls.py — 从抓包/日志里统计 App 访问（含失败）过的 api-cn 接口"""
import collections
import pathlib
import re

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
RE_URL = re.compile(r"https://api-cn\.hellotalk8\.com[A-Za-z0-9_\-./?=&%]+")


def main():
    urls = collections.Counter()
    for name in ("api.log", "mitm_greet.out", "mitm_run1.out", "flows.dec.txt", "flows2.dec.txt", "run1.dec.txt"):
        p = ROOT / name
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        for m in RE_URL.finditer(t):
            urls[m.group(0).split("?")[0]] += 1
    print(f"=== App 尝试访问过的 api-cn 接口（{len(urls)} 个，含失败请求）===")
    for u, c in urls.most_common(80):
        print(f"  {c:>4}  {u}")


if __name__ == "__main__":
    main()
