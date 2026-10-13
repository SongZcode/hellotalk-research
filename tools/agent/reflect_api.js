// reflect_api.js — 用 Java 反射直接读出 Retrofit 接口定义（URL + 参数模型 + 字段名）
import Java from 'frida-java-bridge';

function dumpInterface(name) {
  const out = [];
  try {
    const C = Java.use(name);
    const methods = C.class.getDeclaredMethods();
    for (let i = 0; i < methods.length; i++) {
      const m = methods[i];
      let url = null;
      try {
        const anns = m.getAnnotations();
        for (let j = 0; j < anns.length; j++) {
          const a = anns[j];
          const s = String(a);
          if (s.indexOf('/') >= 0) url = s;
        }
      } catch (e) {}
      const params = m.getParameterTypes();
      const ptypes = [];
      for (let j = 0; j < params.length; j++) {
        const pn = params[j].getName();
        if (pn.indexOf('j98') < 0) ptypes.push(pn); // 过滤掉协程 Continuation
      }
      if (url) out.push({ method: m.getName(), url: url, params: ptypes });
    }
  } catch (e) {
    out.push({ error: String(e).slice(0, 120) });
  }
  return out;
}

function dumpFields(className) {
  const out = [];
  try {
    const C = Java.use(className);
    const fs = C.class.getDeclaredFields();
    for (let i = 0; i < fs.length; i++) {
      const f = fs[i];
      let tag = null;
      try {
        const anns = f.getAnnotations();
        for (let j = 0; j < anns.length; j++) {
          const s = String(anns[j]);
          if (s.indexOf('@') === 0 && s.length < 60) tag = s;
        }
      } catch (e) {}
      out.push({ field: f.getName(), type: f.getType().getName(), ann: tag });
    }
  } catch (e) {
    out.push({ error: String(e).slice(0, 120) });
  }
  return out;
}

rpc.exports = {
  iface(name) { let r = null; Java.perform(() => { r = dumpInterface(name); }); return r; },
  fields(name) { let r = null; Java.perform(() => { r = dumpFields(name); }); return r; },
  ifaces(names) {
    const r = {};
    Java.perform(() => { names.forEach((n) => { r[n] = dumpInterface(n); }); });
    return r;
  },
};
