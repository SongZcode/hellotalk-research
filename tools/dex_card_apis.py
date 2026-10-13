"""dex_card_apis.py — 从 dex 里挖所有与卡/赠送相关的接口路径"""
import pathlib
import re
import sys
import zipfile

APK = pathlib.Path(r"<WORKDIR2>\samples\xapk\com.hellotalk.apk")
STR = re.compile(rb"[\x20-\x7e]{8,140}")
KEYS = (b"card", b"give_", b"send_card", b"friend", b"present")


def main():
    hits = set()
    with zipfile.ZipFile(APK) as z:
        for n in z.namelist():
            if not n.endswith(".dex"):
                continue
            data = z.read(n)
            for m in STR.finditer(data):
                s = m.group(0)
                if b"/" not in s:
                    continue
                sl = s.lower()
                if b"card" in sl or b"give" in sl and b"vip" in sl:
                    hits.add(s.decode("ascii", "replace"))
    print(f"命中 {len(hits)} 条：")
    for s in sorted(hits):
        if s.startswith("/") or "/v" in s or "privilege_center" in s:
            print("  ", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
