"""card_probe3.py — 打印激励视频/权益位的完整清单"""
import json
import pathlib
import ssl
import sys
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
ROOT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")
BASE = "https://api-cn.hellotalk8.com/member_privilege_center/v3/"
UID = <UID>


def post(headers, path, body):
    data = json.dumps(body, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("content-type", "application/json; charset=UTF-8")
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def main():
    h = dict(json.loads((ROOT / "headers_write_off_card.json").read_text(encoding="utf-8"))["headers"])

    raw = post(h, "vip_experience_card/incentive_video_watch_quota", {"user_id": UID})
    print("=== 激励视频额度清单（完整）===")
    try:
        obj = json.loads(raw)
        for it in obj["data"]["items"]:
            print(f"  scene={it.get('scene_id')} feature={it.get('feature_id')} today_watched={it.get('today_watched')}")
    except Exception as e:
        print(raw[:800], e)

    print("\n=== 卡记录（完整）===")
    print(post(h, "vip_experience_card/query_user_record", {"user_id": UID})[:800])

    print("\n=== batch_query_receive_status ===")
    print(post(h, "vip_experience_card/batch_query_receive_status", {"user_id": UID})[:400])

    print("\n=== vip_trial/popup ===")
    print(post(h, "vip_trial/popup", {"user_id": UID})[:400])

    return 0


if __name__ == "__main__":
    sys.exit(main())
