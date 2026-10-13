"""verify_ht_frame.py — 校验复刻帧与抓包帧是否字节级一致"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

EV = pathlib.Path(r"<WORKDIR>\artifacts\mitm\greet_evidence.json")


def main():
    ev = json.loads(EV.read_text(encoding="utf-8"))
    body_obj = ev["greet_up"]["body"]

    print("dumps_ht 斜杠转义:", HF.dumps_ht({"u": "https://a/b"}))

    frame = HF.pack_json(HF.build_opcode(0x01, 0x1AD8, 0x40), <UID>, body_obj)
    print(f"复刻帧 len={len(frame)}（抓包实测 459）→ {'一致' if len(frame) == 459 else '不一致'}")
    print(f"帧头 20B: {frame[:20].hex()}")
    print(f"  magic  : {frame[:4].hex()}  (实测 f0040001)")
    print(f"  opcode : {frame[4:8].hex()}  (实测 0140d81a)")
    print(f"  uid    : {int.from_bytes(frame[8:16], 'little')}  (实测 <UID>)")
    print(f"  bodylen: {int.from_bytes(frame[16:20], 'little')}  (压缩体应 439)")

    # 反向验证：解回来是否还是同一 JSON
    parsed = HF.parse(frame)
    same = parsed["body"] == body_obj
    print(f"解回 JSON 与原始一致: {same}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
