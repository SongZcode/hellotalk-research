import zipfile, re, collections
z = zipfile.ZipFile(r"F:\hellotalk-vip\samples\xapk\com.hellotalk.apk")
hosts = collections.Counter()
pat = re.compile(rb"[a-z0-9][a-z0-9.-]{2,60}\.(?:com|net|cn|org)(?::\d+)?")
for name in [n for n in z.namelist() if re.match(r"classes\d*\.dex$", n)]:
    d = z.read(name)
    for m in pat.finditer(d):
        h = m.group(0).decode("ascii", "ignore").lower()
        if any(k in h for k in ("hellotalk", "ht", "hellotalk8","talk")):
            hosts[h] += 1
for h, c in hosts.most_common(25):
    print(f"{c:6d}  {h}")