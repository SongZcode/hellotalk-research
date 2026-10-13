/* bypass_watch.js — 等 libsscronet/libtprt 加载后再 hook（cronet 专用） */
function log(m) { console.log("[bypass] " + m); }
log("pid=" + Process.id + " modules=" + Process.enumerateModules().length);

var seen = {};
function hookModule(name) {
  if (seen[name]) return; seen[name] = true;
  log("*** module appeared: " + name);

  // 1) cronet 用 custom verify 回调 —— 换成“永远 OK”
  var okCb = new NativeCallback(function () { return 0; }, 'int', ['pointer', 'pointer']);
  ["SSL_CTX_set_custom_verify"].forEach(function (sym) {
    try {
      var a = Module.getExportByName(name, sym);
      Interceptor.attach(a, { onEnter: function (args) { log(sym + " -> override callback"); args[2] = okCb; } });
      log("hooked " + name + "!" + sym);
    } catch (e) { log("miss " + sym + ": " + e); }
  });

  // 2) 常规证书校验函数
  [["X509_verify_cert", 'int', ['pointer'], function () { return 1; }],
   ["X509_STORE_CTX_get_error", 'int', ['pointer'], function () { return 0; }],
   ["SSL_get_verify_result", 'long', ['pointer'], function () { return 0; }],
   ["SSL_CTX_set_verify", 'int', ['pointer', 'int', 'pointer'], function () { log("set_verify bypass"); return 0; }]
  ].forEach(function (it) {
    try {
      var a = Module.getExportByName(name, it[0]);
      Interceptor.replace(a, new NativeCallback(it[3], it[1], it[2]));
      log("hooked " + name + "!" + it[0]);
    } catch (e) { log("miss " + it[0]); }
  });
}

// 每 400ms 扫一次，出现即 hook
setInterval(function () {
  ["libsscronet.so", "libcronet.so", "libtprt.so", "libflutter.so", "libapp.so"].forEach(function (n) {
    try { var m = Process.getModuleByName(n); hookModule(n); } catch (e) { }
  });
}, 400);

log("watcher started");
