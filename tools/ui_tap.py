"""ui_tap.py — 解析 uiautomator dump，列出可点元素；支持按文字/描述点击

用法:
  python tools\\ui_tap.py list
  python tools\\ui_tap.py tap --text 动态
  python tools\\ui_tap.py tap --xy 640,2600
"""
import argparse
import pathlib
import re
import subprocess
import sys

ADB = r"F:\located\toolchain\sdk\platform-tools\adb.exe"
SERIAL = "<PHONE_LAN_IP>:39083"
XML = pathlib.Path(r"<WORKDIR>\artifacts\ui_now.xml")

NODE = re.compile(r"<node[^>]*>")


def attr(node: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', node)
    return m.group(1) if m else ""


def dump() -> str:
    subprocess.run([ADB, "-s", SERIAL, "shell", "uiautomator dump /sdcard/ui_now.xml"],
                   capture_output=True, timeout=60)
    subprocess.run([ADB, "-s", SERIAL, "pull", "/sdcard/ui_now.xml", str(XML)],
                   capture_output=True, timeout=60)
    return XML.read_text(encoding="utf-8", errors="replace") if XML.exists() else ""


def tap_xy(x: int, y: int):
    subprocess.run([ADB, "-s", SERIAL, "shell", f"input tap {x} {y}"], capture_output=True, timeout=30)


def center(bounds: str):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "tap"])
    ap.add_argument("--text", default=None)
    ap.add_argument("--desc", default=None)
    ap.add_argument("--xy", default=None)
    a = ap.parse_args()

    if a.cmd == "tap" and a.xy:
        x, y = map(int, a.xy.split(","))
        tap_xy(x, y)
        print(f"tapped {x},{y}")
        return 0

    xml = dump()
    if not xml:
        print("[FAIL] 无法获取 UI dump")
        return 1

    nodes = []
    for m in NODE.finditer(xml):
        s = m.group(0)
        txt = attr(s, "text")
        desc = attr(s, "content-desc")
        b = attr(s, "bounds")
        if not b:
            continue
        nodes.append((txt, desc, b, attr(s, "clickable")))

    if a.cmd == "list":
        print(f"共 {len(nodes)} 个节点（列出有文字/描述的）")
        for txt, desc, b, clk in nodes:
            if txt or desc:
                c = center(b)
                flag = "可点" if clk == "true" else "  "
                print(f"  [{flag}] {txt[:24]!r:28} desc={desc[:20]!r:24} {b} 中心={c}")
        return 0

    # tap by text/desc
    for txt, desc, b, clk in nodes:
        if a.text and a.text in txt:
            c = center(b)
            if c:
                tap_xy(*c)
                print(f"tapped text={txt!r} at {c}")
                return 0
        if a.desc and a.desc in desc:
            c = center(b)
            if c:
                tap_xy(*c)
                print(f"tapped desc={desc!r} at {c}")
                return 0
    print("[FAIL] 没找到匹配节点")
    return 1


if __name__ == "__main__":
    sys.exit(main())
