import io
import os
import re
import sys

# usage: python scan.py "root1;root2" "PATTERN1" ["PATTERN2" ...] [--ext .smali,.java] [--max 200]
roots = sys.argv[1].split(";")
rest = sys.argv[2:]
exts = (".smali", ".java", ".xml", ".json", ".txt", ".js", ".kt")
maxhits = 400
if "--ext" in rest:
    i = rest.index("--ext")
    exts = tuple(rest[i + 1].split(","))
    del rest[i:i + 2]
if "--max" in rest:
    i = rest.index("--max")
    maxhits = int(rest[i + 1])
    del rest[i:i + 2]
rx = [(p, re.compile(p)) for p in rest]

total = 0
files = 0
for root in roots:
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(exts):
                continue
            files += 1
            p = os.path.join(dirpath, fn)
            try:
                with io.open(p, "r", encoding="utf-8", errors="replace") as f:
                    for lineno, line in enumerate(f, 1):
                        for pat, r in rx:
                            if r.search(line):
                                print("%s:%d: %s" % (p, lineno, line.rstrip()[:240]))
                                total += 1
                                break
                        if total >= maxhits:
                            print("[scan] hit cap reached, files scanned=%d" % files)
                            sys.exit(0)
            except OSError:
                continue
print("[scan] done. files=%d hits=%d" % (files, total))
