import zipfile, re
z = zipfile.ZipFile(r"<WORKDIR2>\samples\xapk\com.hellotalk.apk")
terms = ["say_hi", "sayHi", "SayHi", "greet", "Greet", "limit", "Limit", "remain", "Remain", "quota", "Quota", "exceeded", "upper_limit", "upperLimit"]
for name in [n for n in z.namelist() if re.match(r"classes\d*\.dex$", n)]:
    d = z.read(name)
    hits = {}
    for t in terms:
        c = d.count(t.encode())
        if c: hits[t] = c
    if hits:
        print(name, hits)
print("---- say_hi 相关字符串上下文（classes6） ----")
d = z.read("classes6.dex")
for m in re.finditer(rb"say[_A-Za-z]*(hi|Hi)[_A-Za-z]*", d):
    s = max(0, m.start()-60); e = min(len(d), m.end()+60)
    ctx = re.sub(rb"\s+", b" ", d[s:e]).decode("utf-8", "ignore")
    print("  ", ctx[:130])