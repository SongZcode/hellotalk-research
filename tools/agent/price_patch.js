// price_patch.js — 在 EVP_EncryptUpdate 里就地改写明文（验证服务端是否信任客户端上报的金额）
// 只改同长度字段，避免破坏缓冲区长度
const FROM = '"amount":888000';
const TO   = '"amount":000001';   // 同长度（6 位数字）
const seenKeys = {};

function findSeq(buf, len, needle) {
  const n = needle.length;
  if (len < n) return -1;
  const head = needle.charCodeAt(0);
  const bytes = new Uint8Array(buf.readByteArray(len));
  for (let i = 0; i <= len - n; i++) {
    if (bytes[i] !== head) continue;
    let ok = true;
    for (let j = 1; j < n; j++) {
      if (bytes[i + j] !== needle.charCodeAt(j)) { ok = false; break; }
    }
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
      if (c === 0x20 || c === 0x09 || c === 0x0a || c === 0x0d) continue;
      return c === 0x7b || c === 0x5b || c === 0x22;
    }
  } catch (e) {}
  return false;
}

function dump(ptr, len) {
  try {
    const n = Math.min(len, 1200);
    const b = new Uint8Array(ptr.readByteArray(n));
    let s = '';
    for (let i = 0; i < n; i++) s += String.fromCharCode(b[i]);
    return s + (len > n ? `...(+${len - n}B)` : '');
  } catch (e) { return '<err ' + e + '>'; }
}

rpc.exports = {
  install() {
    const lines = [];
    let n = 0;
    const MOD = /crypto|ssl|NetHT|tprt|tpcore|hpt|protect/i;
    for (const m of Process.enumerateModules()) {
      if (!MOD.test(m.name)) continue;
      let exps = [];
      try { exps = m.enumerateExports(); } catch (e) { continue; }
      for (const e of exps) {
        if (e.type !== 'function') continue;

        if (e.name === 'AES_cbc_encrypt') {
          try {
            Interceptor.attach(e.address, {
              onEnter(args) {
                try {
                  const len = args[2].toInt32();
                  const enc = args[5].toInt32();
                  if (len <= 0 || len > 65536) return;
                  if (enc === 1) {
                    // 加密方向：就地改金额
                    const off = findSeq(args[0], len, FROM);
                    if (off >= 0) {
                      args[0].add(off).writeByteArray(Array.from(TO).map((c) => c.charCodeAt(0)), 0, TO.length);
                      send({ tag: 'patch', msg: `[patch-cbc] ${m.name} @${off} ${FROM} -> ${TO} (len ${len})` });
                    }
                  } else {
                    // 解密方向：明文在 out
                    this._out = args[1]; this._len = len;
                    send({ tag: 'dec', msg: `[cbc-dec] ${m.name} key=${dump(args[3], 32)} iv=${dump(args[4], 16)} ct=${dump(args[0], Math.min(len, 64))}` });
                  }
                } catch (err) { send({ tag: 'patch', msg: '[cbc err] ' + err }); }
              },
              onLeave() {
                try {
                  if (this._out && this._len > 0 && looksJson(this._out, this._len)) {
                    send({ tag: 'dec', msg: `[cbc-dec] plain=${this._len}B ${dump(this._out, this._len)}` });
                  }
                } catch (err) {}
              },
            });
            n++;
            lines.push(`hooked AES_cbc_encrypt in ${m.name}`);
          } catch (err) { lines.push(`hook cbc failed ${m.name}: ${err}`); }
        }

        if (e.name === 'AES_set_encrypt_key' || e.name === 'AES_set_decrypt_key') {
          try {
            Interceptor.attach(e.address, {
              onEnter(args) {
                try {
                  const k = dump(args[0], 32);
                  if (!seenKeys[k]) { seenKeys[k] = 1; send({ tag: 'key', msg: `[${e.name}] ${m.name} key=${k}` }); }
                } catch (err) {}
              },
            });
            n++;
          } catch (err) {}
        }

        if (e.name === 'EVP_EncryptUpdate') {
          try {
            Interceptor.attach(e.address, {
              onEnter(args) {
                try {
                  const inl = args[4].toInt32();
                  if (inl <= 0 || inl > 65536) return;
                  const inPtr = args[3];
                  const off = findSeq(inPtr, inl, FROM);
                  if (off < 0) return;
                  inPtr.add(off).writeByteArray(Array.from(TO).map((c) => c.charCodeAt(0)), 0, TO.length);
                  send({ tag: 'patch', msg: `[patch] ${m.name} @${off} "${FROM}" -> "${TO}" (body ${inl}B)` });
                } catch (err) { send({ tag: 'patch', msg: '[patch err] ' + err }); }
              },
            });
            n++;
            lines.push(`hooked EVP_EncryptUpdate in ${m.name}`);
          } catch (err) { lines.push(`hook enc failed ${m.name}: ${err}`); }
        }

        if (e.name === 'EVP_DecryptUpdate') {
          try {
            Interceptor.attach(e.address, {
              onEnter(args) {
                this._out = args[1];
                this._outl = args[2];
              },
              onLeave() {
                try {
                  if (!this._out || !this._outl) return;
                  const n2 = this._outl.readInt();
                  if (n2 > 0 && looksJson(this._out, n2)) {
                    send({ tag: 'dec', msg: `[dec] ${m.name} plain=${n2}B ${dump(this._out, n2)}` });
                  }
                } catch (err) {}
              },
            });
            n++;
            lines.push(`hooked EVP_DecryptUpdate in ${m.name}`);
          } catch (err) { lines.push(`hook dec failed ${m.name}: ${err}`); }
        }
      }
    }
    lines.unshift(`挂了 ${n} 个函数`);
    return lines;
  },
};
