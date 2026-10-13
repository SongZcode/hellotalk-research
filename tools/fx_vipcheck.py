"""fx_vipcheck.py — 读当前 App 的 VIP 状态（判断补丁是否已移除）

用法: python -u tools\\fx_vipcheck.py
"""
import json
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\vipcheck.bundle.js")


def main():
    box = {}
    code = BUNDLE.read_text(encoding="utf-8")

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        scr = s.create_script(code)
        scr.load()
        time.sleep(0.8)
        try:
            box["res"] = scr.exports_sync.check()
        except Exception as e:
            box["err"] = f"{type(e).__name__}: {e}"
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(40)
    print(json.dumps(box, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
