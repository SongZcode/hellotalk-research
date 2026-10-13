"""fx_dbquery.py — 通过 frida 查询 App 的 SQLite（列表名 / 执行只读 SQL）

用法:
  python tools\\fx_dbquery.py tables <UID>_ht.db
  python tools\\fx_dbquery.py query <UID>_ht.db "SELECT name FROM sqlite_master WHERE type='table'"
"""
import json
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\db_query.bundle.js")


def call(cmd, a, b=None):
    code = BUNDLE.read_text(encoding="utf-8")
    box = {}

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        scr = s.create_script(code)
        scr.load()
        time.sleep(0.8)
        try:
            if cmd == "tables":
                box["res"] = scr.exports_sync.tables(a)
            else:
                box["res"] = scr.exports_sync.query(a, b)
        except Exception as e:
            box["err"] = f"{type(e).__name__}: {e}"
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(60)
    return box


def main():
    cmd = sys.argv[1]
    a = sys.argv[2]
    b = sys.argv[3] if len(sys.argv) > 3 else None
    box = call(cmd, a, b)
    for x in box.get("res") or []:
        print(" ", x)
    if box.get("err"):
        print("ERR:", box["err"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
