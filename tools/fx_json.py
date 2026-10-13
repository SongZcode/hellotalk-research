"""fx_json.py — 装载 json_spy agent：捞解密后的响应 JSON"""
import pathlib, sys, threading, time
import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"<WORKDIR>\tools\agent\json_spy.bundle.js")
OUT = pathlib.Path(r"<WORKDIR>\artifacts\mitm\json_spy.log")

def main():
    code = BUNDLE.read_text(encoding="utf-8")
    lines = []
    def w(s):
        t = f"{time.strftime('%H:%M:%S')} {s}"
        print(t, flush=True); lines.append(t); OUT.write_text("\n".join(lines), encoding="utf-8")
    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        scr = s.create_script(code)
        def on_msg(m, data):
            if isinstance(m, dict) and m.get("type") == "send":
                p = m.get("payload") or {}
                w(f"  <{p.get('tag')}> {str(p.get('msg'))[:900]}")
            else:
                w(f"  [msg] {str(m)[:250]}")
        scr.on("message", on_msg)
        scr.load(); time.sleep(1.5)
        try:
            for l in (scr.exports_sync.install() or []): w("  " + str(l))
        except Exception as e:
            w(f"[install err] {type(e).__name__}: {e}")
        w("[json_spy] 挂载 180s")
        time.sleep(180); s.detach()
    t = threading.Thread(target=run, daemon=True); t.start(); t.join(240)
    return 0

sys.exit(main())
