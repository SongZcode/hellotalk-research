"""find_apk_sig.py — 定位 `android_apk_signature` 的构造代码（判断上报的是官方签名还是重签后的签名）"""
import pathlib
import re
import sys

ROOTS = [pathlib.Path(r"F:\hellotalk-vip\artifacts\apktool\smali"),
         pathlib.Path(r"F:\hellotalk-vip\artifacts\jadx6")]
KEY = "android_apk_signature"
CTX = 40


def main():
    hits = 0
    for root in ROOTS:
        if not root.is_dir():
            continue
        for f in root.rglob("*"):
            if f.suffix not in (".smali", ".java", ".xml"):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if KEY not in text:
                continue
            hits += 1
            print(f"\n===== {f.relative_to(root.parent)} =====")
            for m in re.finditer(re.escape(KEY), text):
                a = max(0, m.start() - CTX * 6)
                b = min(len(text), m.end() + CTX * 6)
                snippet = text[a:b].replace("\n", " | ")
                print(f"  ...{snippet[:900]}...")
            if hits >= 6:
                return 0
    print(f"[i] 命中文件 {hits} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
