"""fx_probe.py — frida 探测：Java 桥是否可用 + 列出网络/SSL 相关模块与类

前提：App 必须在前台（否则 Android 冻结进程，attach 会挂死）。
用法: python tools\\fx_probe.py
"""
import json
import pathlib
import sys
import threading
import time

import frida

HOST = "127.0.0.1:27042"
ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")

JS = r"""
(function () {
  var out = {
    arch: Process.arch,
    javaType: typeof Java,
    javaAvail: (typeof Java !== "undefined" && Java.available) ? true : false,
  };
  try {
    out.modules = Process.enumerateModules()
      .map(function (m) { return m.name; })
      .filter(function (n) { return /ssl|crypto|cronet|tprt|NetHT|flutter|app|curl|mbedtls|boringssl/i.test(n); });
  } catch (e) { out.modErr = String(e); }

  if (out.javaAvail) {
    Java.perform(function () {
      var names = [
        "com.android.org.conscrypt.TrustManagerImpl",
        "com.android.org.conscrypt.Platform",
        "org.chromium.net.X509Util",
        "org.chromium.net.impl.AndroidCertVerifyResult",
        "org.chromium.net.CronetEngine",
        "okhttp3.CertificatePinner",
        "javax.net.ssl.SSLContext",
      ];
      out.classes = {};
      names.forEach(function (n) {
        try { Java.use(n); out.classes[n] = "OK"; }
        catch (e) { out.classes[n] = "MISS: " + String(e).slice(0, 60); }
      });
      // 找 sscronet / 自家 cronet 的 java 包
      try {
        var hits = [];
        Java.enumerateLoadedClasses({
          onMatch: function (n) {
            if (/cronet|sscronet|X509Util|TrustManager|CertVerify/i.test(n) && hits.length < 60) hits.push(n);
          },
          onComplete: function () {},
        });
        out.loadedNetClasses = hits;
      } catch (e) { out.enumErr = String(e); }
    });
  }
  send({ tag: "probe", data: out });
})();
"""


def main():
    box = {}

    def run():
        d = frida.get_device_manager().add_remote_device(HOST)
        s = d.attach("Gadget")
        scr = s.create_script(JS)
        msg = []

        def on_msg(m, data):
            msg.append(m)

        scr.on("message", on_msg)
        scr.load()
        time.sleep(4)
        box["msgs"] = msg
        s.detach()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(60)
    if not box.get("msgs"):
        print("[FAIL] 没有拿到探测结果（App 可能不在前台？）")
        return 1
    for m in box["msgs"]:
        data = m.get("payload", {}).get("data") if isinstance(m, dict) else None
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=1)[:4000])
        else:
            print(m)
    (ROOT / "frida_probe.json").write_text(json.dumps(box["msgs"], ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
