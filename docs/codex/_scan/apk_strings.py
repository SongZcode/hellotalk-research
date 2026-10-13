import re
import sys
import zipfile

# usage: python apk_strings.py <apk> TERM [TERM...]
apk = sys.argv[1]
terms = [t.encode() for t in sys.argv[2:]]
z = zipfile.ZipFile(apk)
names = z.namelist()
targets = [n for n in names if n.endswith(".so") or n.endswith(".dex") or n.startswith("assets/")]
print("[apk_strings] entries=%d targets=%d" % (len(names), len(targets)))
for n in targets:
    try:
        d = z.read(n)
    except Exception as e:
        print("  !! %s %s" % (n, e))
        continue
    hits = []
    for t in terms:
        c = d.count(t)
        if c:
            hits.append("%s=%d" % (t.decode("utf-8", "ignore"), c))
    if hits:
        print("%s (%.1f MB): %s" % (n, len(d) / 1e6, ", ".join(hits)))

print("---- contexts ----")
for n in targets:
    if not n.endswith(".so"):
        continue
    d = z.read(n)
    for t in terms:
        for m in re.finditer(re.escape(t), d):
            s = max(0, m.start() - 48)
            e = min(len(d), m.end() + 48)
            ctx = re.sub(rb"[^\x20-\x7e]", b".", d[s:e]).decode("ascii", "ignore")
            print("%s | %s | %s" % (n, t.decode(), ctx))
