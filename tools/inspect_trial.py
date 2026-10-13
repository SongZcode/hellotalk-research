"""inspect_trial.py — 查看 VIP 试用/体验卡相关类的关键字符串与调用（只读）"""
import glob
import pathlib
import re
import sys

NAMES = [
    "VipTrialUnlockDialog.smali",
    "FreeTrialVipShopPage.smali",
    "TalkGiftVIPExperienceCardDialog.smali",
    "VipRetentionDialog.smali",
    "StarterDiscountGroupVipPlusActivity.smali",
]
STR = re.compile(r'const-string [pv]\d+, "([^"]+)"')


def main():
    for n in NAMES:
        hits = glob.glob(rf"F:\hellotalk-vip\artifacts\apktool*\**\{n}", recursive=True)
        if not hits:
            print(f"--- {n}: 未找到")
            continue
        f = pathlib.Path(hits[0])
        t = f.read_text(encoding="utf-8", errors="replace")
        print(f"\n{'='*18} {n}  ({len(t)}B)  {f.parent.name}")
        seen = set()
        for m in STR.finditer(t):
            s = m.group(1)
            if s in seen:
                continue
            seen.add(s)
            if any(k in s.lower() for k in ("vip", "trial", "/", "api", "card", "privilege", "member", "expire")):
                print(f"   {s[:110]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
