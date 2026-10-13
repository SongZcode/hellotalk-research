"""dex_ui_strings.py — 从 dex 里找与激励视频/次数相关的 UI 文案（定位入口）"""
import pathlib
import re
import sys
import zipfile

APK = pathlib.Path(r"F:\hellotalk-vip\samples\xapk\com.hellotalk.apk")
CJK = re.compile(rb"(?:[\xe4-\xe9][\x80-\xbf]{2}){2,16}")
KEYS = ["激励", "视频", "看广告", "次数", "免费", "领取", "获得", "体验卡", "试用"]


def main():
    hits = set()
    with zipfile.ZipFile(APK) as z:
        for n in z.namelist():
            if not n.endswith(".dex"):
                continue
            data = z.read(n)
            for m in CJK.finditer(data):
                try:
                    s = m.group(0).decode("utf-8")
                except Exception:
                    continue
                if len(s) > 40:
                    continue
                if any(k in s for k in ("激励", "看广告", "看视频", "体验卡", "试用")):
                    hits.add(s)
    print(f"命中 {len(hits)} 条：")
    for s in sorted(hits):
        print("  ", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
