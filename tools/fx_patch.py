"""fx_patch.py — 装载「明文就地改写」agent（金额篡改实验）

用法: python -u tools\\fx_patch.py [--seconds 150]
"""
import argparse
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"<WORKDIR>\tools\agent\price_patch.bundle.js")
OUT = pathlib.Path(r"<WORKDIR>\artifacts\mitm\price_patch.log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=150)
    a = ap.parse_args()
    code = BUNDLE.read_text(encoding="utf-8")
    lines = []

    def w(s):
        t = f"{time.strftime('%H:%M:%S')} {s}"
        print(t, flush=True)
        lines.append(t)
        OUT.write_text("\n".join(lines), encoding="utf-8")

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        scr = s.create_script(code)

        def on_msg(m, data):
            if isinstance(m, dict) and m.get("type") == "send":
                p = m.get("payload") or {}
                w(f"  <{p.get('tag')}> {p.get('msg')}")
            else:
                w(f"  [msg] {str(m)[:250]}")

        scr.on("message", on_msg)
        scr.load()
        time.sleep(1.5)
        try:
            for l in (scr.exports_sync.install() or []):
                w("  " + str(l))
        except Exception as e:
            w(f"[install err] {type(e).__name__}: {e}")
        w(f"[price_patch] 挂载 {a.seconds}s")
        time.sleep(a.seconds)
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(a.seconds + 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
