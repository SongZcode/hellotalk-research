/*
 * hellotalk-mitm: SSL pinning bypass (Java + native / boringssl)
 * run: frida -H 127.0.0.1:27042 -l bypass.js Gadget
 */
function log(msg) { console.log("[bypass] " + msg); }

Java.perform(function () {
  try {
    var X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');
    var SSLContext = Java.use('javax.net.ssl.SSLContext');
    var TrustManager = Java.registerClass({
      name: 'dev.hok.TrustAll',
      implements: [X509TrustManager],
      methods: {
        checkClientTrusted: function () {},
        checkServerTrusted: function () {},
        getAcceptedIssuers: function () { return []; }
      }
    });
    var TrustManagers = [TrustManager.$new()];
    var SSLContext_init = SSLContext.init.overload(
      '[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom');
    SSLContext_init.implementation = function (km, tm, sr) {
      log('SSLContext.init hooked');
      SSLContext_init.call(this, km, TrustManagers, sr);
    };
  } catch (e) { log('java SSLContext hook err: ' + e); }

  ['okhttp3.CertificatePinner', 'com.android.okhttp.CertificatePinner'].forEach(function (name) {
    try {
      var CP = Java.use(name);
      CP.check.overload('java.lang.String', 'java.util.List').implementation = function () { log('pinner bypass ' + name); };
      CP.check.overload('java.lang.String', '[[Ljava.security.cert.X509Certificate;').implementation = function () { log('pinner bypass2 ' + name); };
    } catch (e) { }
  });

  try {
    var HostnameVerifier = Java.use('javax.net.ssl.HostnameVerifier');
    var OkHostnameVerifier = Java.use('okhttp3.internal.tls.OkHostnameVerifier');
    OkHostnameVerifier.verify.overload('java.lang.String', 'javax.net.ssl.SSLSession').implementation = function () { return true; };
    log('hostname verifier hooked');
  } catch (e) { }
});

/* ---- native / boringssl ---- */
(function () {
  var targets = ['SSL_CTX_set_verify', 'X509_verify_cert', 'SSL_get_verify_result', 'SSL_CTX_set_custom_verify', 'X509_STORE_CTX_get_error'];
  targets.forEach(function (name) {
    var addr = null;
    try { addr = Module.findExportByName(null, name); } catch (e) { }
    if (!addr) { log('native export not found: ' + name); return; }
    try {
      if (name === 'SSL_CTX_set_verify') {
        Interceptor.replace(addr, new NativeCallback(function (ctx, mode, cb) {
          log('SSL_CTX_set_verify -> mode 0');
          return 0;
        }, 'int', ['pointer', 'int', 'pointer']));
      } else if (name === 'X509_verify_cert') {
        Interceptor.replace(addr, new NativeCallback(function (ctx) { return 1; }, 'int', ['pointer']));
      } else if (name === 'SSL_get_verify_result') {
        Interceptor.replace(addr, new NativeCallback(function (ssl) { return 0; }, 'long', ['pointer']));
      } else if (name === 'X509_STORE_CTX_get_error') {
        Interceptor.replace(addr, new NativeCallback(function (ctx) { return 0; }, 'int', ['pointer']));
      }
      log('native hooked: ' + name + ' @ ' + addr);
    } catch (e) { log('hook fail ' + name + ': ' + e); }
  });

  // 打印模块列表方便确认 cronet/boringssl 位置
  ['libsscronet.so', 'libcronet.so', 'libssl.so', 'libtprt.so', 'libflutter.so'].forEach(function (n) {
    try { var m = Process.getModuleByName(n); log('module ' + n + ' @ ' + m.base + ' size ' + m.size); } catch (e) { log('no module ' + n); }
  });
})();
log('script loaded');