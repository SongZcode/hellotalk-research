"""scan_trial.py — 定位 VIP 试用/体验卡相关类与接口（只读，限定文件名关键词，快）

用法: python tools\\scan_trial.py
"""
import pathlib
import re
import sys

APK = pathlib.Path(r"<WORKDIR2>\artifacts")
KEY = ("trial", "experience", "privilege", "member", "vipplus", "vipprivilege")
STR_RE = re.compile(r'"(/[A-Za-z0-9_\-./{}]+)"')
CONST_RE = re.compile(r'const-string [pv]\d+, "([^"]{4,80})"')


def iter_files():
    for root in APK.glob("apktool*/smali*"):
        for f in root.rglob("*.smali"):
            low = str(f).lower()
            if any(k in low for k in KEY):
                yield f


def main():
    n = 0
    paths = {}
    strings = {}
    for f in iter_files():
        n += 1
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in STR_RE.finditer(text):
            p = m.group(1)
            if any(k in p.lower() for k in ("trial", "vip", "privilege", "member", "pay")):
                paths.setdefault(p, f.name)
        for m in CONST_RE.finditer(text):
            s = m.group(1)
            if any(k in s.lower() for k in ("trial", "experience", "vip")):
                strings.setdefault(s, f.name)

    print(f"[i] 扫了 {n} 个相关 smali 文件")
    print(f"\n=== 接口路径 ({len(paths)}) ===")
    for p, f in sorted(paths.items())[:40]:
        print(f"  {p:<64} {f}")
    print(f"\n=== 关键字符串 ({len(strings)}) ===")
    for s, f in sorted(strings.items())[:40]:
        print(f"  {s[:70]:<72} {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
