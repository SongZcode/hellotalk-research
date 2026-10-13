"""fx_keep.py — 常驻把证书绕过 agent 挂在 HelloTalk 上（前台运行，Ctrl-C/杀进程结束）

用法（后台跑）: python -u tools\\fx_keep.py
"""
import json
import pathlib
import sys
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\agent.bundle.js")
LOG = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\frida_keep.log")


def w(line: str):
    stamp = time.strftime("%H:%M:%S")
    text = f"{stamp} {line}"
    print(text, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(text + "\n")


def main():
    code = BUNDLE.read_text(encoding="utf-8")
    d = frida.get_device_manager().add_remote_device(HOST)
    s = d.attach("Gadget")
    w("[frida] attached")
    scr = s.create_script(code)

    def on_msg(m, data):
        if isinstance(m, dict) and m.get("type") == "send":
            p = m.get("payload") or {}
            if p.get("tag") == "log":
                w("  " + str(p.get("msg"))[:240])
        else:
            w("  [msg] " + str(m)[:240])

    scr.on("message", on_msg)
    scr.load()
    w("[frida] bundle loaded")
    try:
        scr.exports_sync.install()
        w("[frida] hooks installed")
    except Exception as e:
        w(f"[frida] install err {type(e).__name__}: {e}")
    w("[frida] 常驻中（App 必须保持前台）")
    while True:
        time.sleep(5)


if __name__ == "__main__":
    sys.exit(main())
