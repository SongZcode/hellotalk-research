// prefs_spy.js — 列出/搜索/清除 App 的 SharedPreferences（找「今日不再出现」这类标记）
import Java from 'frida-java-bridge';

const KEYS = /ad|free|popup|show|today|dismiss|card|video|reward|greet|guide|red_?dot|banner|tips|dialog/i;

function ctxPkg() {
  return Java.use('android.app.ActivityThread').currentApplication();
}

rpc.exports = {
  list() {
    const out = [];
    Java.perform(() => {
      try {
        const ctx = ctxPkg();
        const dirPath = ctx.getFilesDir().getParent().toString() + '/shared_prefs';
        const dir = Java.use('java.io.File').$new(dirPath);
        const files = dir.listFiles();
        if (!files) { out.push('no shared_prefs dir'); return; }
        for (let i = 0; i < files.length; i++) {
          out.push(files[i].getName().toString());
        }
      } catch (e) { out.push('err ' + e); }
    });
    return out;
  },

  search(re) {
    const rx = new RegExp(re || KEYS.source, 'i');
    const out = [];
    Java.perform(() => {
      try {
        const ctx = ctxPkg();
        const prefsDir = ctx.getFilesDir().getParent().toString() + '/shared_prefs';
        const list = Java.use('java.io.File').$new(prefsDir).listFiles();
        for (let i = 0; i < list.length; i++) {
          const name = list[i].getName().toString();
          const pname = name.replace(/\.xml$/, '');
          let sp = null;
          try { sp = ctx.getSharedPreferences(pname, 0); } catch (e) { continue; }
          const all = sp.getAll();
          const it = all.keySet().iterator();
          while (it.hasNext()) {
            const k = it.next().toString();
            if (!rx.test(k)) continue;
            let v = null;
            try { v = String(all.get(k)); } catch (e) { v = '<obj>'; }
            out.push({ file: name, key: k, value: v.slice(0, 120) });
          }
        }
      } catch (e) { out.push({ err: String(e) }); }
    });
    return out;
  },

  clear(key) {
    const out = [];
    Java.perform(() => {
      try {
        const ctx = ctxPkg();
        const prefsDir = ctx.getFilesDir().getParent().toString() + '/shared_prefs';
        const list = Java.use('java.io.File').$new(prefsDir).listFiles();
        for (let i = 0; i < list.length; i++) {
          const name = list[i].getName().toString();
          const pname = name.replace(/\.xml$/, '');
          let sp = null;
          try { sp = ctx.getSharedPreferences(pname, 0); } catch (e) { continue; }
          if (sp.contains(key)) {
            sp.edit().remove(key).commit();
            out.push('removed ' + key + ' from ' + name);
          }
        }
      } catch (e) { out.push('err ' + e); }
    });
    return out;
  },
};
