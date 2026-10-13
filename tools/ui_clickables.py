"""ui_clickables.py — 列出 UI dump 里所有可点节点（含无文字的图标按钮）

用法: python tools\\ui_clickables.py [xml路径]
"""
import pathlib
import re
import sys

XML = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(r"F:\hellotalk-mitm\artifacts\g1.xml")


def attr(node, name):
    m = re.search(rf'{name}="([^"]*)"', node)
    return m.group(1) if m else ""


def main():
    t = XML.read_text(encoding="utf-8", errors="replace")
    n = 0
    for m in re.finditer(r"<node[^>]*>", t):
        s = m.group(0)
        if attr(s, "clickable") != "true":
            continue
        b = attr(s, "bounds")
        # 跳过底部导航和顶部筛选
        if "2512" in b or "[0,308]" in b or ",308]" in b and ",445]" in b:
            continue
        n += 1
        print(f"  {b:<26} {attr(s,'class'):<44} text={attr(s,'text')[:18]!r} desc={attr(s,'content-desc')[:18]!r}")
        if n > 24:
            break


if __name__ == "__main__":
    main()
