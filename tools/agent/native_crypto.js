// native_crypto.js — 挂原生 AES/EVP 函数，捞 ht/encbin 接口的明文
function looksJson(ptr, len) {
  if (!ptr || !len || len <= 0) return false;
  try {
    const n = Math.min(len, 8);
    const b = new Uint8Array(ptr.readByteArray(n));
    for (let i = 0; i < n; i++) {
      const c = b[i];
      if (c === 0x20 || c === 0x09 || c === 0x0a || c === 0x0d) continue;
      return c === 0x7b || c === 0x5b || c === 0x22; // { [ "
    }
  } catch (e) {}
  return false;
}

const MAX = 1600;
let hits = [];

function hexdump(ptr, len) {
  if (!ptr || !len || len < 0) return '';
  try {
    const n = Math.min(len, MAX);
    const bytes = new Uint8Array(ptr.readByteArray(n));
    let hexs = '', asc = '';
    for (let i = 0; i < n; i++) {
      hexs += ('0' + bytes[i].toString(16)).slice(-2);
      asc += (bytes[i] >= 32 && bytes[i] < 127) ? String.fromCharCode(bytes[i]) : '.';
    }
    return hexs + (len > MAX ? `...(+${len - MAX}B)` : '') + '\n           ascii: ' + asc;
  } catch (e) { return '<dump err ' + e + '>'; }
}

const WANT = [
  'EVP_EncryptUpdate', 'EVP_DecryptUpdate', 'EVP_EncryptFinal_ex', 'EVP_DecryptFinal_ex',
  'AES_cbc_encrypt', 'AES_encrypt', 'AES_decrypt', 'AES_set_encrypt_key', 'AES_set_decrypt_key',
  'AES_ctr128_encrypt', 'CRYPTO_cbc128_encrypt', 'CRYPTO_ctr128_encrypt',
];

rpc.exports = {
  scan() {
    const res = {};
    for (const m of Process.enumerateModules()) {
      if (!/crypto|ssl|NetHT|tprt|tpcore|sscronet/i.test(m.name)) continue;
      let exps = [];
      try { exps = m.enumerateExports(); } catch (e) { continue; }
      const names = exps.map((e) => e.name).filter((n) => /EVP_|AES_|CRYPTO_/.test(n));
      if (names.length) res[m.name] = names.slice(0, 40);
    }
    return res;
  },

  install() {
    const lines = [];
    let count = 0;
    for (const m of Process.enumerateModules()) {
      if (!/crypto|ssl|NetHT|tprt|tpcore|sscronet/i.test(m.name)) continue;
      let exps = [];
      try { exps = m.enumerateExports(); } catch (e) { lines.push(`enum ${m.name} failed: ${e}`); continue; }
      for (const e of exps) {
        const sym = e.name;
        if (WANT.indexOf(sym) < 0) continue;
        if (e.type !== 'function') continue;
        const addr = e.address;
        try {
          Interceptor.attach(addr, {
            onEnter(args) {
              try {
                if (sym === 'EVP_EncryptUpdate') {
                  // (ctx, out, outl, in, inl) —— 只关心「明文是 JSON」的那次（应用层加密）
                  const inl = args[4].toInt32();
                  if (looksJson(args[3], inl)) {
                    send({ tag: 'crypto', msg: `[${sym}] ${m.name} in=${inl}B\n           ${hexdump(args[3], inl)}` });
                  }
                } else if (sym === 'EVP_DecryptUpdate') {
                  // 解密：记下 out 指针，onLeave 判断明文是否 JSON
                  this._out = args[1];
                  this._outl = args[2];
                } else if (sym === 'AES_cbc_encrypt') {
                  // (in, out, len, key, ivec, enc)
                  const len = args[2].toInt32();
                  const enc = args[5].toInt32();
                  if (enc === 1 && looksJson(args[0], len)) {
                    send({ tag: 'crypto', msg: `[${sym}] ${m.name} enc=1 len=${len}\n           key=${hexdump(args[3], 32)}\n           ivec=${hexdump(args[4], 16)}\n           ${hexdump(args[0], len)}` });
                  }
                } else if (sym === 'AES_encrypt' || sym === 'AES_decrypt') {
                  if (looksJson(args[0], 16)) {
                    send({ tag: 'crypto', msg: `[${sym}] ${m.name} in=${hexdump(args[0], 16)} key=${hexdump(args[2], 32)}` });
                  }
                } else if (sym === 'AES_set_encrypt_key' || sym === 'AES_set_decrypt_key') {
                  // 密钥设置单独打印（可能很多，截断）
                  const k = hexdump(args[0], 32);
                  if (k && !hits.includes(k)) { hits.push(k); send({ tag: 'crypto', msg: `[${sym}] key=${k} bits=${args[1].toInt32()}` }); }
                }
              } catch (e) { send({ tag: 'crypto', msg: '[err] ' + sym + ': ' + e }); }
            },
            onLeave(retval) {
              try {
                if (sym === 'EVP_DecryptUpdate' && this._out && this._outl) {
                  const n = this._outl.readInt();
                  if (n > 0 && looksJson(this._out, n)) {
                    send({ tag: 'crypto', msg: `[${sym}] plain_out=${n}B\n           ${hexdump(this._out, n)}` });
                  }
                }
              } catch (e) {}
            },
          });
          count++;
          lines.push(`hooked ${sym} in ${m.name}`);
        } catch (e) { lines.push(`hook ${sym} in ${m.name} failed: ${e}`); }
      }
    }
    lines.unshift(`共挂 ${count} 个函数`);
    return lines;
  },
};
