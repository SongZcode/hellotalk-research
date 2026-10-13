"""find_card_api.py — 定位 VIP 体验卡/试用卡的接口路径与 card_id 来源"""
import pathlib
import re
import sys

ROOTS = [p for p in pathlib.Path(r"<WORKDIR2>\artifacts").glob("apktool*/smali*") if p.is_dir()]
STR = re.compile(r'const-string [pv]\d+, "([^"]+)"')
INTEREST = re.compile(r"(card|trial|privilege|experience)", re.I)
URLISH = re.compile(r"^/|https?://")


def main():
    hits_path = {}
    hits_key = {}
    for root in ROOTS:
        for f in root.rglob("*.smali"):
            name = f.name.lower()
            low = str(f).lower()
            # 先按文件名粗筛，减少读取量
            if not any(k in low for k in ("card", "trial", "privilege", "vip")):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in STR.finditer(text):
                s = m.group(1)
                if URLISH.search(s) and INTEREST.search(s):
                    hits_path.setdefault(s, f.name)
                elif INTEREST.search(s) and len(s) < 60:
                    hits_key.setdefault(s, f.name)
    print(f"=== URL 形态（card/trial 相关）{len(hits_path)} 条 ===")
    for p, fn in sorted(hits_path.items())[:40]:
        print(f"  {p:<60} {fn}")
    print(f"\n=== 关键字符串 {len(hits_key)} 条 ===")
    for k, fn in sorted(hits_key.items())[:50]:
        print(f"  {k:<58} {fn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
