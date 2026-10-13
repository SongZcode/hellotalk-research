"""fx_crypto.py — 装载 crypto_spy agent（打印 Java 层加解密的密钥与明文），并保持挂载

用法: python -u tools\\fx_crypto.py [--seconds 120]
"""
import argparse
import json
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"<WORKDIR>\tools\agent\crypto_spy.bundle.js")
OUT = pathlib.Path(r"<WORKDIR>\artifacts\mitm\crypto_spy.log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=120)
    a = ap.parse_args()

    code = BUNDLE.read_text(encoding="utf-8")
    lines = []

    def w(s):
        text = f"{time.strftime('%H:%M:%S')} {s}"
        print(text, flush=True)
        lines.append(text)
        OUT.write_text("\n".join(lines), encoding="utf-8")

    box = {}

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        box["attached"] = True
        scr = s.create_script(code)

        def on_msg(m, data):
            if isinstance(m, dict) and m.get("type") == "send":
                p = m.get("payload") or {}
                w(f"  <{p.get('tag')}> {str(p.get('msg'))[:400]}")
            else:
                w(f"  [msg] {str(m)[:300]}")

        scr.on("message", on_msg)
        scr.load()
        time.sleep(1.5)
        try:
            res = scr.exports_sync.install()
            for line in (res or []):
                w("  " + str(line)[:400])
        except Exception as e:
            w(f"[install err] {type(e).__name__}: {e}")
        w(f"[crypto_spy] 挂载中 {a.seconds}s —— 现在去 App 里操作（点 VIP 商品 / 进页面）")
        time.sleep(a.seconds)
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(a.seconds + 40)
    print(f"\n[i] 日志 -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
