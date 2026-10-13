"""show_around.py — 打印打招呼帧前后若干帧（看目标路由线索）"""
import json
import pathlib
import sys

SRC = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\ws.jsonl")


def main():
    recs = [json.loads(l) for l in SRC.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    idx = [i for i, r in enumerate(recs) if "new_sticker" in (r.get("body") or "")]
    print(f"总帧数 {len(recs)}，打招呼帧下标 {idx}")
    if not idx:
        return 1
    i = idx[0]
    lo, hi = max(0, i - 8), min(len(recs), i + 4)
    for j in range(lo, hi):
        r = recs[j]
        b = r.get("body") or r.get("hex", "")
        mark = "  <<< GREET" if j == i else ""
        print(f"[{j}] {r['dir']} op={r['hdr'].get('opcode')} len={r['len']}{mark}")
        print(f"      {str(b)[:220]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
