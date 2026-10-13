import re, sys
xml = open(r"F:\hellotalk-mitm\artifacts\ui.xml", encoding="utf-8", errors="replace").read()
nodes = re.findall(r'<node[^>]*>', xml)
rows = []
for n in nodes:
    t = re.search(r'text="([^"]*)"', n)
    d = re.search(r'content-desc="([^"]*)"', n)
    b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
    if not b: continue
    x1,y1,x2,y2 = map(int, b.groups())
    label = (t.group(1) if t else "") or (d.group(1) if d else "")
    if label.strip():
        rows.append(((x1+x2)//2, (y1+y2)//2, label.strip()))
print("可点击/可见文本节点:", len(rows))
for x, y, label in rows[:40]:
    print(f"  ({x},{y})  {label}")