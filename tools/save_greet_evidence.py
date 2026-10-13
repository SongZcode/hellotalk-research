"""save_greet_evidence.py — 把「打招呼帧 + 服务端拒绝应答」从实时 ws.jsonl 里固化下来

产出 artifacts/mitm/greet_evidence.json（含两帧明文 JSON 与关键字段摘要）
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")
SRC = ROOT / "ws.jsonl"
OUT = ROOT / "greet_evidence.json"


def main():
    recs = []
    for line in SRC.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            recs.append(json.loads(line))
        except Exception:
            continue

    up = None
    dn = None
    for i, r in enumerate(recs):
        body = r.get("body") or ""
        if "new_sticker" in body:
            up = r
            for j in range(i + 1, min(i + 8, len(recs))):
                rb = recs[j].get("body") or ""
                if recs[j]["dir"] == "RECV" and ("code" in rb or "notice_type" in rb):
                    dn = recs[j]
                    break
            break

    if not up:
        print("[FAIL] ws.jsonl 里没有 new_sticker 帧")
        return 1

    ev = {
        "note": "第 11 次打招呼实测：客户端确实把 new_sticker 请求发到服务端，服务端按配额拒绝",
        "greet_up": {"opcode": up["hdr"].get("opcode"), "len": up["len"], "body": json.loads(up["body"])},
    }
    if dn:
        ev["greet_reply"] = {"opcode": dn["hdr"].get("opcode"), "len": dn["len"], "body": json.loads(dn["body"])}
    OUT.write_text(json.dumps(ev, ensure_ascii=False, indent=1), encoding="utf-8")

    print("=== 打招呼上行帧（客户端发出）===")
    print(json.dumps(ev["greet_up"], ensure_ascii=False, indent=1))
    if dn:
        print("\n=== 服务端应答（拒绝）===")
        print(json.dumps(ev["greet_reply"], ensure_ascii=False, indent=1))
    print(f"\n[OK] -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
