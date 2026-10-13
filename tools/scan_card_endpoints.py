"""scan_card_endpoints.py — 在 vip/card/trial 相关 smali 里搜接口路径常量"""
import pathlib
import re
import sys

ROOTS = [p for p in pathlib.Path(r"F:\hellotalk-vip\artifacts").glob("apktool*/smali*") if p.is_dir()]
NEEDLES = [
    "member_privilege_center", "vip_card", "privilege_card", "experience_card", "trial_card",
    "vip_trial", "receive_card", "claim", "card/receive", "gift_card", "/vip/",
]
STR = re.compile(r'const-string [pv]\d+, "([^"]+)"')


def iter_files():
    for root in ROOTS:
        for f in root.rglob("*.smali"):
            low = str(f).lower()
            if any(k in low for k in ("vip", "card", "trial", "privilege", "member", "gift")):
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
        low = text.lower()
        if not any(k in low for k in NEEDLES):
            continue
        for m in STR.finditer(text):
            s = m.group(1)
            sl = s.lower()
            if any(k in sl for k in NEEDLES) and len(s) < 100:
                found.setdefault(s, set()).add(f.name)
    print(f"[i] 扫描 {n} 个文件，命中常量 {len(found)} 条\n")
    for s, names in sorted(found.items()):
        print(f"  {s[:80]:<82} {sorted(names)[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
