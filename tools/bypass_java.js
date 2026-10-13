/* bypass_java.js — Java 层 pinning 绕过（针对 Android/Conscrypt + Cronet + OkHttp） */
function log(m) { console.log("[java-bypass] " + m); }

Java.perform(function () {
  log("java bridge ok");

  // 1) Conscrypt 平台校验器（cronet 在 Android 上走这条）
  try {
    var TMI = Java.use('com.android.org.conscrypt.TrustManagerImpl');
    TMI.verifyChain.implementation = function () {
      log("TrustManagerImpl.verifyChain bypassed");
      return Java.use('java.util.ArrayList').$new();
    };
    log("hooked TrustManagerImpl.verifyChain");
  } catch (e) { log("TrustManagerImpl: " + e); }

  // 2) Cronet 自己的 X509Util
  ['org.chromium.net.X509Util', 'org.chromium.net.impl.X509Util'].forEach(function (n) {
    try {
      var X = Java.use(n);
      X.verifyServerCertificates.implementation = function () { log(n + ".verifyServerCertificates bypassed"); return null; };
      log("hooked " + n);
    } catch (e) { log(n + " miss"); }
  });

  // 3) OkHttp CertificatePinner
  ['okhttp3.CertificatePinner', 'com.android.okhttp.CertificatePinner'].forEach(function (n) {
    try {
      var CP = Java.use(n);
      CP.check.overload('java.lang.String', 'java.util.List').implementation = function () { log(n + ".check bypassed"); };
      log("hooked " + n);
    } catch (e) { log(n + " miss"); }
  });

  // 4) 自定义 TrustManager / HostnameVerifier
  try {
    var X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');
    var SSLContext = Java.use('javax.net.ssl.SSLContext');
    var TrustAll = Java.registerClass({
      name: 'dev.hok.TrustAll2',
      implements: [X509TrustManager],
      methods: {
        checkClientTrusted: function () {},
        checkServerTrusted: function () {},
        getAcceptedIssuers: function () { return []; }
      }
    });
    var tm = [TrustAll.$new()];
    SSLContext.init.overload('[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom')
      .implementation = function (km, t, sr) { log("SSLContext.init -> TrustAll"); this.init(km, tm, sr); };
    log("hooked SSLContext.init");
  } catch (e) { log("SSLContext: " + e); }
  log("done");
});