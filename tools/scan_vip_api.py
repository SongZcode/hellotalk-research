"""scan_vip_api.py — 在反编译产物里找「VIP/支付/订阅」相关的接口路径与验证逻辑

只读扫描：先从 smali 里抽字符串常量（接口路径），再按关键词分组输出。
用法: python tools\\scan_vip_api.py [--limit 400]
"""
import argparse
import collections
import pathlib
import re
import sys

SMALI_ROOTS = [
    pathlib.Path(r"F:\hellotalk-vip\artifacts\apktool\smali"),
    pathlib.Path(r"F:\hellotalk-vip\artifacts\apktool_raw\smali"),
]
EXTRA = list(pathlib.Path(r"F:\hellotalk-vip\artifacts").glob("apktool*/smali*"))

PATHS = re.compile(r'"/(?:[A-Za-z0-9_\-./{}]+)"')
KEYWORDS = ("vip", "pay", "purchase", "billing", "order", "subscri", "product", "entitle", "redeem", "coupon")


def roots():
    seen, out = set(), []
    for r in SMALI_ROOTS + EXTRA:
        if r.is_dir() and r not in seen:
            seen.add(r)
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=400)
    a = ap.parse_args()

    hits = collections.defaultdict(set)
    files = 0
    for root in roots():
        for f in root.rglob("*.smali"):
            files += 1
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            low = text.lower()
            if not any(k in low for k in ("vip", "purchase", "billing")):
                continue
            for m in PATHS.finditer(text):
                p = m.group(0).strip('"')
                pl = p.lower()
                if any(k in pl for k in KEYWORDS):
                    hits[p].add(str(f.relative_to(root)))
    print(f"[i] 扫描 smali 文件 {files} 个")
    print(f"[i] 命中接口路径 {len(hits)} 条\n")
    for p, where in sorted(hits.items())[: a.limit]:
        w = sorted(where)[0]
        print(f"  {p:<70} {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
