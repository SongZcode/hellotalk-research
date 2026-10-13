"""ui_find.py — 在 UI dump 里按文本找节点，打印 bounds / clickable

用法: python tools\\ui_find.py 打招呼 [xml]
"""
import pathlib
import re
import sys

XML = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(r"F:\hellotalk-mitm\artifacts\u8.xml")
NEEDLE = sys.argv[1] if len(sys.argv) > 1 else "打招呼"


def attr(node, name):
    m = re.search(rf'{name}="([^"]*)"', node)
    return m.group(1) if m else ""


def main():
    t = XML.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"<node[^>]*>", t):
        s = m.group(0)
        txt = attr(s, "text")
        desc = attr(s, "content-desc")
        if NEEDLE in txt or NEEDLE in desc:
            print(f"  bounds={attr(s,'bounds'):<26} clickable={attr(s,'clickable'):<6} "
                  f"text={txt[:44]!r} desc={desc[:30]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
