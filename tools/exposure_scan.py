import zipfile, re, sys
from loguru import logger as lg
lg.remove()
sys.path.insert(0, r"F:\hok\tools\vendor")
from androguard.core.dex import DEX
z = zipfile.ZipFile(r"<WORKDIR2>\samples\xapk\com.hellotalk.apk")
targets = {"freeSayHiTimes", "freeNum", "freeSecond", "freeTitle", "exposureStatus"}
for name in [n for n in z.namelist() if re.match(r"classes\d*\.dex$", n)]:
    d = DEX(z.read(name))
    for c in d.get_classes():
        fields = [f.get_name() for f in c.get_fields()]
        hit = targets & set(fields)
        if hit:
            methods = [m.get_name() for m in c.get_methods()][:10]
            print(f"{name}  {c.get_name()}  fields={sorted(hit)}")
            print(f"     methods: {methods}")