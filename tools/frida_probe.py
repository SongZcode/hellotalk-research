"""frida_probe.py — 连接到 gadget 并做基础能力探测（带超时，防挂死）"""
import json
import threading
import time

import frida

HOST = "127.0.0.1:27042"

JS = """
rpc.exports.ping = function () { return "pong"; };
rpc.exports.mods = function () {
  return Process.enumerateModules().map(function (m) { return m.name + ":" + m.base.toString() + ":" + m.size; });
};
send({ tag: "boot", arch: Process.arch, platform: Process.platform, pid: Process.id,
       javaAvail: (typeof Java !== "undefined") });
"""


def main():
    result = {"stage": "start"}

    def run():
        try:
            d = frida.get_device_manager().add_remote_device(HOST)
            result["stage"] = "device"
            s = d.attach("Gadget")
            result["stage"] = "attached"
            scr = s.create_script(JS)

            def on_msg(m, data):
                print("MSG:", json.dumps(m)[:600], flush=True)

            scr.on("message", on_msg)
            scr.load()
            result["stage"] = "loaded"
            time.sleep(1.0)
            result["ping"] = scr.exports_sync.ping()
            mods = scr.exports_sync.mods()
            result["mods"] = mods
            result["stage"] = "rpc-ok"
            s.detach()
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            result["stage"] = result["stage"] + "->FAIL"

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(40)
    print("ALIVE:", t.is_alive(), flush=True)
    print("stage:", result.get("stage"), flush=True)
    if "error" in result:
        print("error:", result["error"], flush=True)
    if "ping" in result:
        print("ping:", result["ping"], flush=True)
    mods = result.get("mods") or []
    print(f"modules: {len(mods)}", flush=True)
    for m in mods:
        print("   ", m, flush=True)


if __name__ == "__main__":
    main()
