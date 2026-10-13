import zipfile, re
z = zipfile.ZipFile(r"<WORKDIR2>\samples\xapk\com.hellotalk.apk")
d = z.read("classes6.dex")
for t in [b"freeSayHiTimes", b"ExposureStatusLiveData", b"free_sayhi_times", b"freeNum"]:
    for m in re.finditer(re.escape(t), d):
        s = max(0, m.start()-400); e = min(len(d), m.end()+200)
        seg = d[s:e].decode("utf-8", "ignore")
        names = re.findall(r"L[a-z0-9/]{6,80};", seg)
        print(f"--- {t.decode()} @ {m.start()}")
        print("   classes nearby:", sorted(set(names))[:6])
        print("   ctx:", re.sub(r"\s+", " ", seg)[-260:])
        break