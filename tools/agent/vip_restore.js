// vip_restore.js — 运行时把客户端 VIP 状态还原为服务端真实值（非会员），用于找出被补丁藏起来的促活入口
import Java from 'frida-java-bridge';

// 服务端 vip_info 实测：vip_type=0, vip_expire=1790022926（已过期）
const REAL_EXPIRE = 1790022926;
const REAL_TYPE = 0;

let on = true;

rpc.exports = {
  set(v) { on = !!v; return on; },
  install() {
    const out = [];
    Java.perform(() => {
      try {
        const C = Java.use('ia30');
        const origI = C.i.overload();
        const origN = C.n.overload();
        const origR = C.r.overload();

        C.i.implementation = function () {
          const v = on ? REAL_EXPIRE : origI.call(this);
          return v;
        };
        C.n.implementation = function () {
          const v = on ? REAL_TYPE : origN.call(this);
          return v;
        };
        C.r.implementation = function () {
          const v = on ? false : origR.call(this);
          return v;
        };
        out.push('[vip_restore] 已挂钩 ia30.i/n/r（当前模式: ' + (on ? '还原非会员' : '补丁VIP') + '）');
        out.push('  i() 原值=' + origI.call(null) + ' → 现在=' + C.i.overload().call(null));
        out.push('  n() 原值=' + origN.call(null) + ' → 现在=' + C.n.overload().call(null));
        out.push('  r() 原值=' + origR.call(null) + ' → 现在=' + C.r.overload().call(null));
      } catch (e) {
        out.push('[vip_restore] 失败: ' + e);
      }
    });
    return out;
  },
};
