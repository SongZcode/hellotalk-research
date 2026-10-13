"""fx_reflect.py — 反射读 Retrofit 接口定义（URL + 请求模型字段名）

用法:
  python tools\\fx_reflect.py iface f7s
  python tools\\fx_reflect.py fields yb30
  python tools\\fx_reflect.py ifaces f7s,xxx
"""
import json
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\reflect_api.bundle.js")


def main():
    cmd = sys.argv[1]
    arg = sys.argv[2]
    code = BUNDLE.read_text(encoding="utf-8")
    box = {}

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        scr = s.create_script(code)
        scr.load()
        time.sleep(0.6)
        try:
            if cmd == "iface":
                box["res"] = scr.exports_sync.iface(arg)
            elif cmd == "fields":
                box["res"] = scr.exports_sync.fields(arg)
            else:
                box["res"] = scr.exports_sync.ifaces(arg.split(","))
        except Exception as e:
            box["err"] = f"{type(e).__name__}: {e}"
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(45)
    print(json.dumps(box, ensure_ascii=False, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
