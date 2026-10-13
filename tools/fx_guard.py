"""fx_guard.py — 常驻守护：App 一启动就自动挂上证书绕过 agent（含崩溃/重启后自动重挂）

用法（后台）: python -u tools\\fx_guard.py
"""
import pathlib
import sys
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"<WORKDIR>\tools\agent\agent.bundle.js")
LOG = pathlib.Path(r"<WORKDIR>\artifacts\mitm\frida_guard.log")


def w(line: str):
    text = f"{time.strftime('%H:%M:%S')} {line}"
    print(text, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(text + "\n")


def attach_once(code: str) -> bool:
    try:
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
    except Exception as e:
        return False
    w(f"[guard] attached ({type(e).__name__ if False else 'ok'})")

    session_dead = {"v": False}

    def on_detached(reason, *a):
        session_dead["v"] = True
        w(f"[guard] session detached: {reason}")

    try:
        s.on("detached", on_detached)
    except Exception:
        pass

    scr = s.create_script(code)

    def on_msg(m, data):
        if isinstance(m, dict) and m.get("type") == "send":
            p = m.get("payload") or {}
            if p.get("tag") == "log":
                w("   " + str(p.get("msg"))[:240])

    scr.on("message", on_msg)
    scr.load()
    try:
        scr.exports_sync.install()
        w("[guard] hooks installed ✅")
    except Exception as e:
        w(f"[guard] install err: {type(e).__name__}: {e}")

    # 阻塞等待会话结束（靠 detached 事件判断，别主动调用 session API）
    for _ in range(3600):
        if session_dead["v"]:
            return True
        time.sleep(1)
    return True


def main():
    code = BUNDLE.read_text(encoding="utf-8")
    w("[guard] 启动，等待 gadget…")
    while True:
        ok = attach_once(code)
        if not ok:
            time.sleep(2)
        else:
            w("[guard] 重新等待 gadget…")
            time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
