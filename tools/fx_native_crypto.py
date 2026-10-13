"""fx_native_crypto.py — 装载 native_crypto agent：扫描并挂钩原生 AES/EVP，打印明文

用法: python -u tools\\fx_native_crypto.py [--seconds 150] [--scan-only]
"""
import argparse
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"F:\hellotalk-mitm\tools\agent\native_crypto.bundle.js")
OUT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\native_crypto.log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=150)
    ap.add_argument("--scan-only", action="store_true")
    a = ap.parse_args()

    code = BUNDLE.read_text(encoding="utf-8")
    lines = []

    def w(s):
        text = f"{time.strftime('%H:%M:%S')} {s}"
        print(text, flush=True)
        lines.append(text)
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
                w(f"  [msg] {str(m)[:300]}")

        scr.on("message", on_msg)
        scr.load()
        time.sleep(1.5)
        try:
            info = scr.exports_sync.scan()
            w("[scan] 模块内 crypto 符号:")
            for mod, names in (info or {}).items():
                w(f"   {mod}: {names[:12]}")
        except Exception as e:
            w(f"[scan err] {e}")
        if not a.scan_only:
            try:
                res = scr.exports_sync.install()
                for line in (res or [])[:40]:
                    w("  " + str(line))
            except Exception as e:
                w(f"[install err] {type(e).__name__}: {e}")
            w(f"[native_crypto] 挂载 {a.seconds}s —— 去 App 里点 VIP 商品/翻页面")
            time.sleep(a.seconds)
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(a.seconds + 60)
    print(f"\n[i] -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
