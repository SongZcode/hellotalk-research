"""inspect_class.py — 打印某个 smali 类里与指定字符串相关的方法体，并列出调用者

用法: python tools\\inspect_class.py f7s incentive_video
"""
import pathlib
import re
import sys

SMALI = pathlib.Path(r"<WORKDIR2>\artifacts\apktool\smali")


def main():
    cls = sys.argv[1] if len(sys.argv) > 1 else "f7s"
    needle = sys.argv[2] if len(sys.argv) > 2 else "incentive_video"
    f = SMALI / f"{cls}.smali"
    if not f.exists():
        print("未找到", f)
        return 1
    t = f.read_text(encoding="utf-8", errors="replace")
    print(f"=== {f.name} ({len(t)}B) ===")

    # 找包含 needle 的方法
    methods = list(re.finditer(r"\.method[^\n]*\n", t))
    for i, m in enumerate(methods):
        start = m.start()
        end = methods[i + 1].start() if i + 1 < len(methods) else len(t)
        body = t[start:end]
        if needle not in body:
            continue
        sig = m.group(0).strip()
        print(f"\n--- 方法: {sig}")
        print(body[:2600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
