"""fx_pay.py — 装载 pay_probe agent（改金额 + 捞响应），支持切换 patch 开关

用法:
  python -u tools\\fx_pay.py --patch-off --seconds 60    # 基线（不改金额）
  python -u tools\\fx_pay.py --patch-on  --seconds 60    # 篡改金额
"""
import argparse
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\pay_probe.bundle.js")
OUT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\pay_probe.log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=90)
    ap.add_argument("--patch-on", action="store_true")
    ap.add_argument("--patch-off", action="store_true")
    a = ap.parse_args()
    want = True if a.patch_on else (False if a.patch_off else True)

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
                w(f"  <{p.get('tag')}> {str(p.get('msg'))[:700]}")
            else:
                w(f"  [msg] {str(m)[:250]}")

        scr.on("message", on_msg)
        scr.load()
        time.sleep(1.5)
        try:
            for l in (scr.exports_sync.install() or []):
                w("  " + str(l))
            w(f"  patch 开关 -> {scr.exports_sync.setPatch(want)}")
        except Exception as e:
            w(f"[install err] {type(e).__name__}: {e}")
        w(f"[pay_probe] 挂载 {a.seconds}s (patch={want})")
        time.sleep(a.seconds)
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(a.seconds + 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
