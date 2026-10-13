// agent.js — HelloTalk 证书校验绕过 + 可选 VIP 状态还原（frida 17 + frida-java-bridge）
// 覆盖: Conscrypt TrustManagerImpl / cronet X509Util / OkHttp CertificatePinner / 原生 BoringSSL X509
import Java from 'frida-java-bridge';

const LOG = [];
function log(s) { LOG.push(s); send({ tag: 'log', msg: s }); }

// 服务端 vip_info 实测值（用于「还原非会员」模式）
const REAL_VIP_EXPIRE = 1790022926;
const REAL_VIP_TYPE = 0;

// 默认 false = 保持客户端「自称 VIP」（赠送/促销入口可见，但会触发篡改上报）
// 设为 true = 还原成服务端真实值（非会员入口可见）
let vipRestore = false;

// ---------- 1) Java 层证书绕过 ----------
function hookJava() {
  return new Promise((resolve) => {
    if (!Java.available) { log('[java] 不可用'); return resolve(); }
    Java.perform(() => {
      try {
        const TMI = Java.use('com.android.org.conscrypt.TrustManagerImpl');
        TMI.verifyChain.implementation = function (untrustedChain) {
          log('[java] TrustManagerImpl.verifyChain 放行 (' + untrustedChain.length + ' 张证书)');
          return untrustedChain;
        };
        log('[java] hooked TrustManagerImpl.verifyChain');
        try {
          TMI.checkTrustedRecursive.implementation = function () {
            return Java.use('java.util.ArrayList').$new();
          };
          log('[java] hooked TrustManagerImpl.checkTrustedRecursive');
        } catch (e) { log('[java] checkTrustedRecursive 跳过: ' + e); }
      } catch (e) { log('[java] TrustManagerImpl 失败: ' + e); }

      for (const cn of ['org.chromium.net.X509Util', 'org.chromium.net.impl.X509Util']) {
        try {
          const X = Java.use(cn);
          log('[java] 找到 ' + cn);
          if (X.verifyServerCertificates) {
            X.verifyServerCertificates.implementation = function () {
              log('[java] ' + cn + '.verifyServerCertificates 放行');
              return null;
            };
          }
        } catch (e) { log('[java] ' + cn + ' 不可用: ' + String(e).slice(0, 60)); }
      }

      try {
        const CP = Java.use('okhttp3.CertificatePinner');
        CP.check.overload('java.lang.String', 'java.util.List').implementation = function () {
          log('[java] CertificatePinner.check 放行');
        };
        log('[java] hooked CertificatePinner.check');
      } catch (e) { log('[java] CertificatePinner 跳过: ' + String(e).slice(0, 60)); }

      try {
        const hits = [];
        Java.enumerateLoadedClasses({
          onMatch(n) {
            if (/cronet|sscronet|X509Util|TrustManager|CertVerify|CertPath/i.test(n) && hits.length < 50) hits.push(n);
          },
          onComplete() {},
        });
        log('[java] 相关已加载类: ' + JSON.stringify(hits));
      } catch (e) { log('[java] 枚举失败: ' + e); }
      resolve();
    });
  });
}

// ---------- 2) VIP 状态还原开关 ----------
function hookVipRestore() {
  try {
    const C = Java.use('ia30');
    const origI = C.i.overload();
    const origN = C.n.overload();
    const origR = C.r.overload();
    C.i.implementation = function () { return vipRestore ? REAL_VIP_EXPIRE : origI.call(this); };
    C.n.implementation = function () { return vipRestore ? REAL_VIP_TYPE : origN.call(this); };
    C.r.implementation = function () { return vipRestore ? false : origR.call(this); };
    log('[vip] ia30.i/n/r 已挂钩（当前: ' + (vipRestore ? '还原非会员' : '保持客户端自称VIP') + '）');
  } catch (e) { log('[vip] ia30 挂钩失败: ' + e); }
}

// ---------- 3) 原生层（BoringSSL） ----------
function hookNative() {
  const mods = Process.enumerateModules().filter((m) => /libcrypto|libssl|libpki|stable_cronet/i.test(m.name));
  log('[native] 目标模块: ' + mods.map((m) => m.name + '@' + m.base).join(', '));
  for (const m of mods) {
    for (const sym of ['X509_verify_cert', 'X509_STORE_CTX_get_error', 'SSL_get_verify_result']) {
      let addr = null;
      try { addr = Module.findExportByName(m.name, sym); } catch (e) {}
      if (!addr) continue;
      try {
        Interceptor.attach(addr, {
          onLeave(retval) {
            if (sym === 'X509_verify_cert') { retval.replace(1); } else { retval.replace(0); }
          },
        });
        log('[native] hooked ' + sym + ' in ' + m.name);
      } catch (e) { log('[native] hook 失败 ' + sym + ' in ' + m.name + ': ' + e); }
    }
  }
  for (const sym of ['X509_verify_cert', 'SSL_get_verify_result']) {
    try {
      const a = Module.findGlobalExportByName(sym);
      if (a) {
        Interceptor.attach(a, { onLeave(r) { r.replace(sym === 'X509_verify_cert' ? 1 : 0); } });
        log('[native] global hooked ' + sym);
      }
    } catch (e) {}
  }
}

rpc.exports = {
  status() { return LOG; },
  setVipRestore(v) {
    vipRestore = !!v;
    log('[vip] 切换 -> ' + (vipRestore ? '还原非会员' : '保持客户端自称VIP'));
    return vipRestore;
  },
  install() {
    hookNative();
    return hookJava().then(() => {
      hookVipRestore();
      log('[done] agent 装载完成');
      return LOG;
    });
  },
};
