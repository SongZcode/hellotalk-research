"""list_all_paths.py — 汇总所有抓到的接口路径（去重），并按关键词分类"""
import collections
import pathlib
import re

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
PAT = re.compile(r"\[(\d+)\] (GET|POST) (https?://[^\s]+)")
PAT2 = re.compile(r"(GET|POST) (https?://[^\s]+)")


def main():
    seen = collections.Counter()
    for p in ROOT.glob("*"):
        if p.suffix not in (".log", ".txt", ".out"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in PAT.finditer(text):
            seen[m.group(3).split("?")[0]] += 1
        for m in PAT2.finditer(text):
            seen[m.group(2).split("?")[0]] += 1
    print(f"=== 共 {len(seen)} 个不同 URL ===\n")
    groups = {"卡/试用": [], "支付": [], "会员权益": [], "其它": []}
    for u, n in sorted(seen.items()):
        lu = u.lower()
        if any(k in lu for k in ("card", "trial", "gift")):
            groups["卡/试用"].append((n, u))
        elif any(k in lu for k in ("pay", "order", "billing", "purchase", "wechat")):
            groups["支付"].append((n, u))
        elif any(k in lu for k in ("vip", "privilege", "member")):
            groups["会员权益"].append((n, u))
        elif "hellotalk" in lu:
            groups["其它"].append((n, u))
    for g, items in groups.items():
        print(f"--- {g} ({len(items)}) ---")
        for n, u in sorted(items, reverse=True):
            print(f"  x{n:<3} {u}")
        print()


if __name__ == "__main__":
    main()
