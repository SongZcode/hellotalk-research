"""ht_ops.py — 从抓包统计「(消息类型, 第二字节)」映射，产出可信 opcode 表

结论（已实测）：opcode = [type, marker, counter_lo, counter_hi]
  marker 与 type 绑定：0x40=收件箱类、0x75=消息类、0x10=握手、0x20=轨迹/存在、0x10=发送类…
用法: python tools\ht_ops.py
"""
import collections
import json
import pathlib
import sys

from mitmproxy import io as mio

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")


def main():
    table = collections.defaultdict(lambda: {"UP": 0, "DN": 0, "sample": None, "body": None})
    for p in sorted(ROOT.glob("*.mitm")):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    for m in flow.websocket.messages:
                        raw = bytes(m.content)
                        if len(raw) < 8:
                            continue
                        key = (raw[4], raw[5])
                        body = HF.body_of(raw)
                        t = table[key]
                        t["UP" if m.from_client else "DN"] += 1
                        if t["sample"] is None:
                            t["sample"] = f"{p.name}:{raw[4:8].hex()}"
                            t["body"] = (body.decode("utf-8", "replace")[:110] if body else raw[20:40].hex())
        except Exception as e:
            print(f"[warn] {p.name}: {e}")

    print(f"{'type':<6}{'marker':<8}{'UP':>4}{'DN':>4}  样例")
    for (tp, mk), t in sorted(table.items()):
        print(f"0x{tp:02x}  0x{mk:02x}    {t['UP']:>4}{t['DN']:>4}  {t['sample']}  {t['body']}")


if __name__ == "__main__":
    main()
