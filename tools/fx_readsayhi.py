"""fx_readsayhi.py — 读 App 内存里的免费打招呼/额度模型

用法:
  python tools\\fx_readsayhi.py fields bzd
  python tools\\fx_readsayhi.py choose bzd freeSayHiTimes,clickedUserInfo
"""
import json
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\read_sayhi.bundle.js")


def main():
    cmd, cls = sys.argv[1], sys.argv[2]
    arg = sys.argv[3] if len(sys.argv) > 3 else ""
    code = BUNDLE.read_text(encoding="utf-8")
    box = {}

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        scr = s.create_script(code)
        scr.load()
        time.sleep(0.8)
        try:
            box["res"] = scr.exports_sync.fields(cls) if cmd == "fields" else scr.exports_sync.choose(cls, arg)
        except Exception as e:
            box["err"] = f"{type(e).__name__}: {e}"
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(50)
    res = box.get("res")
    if isinstance(res, list):
        for x in res:
            print(" ", json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else x)
    else:
        print(json.dumps(box, ensure_ascii=False)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
