var pat = /ss|cronet|tprt|flutter|app|tt|tencent|net/i;
var mods = Process.enumerateModules();
console.log("total modules: " + mods.length);
mods.filter(function(m){ return pat.test(m.name); }).forEach(function(m){ console.log("  " + m.name + " @ " + m.base + " size=" + m.size); });
console.log("--- java check ---");
try { Java.perform(function(){ console.log("java bridge ok, classloader=" + Java.classFactory.loader); }); } catch (e) { console.log("java fail: " + e); }