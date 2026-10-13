/* Native-only SSL pinning bypass（避开 Java bridge 版本问题） */
function log(m) { console.log("[bypass] " + m); }

['libsscronet.so','libcronet.so','libssl.so','libtprt.so','libflutter.so','libapp.so'].forEach(function (n) {
  try { var m = Process.getModuleByName(n); log('module ' + n + ' @ ' + m.base + ' size ' + m.size); } catch (e) { log('no module ' + n); }
});

var targets = ['SSL_CTX_set_verify', 'SSL_CTX_set_custom_verify', 'X509_verify_cert', 'SSL_get_verify_result', 'X509_STORE_CTX_get_error', 'SSL_CTX_set_verify_depth'];
targets.forEach(function (name) {
  var addr = null;
  try { addr = Module.findExportByName(null, name); } catch (e) { }
  if (!addr) { log('not found: ' + name); return; }
  try {
    if (name === 'SSL_CTX_set_verify') {
      Interceptor.replace(addr, new NativeCallback(function (ctx, mode, cb) { log('SSL_CTX_set_verify(mode=' + mode + ') -> 0'); return 0; }, 'int', ['pointer', 'int', 'pointer']));
    } else if (name === 'SSL_CTX_set_custom_verify') {
      Interceptor.replace(addr, new NativeCallback(function (ctx, mode, cb) { log('SSL_CTX_set_custom_verify -> 0'); return 0; }, 'int', ['pointer', 'int', 'pointer']));
    } else if (name === 'X509_verify_cert') {
      Interceptor.replace(addr, new NativeCallback(function (ctx) { return 1; }, 'int', ['pointer']));
    } else if (name === 'SSL_get_verify_result') {
      Interceptor.replace(addr, new NativeCallback(function (ssl) { return 0; }, 'long', ['pointer']));
    } else if (name === 'X509_STORE_CTX_get_error') {
      Interceptor.replace(addr, new NativeCallback(function (ctx) { return 0; }, 'int', ['pointer']));
    } else if (name === 'SSL_CTX_set_verify_depth') {
      Interceptor.replace(addr, new NativeCallback(function () { return 0; }, 'int', ['pointer', 'int']));
    }
    log('hooked ' + name + ' @ ' + addr);
  } catch (e) { log('hook fail ' + name + ': ' + e); }
});
log('native bypass loaded');