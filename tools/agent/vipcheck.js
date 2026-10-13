// vipcheck.js — 读当前 VIP 状态（需 frida-java-bridge）
import Java from 'frida-java-bridge';

rpc.exports.check = function () {
  const out = {};
  Java.perform(() => {
    try {
      const C = Java.use('ia30');
      out.i = C.i().toString();
      out.n = C.n().toString();
      out.r = C.r().toString();
      out.verdict = (C.n() > 0 && C.i() > 0) ? '客户端自认VIP（补丁仍在）' : '客户端自认非VIP（诚实 ✅）';
    } catch (e) { out.err = String(e); }
  });
  return out;
};
