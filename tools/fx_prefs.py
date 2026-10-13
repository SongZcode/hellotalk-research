"""fx_prefs.py — 通过 frida 查看/清除 App 的 SharedPreferences

用法:
  python tools\\fx_prefs.py list
  python tools\\fx_prefs.py search            # 默认关键词
  python tools\\fx_prefs.py search <正则>
  python tools\\fx_prefs.py clear <键名>
"""
import json
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\prefs_spy.bundle.js")


def main():
    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    code = BUNDLE.read_text(encoding="utf-8")
    box = {}

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        scr = s.create_script(code)
        scr.load()
        time.sleep(0.8)
        try:
            if cmd == "list":
                box["res"] = scr.exports_sync.list()
            elif cmd == "search":
                box["res"] = scr.exports_sync.search(arg)
            else:
                box["res"] = scr.exports_sync.clear(arg)
        except Exception as e:
            box["err"] = f"{type(e).__name__}: {e}"
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(60)
    res = box.get("res")
    if isinstance(res, list):
        for item in res:
            if isinstance(item, dict):
                print(f"  [{item.get('file','')}] {item.get('key','')} = {item.get('value','')}")
            else:
                print(f"  {item}")
    else:
        print(json.dumps(box, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
