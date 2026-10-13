// read_sayhi.js — 从 App 内存里读「免费打招呼次数 / 新会话额度」等模型值
import Java from 'frida-java-bridge';

function dumpInstance(obj, fields) {
  const out = {};
  fields.forEach((f) => {
    try {
      const v = obj[f].value;
      out[f] = (v === null || v === undefined) ? null : String(v);
    } catch (e) { /* 字段可能不存在 */ }
  });
  return out;
}

rpc.exports = {
  // 在内存里找某类的实例并读字段
  choose(cls, fieldsCsv) {
    const out = [];
    const fields = (fieldsCsv || '').split(',').map((s) => s.trim()).filter(Boolean);
    Java.perform(() => {
      try {
        Java.choose(cls, {
          onMatch(inst) {
            out.push(dumpInstance(inst, fields));
          },
          onComplete() {},
        });
      } catch (e) { out.push({ err: String(e).slice(0, 160) }); }
    });
    return out;
  },

  // 列出类的字段名（便于确认字段叫什么）
  fields(cls) {
    const out = [];
    Java.perform(() => {
      try {
        const C = Java.use(cls);
        const fs = C.class.getDeclaredFields();
        for (let i = 0; i < fs.length; i++) out.push(fs[i].getName() + ' : ' + fs[i].getType().getName());
      } catch (e) { out.push('err ' + String(e).slice(0, 160)); }
    });
    return out;
  },
};
