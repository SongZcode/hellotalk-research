$env:JAVA_HOME='F:\located\toolchain\jdk17'; $env:PATH="$env:JAVA_HOME\bin;F:\located\toolchain\sdk\build-tools\34.0.0;$env:PATH"
$java="$env:JAVA_HOME\bin\java.exe"
$proj='F:\hellotalk-vip\artifacts\apktool_raw'
$out='F:\hellotalk-mitm\artifacts\build'
New-Item -ItemType Directory -Force -Path $out | Out-Null
Write-Output "[1/3] apktool build (含 gadget)"
& $java -Xmx5g -jar 'F:\hellotalk-vip\tools\apktool.jar' b $proj -o "$out\ht-gadget-unsigned.apk" 2>&1 | Select-Object -Last 5
Write-Output "[2/3] zipalign -p 16384"
& zipalign -f -p 16384 "$out\ht-gadget-unsigned.apk" "$out\ht-gadget-aligned.apk" 2>&1 | Select-Object -First 3
Write-Output "[3/3] sign"
& apksigner sign --ks 'F:\hellotalk-vip\tools\ht-debug.keystore' --ks-pass pass:android --key-pass pass:android --out "$out\com.hellotalk.gadget.apk" "$out\ht-gadget-aligned.apk" 2>&1 | Select-Object -First 3
Write-Output "[4/4] 两个 split 用同一 key 重签"
& apksigner sign --ks 'F:\hellotalk-vip\tools\ht-debug.keystore' --ks-pass pass:android --key-pass pass:android --out "$out\com.hellotalk.arm64.apk" 'F:\hellotalk-vip\artifacts\build\signed2\com.hellotalk.arm64.apk' 2>&1 | Select-Object -First 2
& apksigner sign --ks 'F:\hellotalk-vip\tools\ht-debug.keystore' --ks-pass pass:android --key-pass pass:android --out "$out\com.hellotalk.mdpi.apk" 'F:\hellotalk-vip\artifacts\build\signed2\com.hellotalk.mdpi.apk' 2>&1 | Select-Object -First 2
Get-ChildItem $out -Filter '*.apk' | Select-Object Name,Length | Format-Table -AutoSize