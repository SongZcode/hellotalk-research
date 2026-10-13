"""card_probe2.py — 探测体验卡/试用模块的其余接口（重点：激励视频领权益）

用法: python tools\\card_probe2.py
"""
import json
import pathlib
import ssl
import sys
import time
import urllib.error
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
BASE = "https://api-cn.hellotalk8.com/member_privilege_center/v3/"
UID = <UID>


def load_headers():
    data = json.loads((ROOT / "headers_write_off_card.json").read_text(encoding="utf-8"))
    return dict(data["headers"])


def post(headers, path, body):
    data = json.dumps(body, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("content-type", "application/json; charset=UTF-8")
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")[:400]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def try_variants(h, path, variants, label):
    print(f"\n=== {label} ({path}) ===")
    for note, body in variants:
        code, text = post(h, path, body)
        print(f"  {note:<38} [{code}] {text[:200]}")
        time.sleep(0.4)


def main():
    h = load_headers()

    try_variants(h, "vip_experience_card/incentive_video_watch_quota",
                 [("只带 user_id", {"user_id": UID}),
                  ("带 scene_id", {"user_id": UID, "scene_id": "20000"}),
                  ("带 card_type", {"user_id": UID, "card_type": "1", "scene_id": "20000"})],
                 "A. 激励视频剩余次数")

    try_variants(h, "vip_experience_card/incentive_video_obtain_right",
                 [("只带 user_id", {"user_id": UID}),
                  ("带 feature_id=00001", {"user_id": UID, "feature_id": "00001"}),
                  ("带 scene_id+feature", {"user_id": UID, "feature_id": "00001",
                                           "scene_id": "20000", "card_type": "1"}),
                  ("带 advertising_id", {"user_id": UID, "feature_id": "00001",
                                         "scene_id": "20000", "advertising_id": "16ca34f0-6b86-4994-b9fd-588f67708af2"})],
                 "B. 激励视频领权益（看是否校验广告完成）")

    try_variants(h, "vip_experience_card/query_user_record",
                 [("只带 user_id", {"user_id": UID})],
                 "C. 我的卡记录")

    try_variants(h, "vip_trial/card_detail",
                 [("只带 user_id", {"user_id": UID})],
                 "D. 试用卡详情")

    try_variants(h, "vip_trial/unlock",
                 [("只带 user_id", {"user_id": UID})],
                 "E. 解锁试用（危险动作，只看服务端怎么答）")

    # 领完后复查权益
    code, text = post(h, "vip_experience_card/query_user_feature_right",
                      {"card_type": "1", "feature_id": "00001", "scene_id": "20000", "user_id": UID})
    print(f"\n=== F. 复查 feature 00001 权益 -> [{code}] {text}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
