"""scan_vip_files.py — 只扫「文件名含 vip/pay/billing/subscribe 的 smali」+ jadx 同名 Java，快得多

用法: python tools\\scan_vip_files.py
"""
import pathlib
import re
import sys

APK = pathlib.Path(r"<WORKDIR2>\artifacts")
PATH_RE = re.compile(r'"(/[A-Za-z0-9_\-./{}]+)"')
NAME_KEYS = ("vip", "paywall", "billing", "purchase", "subscribe", "subscription", "entitle", "order")


def iter_files():
    for root in APK.glob("apktool*/smali*"):
        for f in root.rglob("*.smali"):
            if any(k in str(f).lower() for k in NAME_KEYS):
                yield f
    jadx = APK / "jadx6"
    if jadx.is_dir():
        for f in jadx.rglob("*.java"):
            if any(k in str(f).lower() for k in NAME_KEYS):
                yield f


def main():
    n = 0
    found = {}
    for f in iter_files():
        n += 1
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in PATH_RE.finditer(text):
            p = m.group(1)
            if any(k in p.lower() for k in ("vip", "pay", "order", "subscri", "purchase", "billing", "product", "entitle")):
                found.setdefault(p, set()).add(f.name)
    print(f"[i] 扫了 {n} 个相关文件，命中路径 {len(found)} 条\n")
    for p, names in sorted(found.items()):
        print(f"  {p:<62} {sorted(names)[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
