"""dex_strings.py — 直接从 APK 的 dex 里抽字符串（比扫 smali 快几十倍），找接口路径

用法: python tools\\dex_strings.py [关键词...]
"""
import pathlib
import re
import sys
import zipfile

APK = pathlib.Path(r"<WORKDIR2>\samples\xapk\com.hellotalk.apk")
STR_RE = re.compile(rb"[\x20-\x7e]{6,120}")
DEFAULT_KEYS = ("member_privilege_center", "vip_experience_card", "vip_trial")


def iter_dex(apk: pathlib.Path):
    with zipfile.ZipFile(apk) as z:
        for n in z.namelist():
            if n.endswith(".dex"):
                yield n, z.read(n)


def main():
    keys = [k.encode() for k in (sys.argv[1:] or DEFAULT_KEYS)]
    hits = set()
    total = 0
    for name, data in iter_dex(APK):
        total += 1
        for m in STR_RE.finditer(data):
            s = m.group(0)
            if any(k in s for k in keys):
                hits.add(s.decode("ascii", "replace"))
    print(f"[i] 扫了 {total} 个 dex，命中 {len(hits)} 条\n")
    for s in sorted(hits):
        # 只显示像路径/字段的
        if s.startswith("/") or "_" in s or len(s) < 80:
            print(f"  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
