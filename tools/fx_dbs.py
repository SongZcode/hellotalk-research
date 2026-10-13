"""fx_dbs.py — 列出 App 的数据文件（databases / files / shared_prefs）"""
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\dbs_spy.bundle.js")


def main():
    code = BUNDLE.read_text(encoding="utf-8")
    box = {}

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        scr = s.create_script(code)
        scr.load()
        time.sleep(0.8)
        try:
            box["res"] = scr.exports_sync.dbs()
        except Exception as e:
            box["err"] = f"{type(e).__name__}: {e}"
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(60)
    for x in box.get("res") or []:
        print(" ", x)
    if box.get("err"):
        print("ERR:", box["err"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
