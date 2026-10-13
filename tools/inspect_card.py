"""inspect_card.py — 检查 VIP 体验卡/试用相关类：字符串、方法调用、card_id 来源"""
import glob
import pathlib
import re
import sys

NAMES = [
    "VipTrialUnlockDialog.smali",
    "TalkGiftVIPExperienceCardDialog.smali",
    "FreeTrialVipShopPage.smali",
    "VipRetentionDialog.smali",
]
STR = re.compile(r'const-string [pv]\d+, "([^"]+)"')
CALL = re.compile(r'invoke-[a-z/]+ \{[^}]*\}, L([A-Za-z0-9_/$]+)->([A-Za-z0-9_<>]+)\(([^)]*)\)')


def main():
    for pat in NAMES:
        hits = glob.glob(rf"<WORKDIR2>\artifacts\apktool*\**\{pat}", recursive=True)
        if not hits:
            print(f"未找到 {pat}")
            continue
        f = pathlib.Path(hits[0])
        t = f.read_text(encoding="utf-8", errors="replace")
        print(f"\n{'='*24} {pat}  ({f.parent.name})")
        seen = set()
        for m in STR.finditer(t):
            s = m.group(1)
            if s in seen:
                continue
            seen.add(s)
            if any(k in s.lower() for k in ("card", "trial", "privilege", "receive", "claim", "vip", "/")):
                print(f"   STR: {s[:90]}")
        print("   --- 相关方法调用 ---")
        seen2 = set()
        for m in CALL.finditer(t):
            cls, meth, args = m.group(1), m.group(2), m.group(3)
            key = cls + "." + meth
            if key in seen2:
                continue
            if any(k in (cls + meth).lower() for k in ("card", "trial", "privilege", "vip", "gift", "pay")):
                seen2.add(key)
                print(f"   CALL: {cls}.{meth}({args[:50]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
