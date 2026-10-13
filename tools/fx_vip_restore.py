"""fx_vip_restore.py — 装载 vip_restore：把客户端 VIP 状态还原成非会员（找被藏起来的入口）

用法:
  python -u tools\\fx_vip_restore.py --seconds 240      # 还原非会员（默认）
  python -u tools\\fx_vip_restore.py --off --seconds 60 # 恢复补丁 VIP
"""
import argparse
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\vip_restore.bundle.js")
OUT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\vip_restore.log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=240)
    ap.add_argument("--off", action="store_true")
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
        scr.on("message", lambda m, data: w(f"  {str(m)[:300]}"))
        scr.load()
        time.sleep(1.5)
        try:
            for l in (scr.exports_sync.install() or []):
                w("  " + str(l))
            w(f"  模式开关 -> {scr.exports_sync.set(not a.off)}")
        except Exception as e:
            w(f"[install err] {type(e).__name__}: {e}")
        w(f"[vip_restore] 挂载 {a.seconds}s（{'非会员' if not a.off else '补丁VIP'}）")
        time.sleep(a.seconds)
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(a.seconds + 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
