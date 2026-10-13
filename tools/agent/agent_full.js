// agent_full.js — 证书绕过 + native 解密日志 + Java JSON 日志（三合一，用于抓激励视频流程）
import Java from 'frida-java-bridge';

const LOG = [];
function log(s) { LOG.push(s); send({ tag: 'log', msg: s }); }

const KW = /incentive|obtain|reward|ad_free|advert|watch|quota|feature_id|scene_id|card|vip|sayhi|say_hi|greet|free_say|new_chat|exposure/i;

function looksJson(ptr, len) {
  if (!ptr || !len || len <= 0) return false;
  try {
    const b = new Uint8Array(ptr.readByteArray(Math.min(len, 8)));
    for (let i = 0; i < b.length; i++) {
      const c = b[i];
      if (c === 32 || c === 9 || c === 10 || c === 13) continue;
      return c === 123 || c === 91 || c === 34;
    }
  } catch (e) {}
  return false;
}
function dump(ptr, len) {
  try {
    const n = Math.min(len, 1500);
    const b = new Uint8Array(ptr.readByteArray(n));
    let s = '';
    for (let i = 0; i < n; i++) s += String.fromCharCode(b[i]);
    return s + (len > n ? `...(+${len - n}B)` : '');
  } catch (e) { return '<err>'; }
}

// ---------- 1) Java 证书绕过 ----------
function hookJava() {
  return new Promise((resolve) => {
    if (!Java.available) { log('[java] 不可用'); return resolve(); }
    Java.perform(() => {
      try {
        const TMI = Java.use('com.android.org.conscrypt.TrustManagerImpl');
        TMI.verifyChain.implementation = function (chain) { return chain; };
        log('[java] hooked TrustManagerImpl.verifyChain');
      } catch (e) { log('[java] TMI 失败: ' + e); }
      try {
        const J = Java.use('org.json.JSONObject');
        J.$init.overload('java.lang.String').implementation = function (s) {
          try { if (s && s.length < 4000 && KW.test(s)) log('[json] ' + s); } catch (e) {}
          return this.$init(s);
        };
        log('[java] hooked JSONObject(String)');
      } catch (e) { log('[java] JSONObject 失败: ' + e); }
      try {
        const G = Java.use('com.google.gson.Gson');
        G.fromJson.overload('java.lang.String', 'java.lang.Class').implementation = function (s, c) {
          try { if (s && s.length < 4000 && KW.test(s)) log('[gson ' + c + '] ' + s); } catch (e) {}
          return this.fromJson(s, c);
        };
        log('[java] hooked Gson.fromJson');
      } catch (e) {}
      resolve();
    });
  });
}

// ---------- 0) native 证书绕过（App 的 HTTP 走 libsscronet，必须挂原生层） ----------
function hookX509() {
  const mods = Process.enumerateModules().filter((m) => /libcrypto|libssl|libpki|stable_cronet|sscronet/i.test(m.name));
  log('[x509] 目标模块: ' + mods.map((m) => m.name).join(', '));
  let n = 0;
  for (const m of mods) {
    for (const sym of ['X509_verify_cert', 'X509_STORE_CTX_get_error', 'SSL_get_verify_result']) {
      let addr = null;
      try { addr = Module.findExportByName(m.name, sym); } catch (e) {}
      if (!addr) continue;
      try {
        Interceptor.attach(addr, {
          onLeave(retval) { retval.replace(sym === 'X509_verify_cert' ? 1 : 0); },
        });
        n++;
      } catch (e) {}
    }
  }
  for (const sym of ['X509_verify_cert', 'SSL_get_verify_result']) {
    try {
      const a = Module.findGlobalExportByName(sym);
      if (a) {
        Interceptor.attach(a, { onLeave(r) { r.replace(sym === 'X509_verify_cert' ? 1 : 0); } });
        n++;
      }
    } catch (e) {}
  }
  log('[x509] 已挂 ' + n + ' 处原生校验');
}

// ---------- 2) native 解密日志 ----------
function hookNative() {
  hookX509();
  for (const m of Process.enumerateModules()) {
    if (!/crypto|ssl/i.test(m.name)) continue;
    let exps = [];
    try { exps = m.enumerateExports(); } catch (e) { continue; }
    for (const e of exps) {
      if (e.type !== 'function') continue;
      if (e.name === 'EVP_EncryptUpdate') {
        Interceptor.attach(e.address, {
          onEnter(args) {
            try {
              const n = args[4].toInt32();
              if (n > 0 && n < 65536 && looksJson(args[3], n)) {
                const s = dump(args[3], n);
                if (KW.test(s)) log('[enc] ' + s);
              }
            } catch (err) {}
          },
        });
      }
      if (e.name === 'EVP_DecryptUpdate') {
        Interceptor.attach(e.address, {
          onEnter(args) { this._o = args[1]; this._l = args[2]; },
          onLeave() {
            try {
              const n = this._l.readInt();
              if (n > 0 && looksJson(this._o, n)) {
                const s = dump(this._o, n);
                if (KW.test(s)) log('[dec] ' + s);
              }
            } catch (err) {}
          },
        });
      }
    }
  }
  log('[native] 解密日志已挂');
}

rpc.exports = {
  install() {
    hookNative();
    return hookJava().then(() => { log('[done]'); return LOG; });
  },
};
