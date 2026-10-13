"""extract_greet.py — 从抓包里抽出「打招呼(new_sticker)帧 + 服务端拒绝应答」，存成对照样本

产出:
  artifacts/mitm/greet_frame.bin    打招呼上行帧（原始字节）
  artifacts/mitm/greet_reply.bin    服务端应答帧（原始字节）
  artifacts/mitm/greet_decode.json  两帧的明文 JSON
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")


def main():
    from mitmproxy import io as mio

    up = None
    dn = None
    for p in sorted(ROOT.glob("*.mitm"), key=lambda x: x.stat().st_mtime):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    msgs = list(flow.websocket.messages)
                    for i, m in enumerate(msgs):
                        raw = bytes(m.content)
                        body = HF.body_of(raw)
                        if not body or b"new_sticker" not in body:
                            continue
                        up = raw
                        # 找紧随其后的响应帧
                        for j in range(i + 1, min(i + 6, len(msgs))):
                            cand = bytes(msgs[j].content)
                            if not msgs[j].from_client:
                                dn = cand
                                break
                        print(f"[hit] {p.name}: 打招呼帧 {len(raw)}B")
        except Exception as e:
            print(f"[warn] {p.name}: {e}")

    if not up:
        print("[FAIL] 没找到 new_sticker 帧")
        return 1

    out = {"up_hex": up.hex(), "dn_hex": dn.hex() if dn else None}
    for tag, raw in (("up", up), ("dn", dn)):
        if not raw:
            continue
        body = HF.body_of(raw)
        out[tag] = {
            "opcode": raw[4:8].hex(),
            "len": len(raw),
            "json": json.loads(body.decode("utf-8")) if body else None,
        }
        (ROOT / f"greet_{'frame' if tag == 'up' else 'reply'}.bin").write_bytes(raw)

    (ROOT / "greet_decode.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== 打招呼上行帧 ===")
    print(json.dumps(out.get("up", {}).get("json"), ensure_ascii=False, indent=1)[:2000])
    print("\n=== 服务端应答 ===")
    print(json.dumps(out.get("dn", {}).get("json"), ensure_ascii=False, indent=1)[:1200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
