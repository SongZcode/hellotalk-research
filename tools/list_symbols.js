["stable_cronet_libssl.so","libmainlinecronet.133.0.6876.3.so","stable_cronet_libpki.so"].forEach(function (n) {
  try {
    var m = Process.getModuleByName(n);
    console.log("=== " + n + " @ " + m.base);
    var syms = Module.enumerateSymbols(n);
    console.log("  exported symbols: " + syms.length);
    syms.filter(function (s) { return /verify|Verify|X509|SSL_CTX_set|pinning|Pinning/i.test(s.name); })
        .slice(0, 40).forEach(function (s) { console.log("   " + s.name + " @ " + s.address); });
  } catch (e) { console.log("!! " + n + ": " + e); }
});