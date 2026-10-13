"""card_probe5.py — 用反射拿到的准确字段名探测「卡」相关接口

模型字段（frida 反射所得）：
  user_use_card(eh20)              : card_id, feature_id, scene_id, user_id, version
  receive_friend_sent_card(k930)   : record_id
  write_off_card(yb30)             : feature_id, incr_times, scene_id, user_id, advertising_id
  query_user_feature_right(hct)    : card_type, feature_id, scene_id, user_id
  watch_quota(khh)                 : user_id, scenes
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
ZERO_CARD = "000000000000000000000000"


def post(headers, path, body):
    data = json.dumps(body, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("content-type", "application/json; charset=UTF-8")
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")[:320]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:320]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def main():
    h = dict(json.loads((ROOT / "headers_write_off_card.json").read_text(encoding="utf-8"))["headers"])

    tests = [
        ("使用卡(user_use_card) 全字段",
         "vip_experience_card/user_use_card",
         {"card_id": ZERO_CARD, "feature_id": "00001", "scene_id": "20000", "user_id": UID, "version": 1}),
        ("使用卡 不带 version",
         "vip_experience_card/user_use_card",
         {"card_id": ZERO_CARD, "feature_id": "00001", "scene_id": "20000", "user_id": UID}),
        ("使用卡 随机 card_id",
         "vip_experience_card/user_use_card",
         {"card_id": "1234567890abcdef12345678", "feature_id": "00001", "scene_id": "20000",
          "user_id": UID, "version": 1}),
        ("收好友卡(receive_friend_sent_card) 占位 record_id",
         "vip_experience_card/receive_friend_sent_card",
         {"record_id": ZERO_CARD}),
        ("查卡记录 query_user_record",
         "vip_experience_card/query_user_record",
         {"user_id": UID}),
        ("额度(带 scenes) watch_quota",
         "vip_experience_card/incentive_video_watch_quota",
         {"user_id": UID, "scenes": ["20000", "30000"]}),
    ]

    for label, path, body in tests:
        code, text = post(h, path, body)
        print(f"\n--- {label}")
        print(f"    [{code}] {text}")
        time.sleep(0.4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
