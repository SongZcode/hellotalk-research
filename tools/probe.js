Java.perform(function () {
  console.log("[+] Java bridge ok");
  var mods = Process.enumerateModules();
  console.log("[+] modules: " + mods.length);
  mods.slice(0, 12).forEach(function (m) { console.log("   " + m.name + " @" + m.base); });
});