#!/usr/bin/env python3
"""inject_gadget.py — 往 apktool 工程里注入 frida-gadget（免 root 动态插桩）

步骤：
 1) 拷贝 libgadget.so + libgadget.config.so 到 <project>/lib/arm64-v8a/
 2) apktool.yml 的 doNotCompress 加入 so
 3) 在 Application.attachBaseContext 开头注入 System.loadLibrary("gadget")
用法：python inject_gadget.py --project <apktool 工程> --gadget <libgadget.so> --app-smali <NihaotalkApplication.smali>
"""
import argparse, json, os, pathlib, re, shutil, sys

GADGET_LIB = "libgadget.so"
GADGET_CFG = "libgadget.config.so"
INJECT = [
    '    const-string v0, "gadget"',
    '    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V',
]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--gadget", required=True)
    ap.add_argument("--app-smali", required=True)
    ap.add_argument("--port", type=int, default=27042)
    a = ap.parse_args()

    proj = pathlib.Path(a.project)
    libdir = proj / "lib" / "arm64-v8a"
    libdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.gadget, libdir / GADGET_LIB)
    cfg = {"interaction": {"type": "listen", "address": "0.0.0.0", "port": a.port, "on_load": "resume"}}
    (libdir / GADGET_CFG).write_text(json.dumps(cfg), encoding="utf-8")
    print(f"[1/3] gadget -> {libdir}")

    yml = proj / "apktool.yml"
    text = yml.read_text(encoding="utf-8")
    if "\n- so\n" not in text:
        text = text.rstrip() + "\n- so\n"
        yml.write_text(text, encoding="utf-8")
        print("[2/3] apktool.yml: 已加入 doNotCompress 'so'")
    else:
        print("[2/3] apktool.yml: 已包含 'so'")

    smali = pathlib.Path(a.app_smali)
    body = smali.read_text(encoding="utf-8")
    if "loadLibrary(Ljava/lang/String;)V" in body and '"gadget"' in body:
        print("[3/3] 已注入过，跳过")
        return 0
    m = re.search(r"(\.method public final attachBaseContext\(Landroid/content/Context;\)V\n)", body)
    if not m:
        print("!! 未找到 attachBaseContext，改用 <clinit>")
        m = re.search(r"(\.method static constructor <clinit>\(\)V\n)", body)
        if not m:
            print("!! 注入点缺失"); return 2
    inject = m.group(1) + "    # frida-gadget injection\n" + "\n".join(INJECT) + "\n\n"
    body = body[:m.start()] + inject + body[m.end():]
    smali.write_text(body, encoding="utf-8")
    print("[3/3] 已注入 loadLibrary(\"gadget\")")
    return 0

if __name__ == "__main__":
    sys.exit(main())