"""frida_attach_test.py — 修复 gadget 会话：分别测试 remote/USB 两条 attach 路径（带超时）"""
import threading
import time

import frida


def try_attach(label, get_device, target="Gadget", timeout=20):
    box = {}

    def run():
        try:
            dev = get_device()
            box["device"] = repr(dev)[:120]
            box["procs"] = [p.name for p in dev.enumerate_processes()]
            s = dev.attach(target)
            box["attached"] = True
            scr = s.create_script("send({ok:1, arch: Process.arch, mods: Process.enumerateModules().length});")
            scr.on("message", lambda m, d: box.setdefault("msgs", []).append(m))
            scr.load()
            time.sleep(1.0)
            s.detach()
            box["loaded"] = True
        except Exception as e:
            box["error"] = f"{type(e).__name__}: {e}"

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    print(f"--- {label} ---")
    print("  alive:", t.is_alive())
    for k, v in box.items():
        print(f"  {k}: {v}")
    print()


def main():
    try_attach("remote 127.0.0.1:27042", lambda: frida.get_device_manager().add_remote_device("127.0.0.1:27042"))
    try_attach("usb", lambda: frida.get_usb_device(timeout=10))


if __name__ == "__main__":
    main()
