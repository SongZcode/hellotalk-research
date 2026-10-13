"""ui_texts.py — 打印 UI dump 里所有非空文本（完整，不截断）
用法: python tools\\ui_texts.py [xml路径]
"""
import pathlib
import re
import sys

XML = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(r"<WORKDIR>\artifacts\u3.xml")


def attr(node: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', node)
    return m.group(1) if m else ""


def main():
    t = XML.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"<node[^>]*>", t):
        s = m.group(0)
        txt = attr(s, "text")
        desc = attr(s, "content-desc")
        if len(txt) > 8 or len(desc) > 8:
            print(f"[{'可点' if attr(s,'clickable')=='true' else '  '}] {attr(s,'bounds')}")
            print(f"      text={txt}")
            if desc:
                print(f"      desc={desc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
