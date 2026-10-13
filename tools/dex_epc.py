"""dex_epc.py — 精确列出 vip_experience_card / vip_trial / vip_privilege 模块的所有接口路径"""
import pathlib
import re
import sys
import zipfile

APK = pathlib.Path(r"F:\hellotalk-vip\samples\xapk\com.hellotalk.apk")
PAT = re.compile(rb"/(?:member_privilege_center|virtual_pay|virtual_product|payment_gateway)[A-Za-z0-9_/\-{}.]*")


def main():
    hits = set()
    with zipfile.ZipFile(APK) as z:
        for n in z.namelist():
            if not n.endswith(".dex"):
                continue
            for m in PAT.finditer(z.read(n)):
                hits.add(m.group(0).decode("ascii", "replace"))
    print(f"命中 {len(hits)} 条\n")
    for s in sorted(hits):
        print("  ", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
