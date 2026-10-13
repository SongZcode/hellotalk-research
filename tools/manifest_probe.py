from loguru import logger as lg
lg.remove()
import zipfile, re
z = zipfile.ZipFile(r"<WORKDIR2>\samples\xapk\com.hellotalk.apk")
data = z.read("AndroidManifest.xml")
# 直接找字符串池里的类名
text = data.decode("utf-16-le", "ignore")
cands = sorted(set(re.findall(r"(?:com|org|cn)\.[A-Za-z0-9_.]*Application[A-Za-z0-9_]*", text)))
print("application 候选:", cands[:10])
print("activity 候选:", sorted(set(re.findall(r"com\.hellotalk\.[A-Za-z0-9_.]*Activity", text)))[:8])