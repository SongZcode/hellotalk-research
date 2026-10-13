"""find_uids.py — 从所有 dump 的明文帧里提取出现过的 uid（找可用的测试收件人）"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

ROOT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")
PATTERNS = [r'"from_uid":(\d+)', r'"to_uid":(\d+)', r'"uid":(\d+)', r'"user_id":(\d+)', r'"target_uid":(\d+)']


def main():
    from mitmproxy import io as mio

    counts: dict[str, int] = {}
    for p in sorted(ROOT.glob("*.mitm")):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    for m in flow.websocket.messages:
                        b = HF.body_of(bytes(m.content))
                        if not b:
                            continue
                        try:
                            txt = b.decode("utf-8")
                        except UnicodeDecodeError:
                            continue
                        for pat in PATTERNS:
                            for v in re.findall(pat, txt):
                                counts[v] = counts.get(v, 0) + 1
        except Exception as e:
            print(f"[warn] {p.name}: {e}")
    print("候选 uid（出现次数）：")
    for v, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {v}  x{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
