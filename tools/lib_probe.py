import zipfile, re
z = zipfile.ZipFile(r"F:\hellotalk-vip\samples\xapk\config.arm64_v8a.apk")
libs = [n for n in z.namelist() if n.startswith("lib/arm64-v8a/") and n.endswith(".so")]
terms = [b"session_key", b"ht_im/sock", b"session_id", b"encrypt", b"AES", b"IMSocket", b"im/sock", b"jwt"]
out = []
for n in libs:
    d = z.read(n)
    hits = {t.decode(): d.count(t) for t in terms if d.count(t)}
    if hits:
        out.append((n, hits, len(d)))
for n, hits, size in out:
    print(f"{n}  ({size//1024} KB)  {hits}")
print("---- total libs scanned:", len(libs))