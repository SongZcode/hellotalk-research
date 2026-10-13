// dbs_spy.js — 列出 App 的数据库文件，并搜「今日/today/date」相关键
import Java from 'frida-java-bridge';

function ctxApp() {
  return Java.use('android.app.ActivityThread').currentApplication();
}

rpc.exports = {
  dbs() {
    const out = [];
    Java.perform(() => {
      try {
        const ctx = ctxApp();
        const base = ctx.getFilesDir().getParent().toString();
        const dirs = ['databases', 'files', 'shared_prefs'];
        for (const d of dirs) {
          const dir = Java.use('java.io.File').$new(base + '/' + d);
          const fs = dir.listFiles();
          if (!fs) continue;
          for (let i = 0; i < fs.length && i < 200; i++) out.push(d + '/' + fs[i].getName().toString());
        }
      } catch (e) { out.push('err ' + e); }
    });
    return out;
  },
};
