// crypto_spy.js — 监听 Java 层加解密，把 ht/encbin 类接口的明文捞出来
import Java from 'frida-java-bridge';

const MAX = 800;
function hex(b) {
  if (!b) return '';
  const arr = Java.array('byte', b);
  let s = '';
  for (let i = 0; i < Math.min(arr.length, MAX); i++) {
    s += ('0' + (arr[i] & 0xff).toString(16)).slice(-2);
  }
  return s + (arr.length > MAX ? `...(+${arr.length - MAX}B)` : '') + ` (${arr.length}B)`;
}
function ascii(b) {
  try {
    const arr = Java.array('byte', b);
    let s = '';
    for (let i = 0; i < Math.min(arr.length, 200); i++) {
      const c = arr[i] & 0xff;
      s += (c >= 32 && c < 127) ? String.fromCharCode(c) : '.';
    }
    return s;
  } catch (e) { return ''; }
}

rpc.exports = {
  install() {
    const out = [];
    Java.perform(() => {
      try {
        const Cipher = Java.use('javax.crypto.Cipher');
        const instances = {};

        Cipher.getInstance.overload('java.lang.String').implementation = function (t) {
          out.push('[cipher] getInstance(' + t + ')');
          return this.getInstance(t);
        };
        Cipher.init.overload('int', 'java.security.Key').implementation = function (mode, key) {
          try {
            out.push(`[cipher] init mode=${mode} alg=${this.getAlgorithm()} key=${hex(key.getEncoded())}`);
          } catch (e) {}
          return this.init(mode, key);
        };
        Cipher.init.overload('int', 'java.security.Key', 'java.security.spec.AlgorithmParameterSpec').implementation = function (mode, key, spec) {
          try {
            out.push(`[cipher] init+spec mode=${mode} alg=${this.getAlgorithm()} key=${hex(key.getEncoded())} spec=${spec}`);
          } catch (e) {}
          return this.init(mode, key, spec);
        };
        Cipher.doFinal.overload('[B').implementation = function (input) {
          let alg = '';
          try { alg = this.getAlgorithm(); } catch (e) {}
          out.push(`[cipher] doFinal alg=${alg} IN(${input ? input.length : 0}B) hex=${hex(input)}`);
          out.push(`[cipher]        IN-ascii="${ascii(input)}"`);
          const res = this.doFinal(input);
          out.push(`[cipher] OUT(${res ? res.length : 0}B) hex=${hex(res)}`);
          out.push(`[cipher]        OUT-ascii="${ascii(res)}"`);
          return res;
        };
        out.push('[cipher] hooked javax.crypto.Cipher');
      } catch (e) {
        out.push('[cipher] hook 失败: ' + e);
      }
    });
    return out;
  },
};
