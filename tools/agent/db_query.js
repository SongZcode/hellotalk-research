// db_query.js — 打开 App 的 SQLite 库，列出表名，并搜含 ad/promo/pop/show/guide/today 的表与键
import Java from 'frida-java-bridge';

function ctxApp() {
  return Java.use('android.app.ActivityThread').currentApplication();
}

rpc.exports = {
  tables(dbName) {
    const out = [];
    Java.perform(() => {
      try {
        const ctx = ctxApp();
        const p = ctx.getDatabasePath(dbName).toString();
        const db = Java.use('android.database.sqlite.SQLiteDatabase').openDatabase(p, null, 1);
        const cur = db.rawQuery("SELECT name FROM sqlite_master WHERE type='table'", null);
        while (cur.moveToNext()) out.push(cur.getString(0));
        cur.close();
        db.close();
      } catch (e) { out.push('err ' + e); }
    });
    return out;
  },

  query(dbName, sql) {
    const out = [];
    Java.perform(() => {
      try {
        const ctx = ctxApp();
        const p = ctx.getDatabasePath(dbName).toString();
        const db = Java.use('android.database.sqlite.SQLiteDatabase').openDatabase(p, null, 1);
        const cur = db.rawQuery(sql, null);
        const n = cur.getColumnCount();
        let rows = 0;
        while (cur.moveToNext() && rows < 60) {
          const row = [];
          for (let i = 0; i < n; i++) {
            try { row.push(cur.getString(i)); } catch (e) { row.push('<blob>'); }
          }
          out.push(row.join(' | '));
          rows++;
        }
        cur.close();
        db.close();
      } catch (e) { out.push('err ' + e); }
    });
    return out;
  },
};
