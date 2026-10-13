// pay_probe.js — 合并版：① native 层改金额 ② Java 层捞解密的响应 JSON
import Java from 'frida-java-bridge';

const FROM = '"amount":888000';
const TO = '"amount":000001'; // 同长度
const KW = /order_id|pay_amount|error_code|prepay|trade|wechat|failure_reason/i;

function findSeq(buf, len, needle) {
  const n = needle.length;
  if (len < n) return -1;
  const bytes = new Uint8Array(buf.readByteArray(len));
  const head = needle.charCodeAt(0);
  for (let i = 0; i <= len - n; i++) {
    if (bytes[i] !== head) continue;
    let ok = true;
    for (let j = 1; j < n; j++) if (bytes[i + j] !== needle.charCodeAt(j)) { ok = false; break; }
    if (ok) return i;
  }
  return -1;
}

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
    const n = Math.min(len, 1000);
    const b = new Uint8Array(ptr.readByteArray(n));
    let s = '';
    for (let i = 0; i < n; i++) s += String.fromCharCode(b[i]);
    return s + (len > n ? `...(+${len - n}B)` : '');
  } catch (e) { return '<err>'; }
}

let patchOn = true;

rpc.exports = {
  setPatch(v) { patchOn = !!v; return patchOn; },
  install() {
    const lines = [];
    let n = 0;
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
                const inl = args[4].toInt32();
                if (inl <= 0 || inl > 65536) return;
                const off = findSeq(args[3], inl, FROM);
                if (off < 0) return;
                if (!patchOn) { send({ tag: 'patch', msg: `[patch OFF] 看到 amount=888000 但未改写 (${inl}B)` }); return; }
                args[3].add(off).writeByteArray(Array.from(TO).map((c) => c.charCodeAt(0)), 0, TO.length);
                send({ tag: 'patch', msg: `[patch ON] ${FROM} -> ${TO} (${inl}B)` });
              } catch (err) { send({ tag: 'patch', msg: '[err] ' + err }); }
            },
          });
          n++; lines.push('hooked EVP_EncryptUpdate ' + m.name);
        }
        if (e.name === 'EVP_DecryptUpdate') {
          Interceptor.attach(e.address, {
            onEnter(args) { this._o = args[1]; this._l = args[2]; },
            onLeave() {
              try {
                const n2 = this._l.readInt();
                if (n2 > 0 && looksJson(this._o, n2)) {
                  const s = dump(this._o, n2);
                  if (KW.test(s)) send({ tag: 'dec', msg: s });
                }
              } catch (err) {}
            },
          });
          n++; lines.push('hooked EVP_DecryptUpdate ' + m.name);
        }
      }
    }

    Java.perform(() => {
      try {
        const J = Java.use('org.json.JSONObject');
        J.$init.overload('java.lang.String').implementation = function (s) {
          try {
            if (s && s.length < 4000 && KW.test(s)) send({ tag: 'java-json', msg: s });
          } catch (e) {}
          return this.$init(s);
        };
        lines.push('hooked org.json.JSONObject(String)');
        n++;
      } catch (e) { lines.push('JSONObject hook 失败: ' + e); }
      try {
        const G = Java.use('com.google.gson.Gson');
        G.fromJson.overload('java.lang.String', 'java.lang.Class').implementation = function (s, c) {
          try {
            if (s && s.length < 4000 && KW.test(s)) send({ tag: 'java-gson-' + c, msg: s });
          } catch (e) {}
          return this.fromJson(s, c);
        };
        lines.push('hooked Gson.fromJson');
        n++;
      } catch (e) {}
    });

    lines.unshift(`共挂 ${n} 处`);
    return lines;
  },
};
