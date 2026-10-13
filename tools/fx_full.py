"""fx_full.py — 装载三合一 agent（证书绕过 + 解密日志），常驻并打印命中内容

用法: python -u tools\\fx_full.py [--seconds 600]
"""
import argparse
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"<WORKDIR>\tools\agent\agent_full.bundle.js")
OUT = pathlib.Path(r"<WORKDIR>\artifacts\mitm\full_agent.log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=600)
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
                w(f"  <{p.get('tag')}> {str(p.get('msg'))[:1200]}")
            else:
                w(f"  [msg] {str(m)[:250]}")

        scr.on("message", on_msg)
        scr.load()
        time.sleep(1.2)
        try:
            for l in (scr.exports_sync.install() or []):
                w("  " + str(l))
        except Exception as e:
            w(f"[install err] {type(e).__name__}: {e}")
        w(f"[full] 挂载 {a.seconds}s —— 现在去点「免广告体验」")
        time.sleep(a.seconds)
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(a.seconds + 90)
    return 0


if __name__ == "__main__":
    sys.exit(main())
