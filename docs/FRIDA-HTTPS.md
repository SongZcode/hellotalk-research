# frida + HTTPS 抓包打通记录（2026-10-11 深夜）

> 结论：**HelloTalk 的 HTTPS 已可完整解密**。frida gadget 会话修好，证书校验绕过生效，
> 44 个接口的真实请求/响应（含参数、签名、body）全部可见。

---

## 1. frida 会话挂死的真因（关键）

**不是版本问题**（gadget 与 PC 端都是 17.23.3，已核对 APK 内 `libgadget.so` 的版本串）。

真因：**App 在后台时被 Android 14+ 冻结（cached process freeze）**，gadget 的 agent 线程随之冻住 →
现象：端口在监听、`enumerate_processes` 偶尔能过、`attach` 挂死或 `ServerNotRunningError`。

**解法（三条缺一不可）**：
```powershell
$adb='F:\located\toolchain\sdk\platform-tools\adb.exe'; $s='<PHONE_LAN_IP>:39083'
& $adb -s $s shell "input keyevent KEYCODE_WAKEUP; svc power stayon true"   # 屏幕唤醒+常亮
& $adb -s $s shell "monkey -p com.hellotalk -c android.intent.category.LAUNCHER 1"  # 让 App 在前台
& $adb -s $s forward tcp:27042 tcp:27042    # ← 重启 adb server 会清掉转发，务必重加
```

## 2. 证书绕过 agent（frida 17 需自带 Java 桥）

frida 17 移除了内置 Java 桥（`typeof Java === "undefined"`），必须用 `frida-java-bridge` 打包：

```powershell
cd F:\hellotalk-mitm\tools\agent
npm install frida-java-bridge esbuild buffer
node node_modules\esbuild\bin\esbuild agent.js --bundle --format=iife --platform=neutral --target=es2020 `
     --outfile=agent.bundle.js
```

`agent.js` 挂的东西：
- **Java**：`com.android.org.conscrypt.TrustManagerImpl.verifyChain` → 直接返回原始链（**主力**）
  ＋ `checkTrustedRecursive` → 返回空
- **native**：`X509_verify_cert`（全局 + 各 crypto 库）、`X509_STORE_CTX_get_error`、`SSL_get_verify_result`

实测装载日志：
```
[native] 目标模块: libcrypto.so, libssl.so, stable_cronet_libcrypto.so,
                   stable_cronet_libpki.so, stable_cronet_libssl.so
[native] global hooked X509_verify_cert
[java] hooked TrustManagerImpl.verifyChain ✅
[java] hooked TrustManagerImpl.checkTrustedRecursive ✅
```

运行器：
| 脚本 | 用途 |
|---|---|
| `tools/fx_probe.py` | 探测 Java 桥/模块/类 |
| `tools/fx_run.py` | 一次性装载 + 打印日志 |
| `tools/fx_keep.py` | 常驻装载 |
| **`tools/fx_guard.py`** | **守护进程**：App 一启动/重启就自动重挂（推荐） |

## 3. 抓包姿势（两个坑）

1. **必须先设代理再启动 App**：App 有长连接池，先启动后设代理的话，旧连接是直连的，抓不到新请求
2. 抓包期间 App 必须**保持前台**（否则冻结 → 钩子失效）

```powershell
# 起抓包（已解密的 WS + HTTP 都会写进 api.log / ws.jsonl）
$venv='F:\hellotalk-mitm\tools\venv\Scripts'
Start-Process "$venv\mitmdump.exe" -ArgumentList '-p','8080','--set','block_global=false',
  '-s','F:\hellotalk-mitm\tools\ht_live.py','-w','F:\hellotalk-mitm\artifacts\mitm\flows_https.mitm',
  '--set','ws_deflate=false','--set','flow_detail=0'
& $adb -s $s shell "settings put global http_proxy <PC_LAN_IP>:8080"
# 守护挂钩子（后台跑）
python -u F:\hellotalk-mitm\tools\fx_guard.py
```

验证：`mitm_https.out` 里 `Client TLS handshake failed` 计数应为 **0**（之前 95~312）。

## 4. 已解密的关键接口（44 个，真实请求/响应）

| 接口 | 用途 | 备注 |
|---|---|---|
| **`POST /payment_gateway_v2/user/vip_info`** | **VIP 状态（服务端权威）** | 见 §5 |
| `GET /api/login_config/business/vip_product` | VIP 商品 | 响应为**二进制/密文** |
| `GET /api/login_config/business/vip_page_content` | VIP 页内容 | 响应为**密文** |
| `GET /config-center/v1/vip_page_banner` | VIP banner | 明文 404 |
| `GET /api/login_config/business/chat_magic_wand` | 魔法棒话术 | 响应密文 |
| `GET /api/login_config` | 启动配置 | 带客户端上报的 `vip=2` |
| `GET /system_notice/v1/notice`、`/v3/moment/notify`、`/lang_exchange/v3/exchange_list` 等 | 业务接口 | — |
| `GET /ht_im/sock` | IM 长连接（WS） | 明文 zlib JSON（见协议文档） |

**共同点**：查询串里带 `userid/t/lang/version/htntkey/te/le/na/tl/vip/birthday/sex/build/channel/deviceid/reg/...`
—— 其中 **`htntkey` 是请求签名**（改包需重算，签名 key 未知）；`vip=2` 是**客户端自己上报的**字段（见 §5 研究点）。

## 5. 服务端 VIP 状态（权威答案）

```http
POST /payment_gateway_v2/user/vip_info
authorization: Bearer <JWT>
x-ht-session: <加密会话串>
body: {"user_id":<UID>,"ignore_sub":0}
```
```json
{"status":0,"msg":"success","data":{
  "vip_type":0,             // ← 0 = 非 VIP（服务端判定）
  "vip_stat":1,
  "last_vip_type":1,        // 曾经是 VIP
  "vip_expire":1790022926,
  "vip_plus_type":0, "vip_plus_expire":0,
  "current_vip_level":"Normal",
  "current_vip_renewals_status":"Normal",
  "visitor_expire_ts":0, "learn_language_expire_ts":0, "teach_language_expire_ts":0,
  "is_first_vip":false, "purchase_product_id":""}}
```

⇒ 服务端认为该账号是 **Normal** 等级 —— 所以「陌生人聊天」额度走免费档（10/日），
所以客户端那些本地 VIP 补丁**只影响 UI 与本地门禁**，影响不了额度。

⇒ **「VIP 破解」的真正靶子就是这个接口的 `vip_type/vip_plus_type` 怎么被服务端改写**：
   - 正常路径 = Google Play 购买 → 客户端通知服务端 → 服务端（大概）向 Google 校验
   - 待查：购买通知接口的**校验强度**（客户端断言 or 服务端与 Google 核对）
   - 待查：`vip_trial`（VIP 试用）与「VIP 体验卡」的领取接口授权强度

## 6. 下一步

1. 在 App 里打开 VIP 页 → 抓 `vip_product` / 购买流程接口 → 定位「购买后通知服务端」的接口与字段
2. 用 `ignore_sub=1` 等参数变体试 `vip_info`（看是否有分支能返回更高等级）
3. 查 `member_privilege_center/v3/vip_trial/*`（试用）与体验卡领取接口
4. 解 `vip_product`/`vip_page_content` 响应密文（可能是 AES，密钥在 so 里）
