"""fx_run.py — 把 agent 装载到 HelloTalk（attach gadget → load bundle → install hooks）

前提：App 前台、屏幕常亮（后台会被冻结）。
用法: python tools\\fx_run.py
"""
import json
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
BUNDLE = pathlib.Path(r"<WORKDIR>\tools\agent\agent.bundle.js")
OUT = pathlib.Path(r"<WORKDIR>\artifacts\mitm\frida_agent.jsonl")


def main():
    code = BUNDLE.read_text(encoding="utf-8")
    box = {}
    logs = []

    def on_msg(m, data):
        logs.append(m)
        if isinstance(m, dict) and m.get("type") == "send":
            p = m.get("payload") or {}
            if p.get("tag") == "log":
                print("  " + str(p.get("msg"))[:220], flush=True)
        else:
            print("  [msg] " + str(m)[:220], flush=True)

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        box["attached"] = True
        scr = s.create_script(code)
        scr.on("message", on_msg)
        scr.load()
        box["loaded"] = True
        time.sleep(1.5)
        try:
            box["status"] = scr.exports_sync.install()
        except Exception as e:
            box["install_err"] = f"{type(e).__name__}: {e}"
        time.sleep(3)
        box["level"] = "?", "detach-soon"  # 保持挂载：不 detach，交给 mitmproxy 抓流量
        # 保持会话：这里不 detach，等 60 秒让 App 产生流量
        time.sleep(60)
        box["done"] = True

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(90)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(x, ensure_ascii=False, default=str) for x in logs), encoding="utf-8")
    print("\n[结果]", json.dumps({k: v for k, v in box.items() if k != "status"}, ensure_ascii=False, default=str)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
