// json_spy.js — hook Java 层 JSON 解析，捞出解密后的响应明文（含支付订单）
import Java from 'frida-java-bridge';

const KEYWORDS = /order|prepay|amount|money|price|trade|wechat|pay|vip|nonce|sign/i;

rpc.exports = {
  install() {
    const out = [];
    Java.perform(() => {
      // 1) org.json
      try {
        const JSONObject = Java.use('org.json.JSONObject');
        JSONObject.$init.overload('java.lang.String').implementation = function (s) {
          try {
            if (s && s.length < 4000 && KEYWORDS.test(s)) {
              out.push('[org.json] ' + s);
              send({ tag: 'json', msg: s });
            }
          } catch (e) {}
          return this.$init(s);
        };
        out.push('[json_spy] hooked org.json.JSONObject(String)');
      } catch (e) { out.push('[json_spy] JSONObject 失败: ' + e); }

      // 2) Gson
      try {
        const Gson = Java.use('com.google.gson.Gson');
        Gson.fromJson.overload('java.lang.String', 'java.lang.Class').implementation = function (s, c) {
          try {
            const cn = String(c);
            if (s && s.length < 4000 && KEYWORDS.test(s)) {
              out.push('[gson->' + cn + '] ' + s);
              send({ tag: 'json', msg: `[${cn}] ${s}` });
            }
          } catch (e) {}
          return this.fromJson(s, c);
        };
        out.push('[json_spy] hooked Gson.fromJson(String,Class)');
      } catch (e) { out.push('[json_spy] Gson 不可用: ' + String(e).slice(0, 60)); }

      // 3) kotlinx.serialization
      for (const cls of ['kotlinx.serialization.json.Json', 'kotlinx.serialization.json.JsonImpl']) {
        try {
          const J = Java.use(cls);
          out.push('[json_spy] 找到 ' + cls);
        } catch (e) {}
      }
    });
    return out;
  },
};
