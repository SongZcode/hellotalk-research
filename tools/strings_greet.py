"""strings_greet.py — 列出与「免费打招呼/次数」相关的字符串资源"""
import pathlib
import re
import sys

PATHS = [
    pathlib.Path(r"F:\hellotalk-vip\artifacts\apktool_clean\res\values-zh-rCN\strings.xml"),
    pathlib.Path(r"F:\hellotalk-vip\artifacts\apktool_clean\res\values\strings.xml"),
]
KEYS = ("greet", "sayhi", "say_hi", "free_", "chat_chance", "stranger")


def main():
    for p in PATHS:
        if not p.exists():
            print(f"(缺) {p}")
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        print(f"\n=== {p.parent.name} ===")
        for m in re.finditer(r'<string name="([^"]+)">([^<]*)</string>', t):
            n, v = m.group(1), m.group(2)
            if any(k in n.lower() for k in KEYS) or "打招呼" in v or "陌生" in v or "免费" in v:
                print(f"  {n:<44} = {v[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
