# HelloTalk VIP 支付链路分析（2026-10-11 深夜实测）

> 结论：**服务端 VIP 无法从客户端伪造。** 价格由服务端价格表决定、请求体有完整性校验、
> 支付确认走微信/Google 服务端回调。客户端能做的只有「读」和「改包被发现」。

---

## 1. 拿到的支付链路（全流程实测）

| 步骤 | 接口 | 加密 | 说明 |
|---|---|---|---|
| 1 | `POST /payment_gateway_v2/report/purchase_action` | 明文 | 点击埋点，带 `sign`（md5 风格） |
| 2 | `POST /payment_gateway_v2/wechatpay/common_json` | **`ht/encbin`** | 真正的下单/报价接口（请求+响应都加密） |
| 3 | 商品信息 | `GET /api/login_config/business/vip_product` 等 | 响应加密（24~99KB） |
| 4 | VIP 状态 | `POST /payment_gateway_v2/user/vip_info` | **明文**，服务端权威 |

**商品（实测页面+接口）**：
- VIP Plus 1 个月 ¥158（`...vip.1monthplus.wechat` 之类）
- **VIP Plus 12 个月 ¥888**，`product_id = com.hellotalk.android.vip.1yearplus.wechat`
- 权益表：**陌生人聊天 25/天（VIP）· 50/天（VIP Plus）** ← 就是限制我们的那个额度

## 2. 加密层已被攻克（读 + 改都能做到）

`ht/encbin` 接口的加密**不在 Java 层**（hooks `javax.crypto.Cipher` 无捕获），走 **native**。

**解法：hook BoringSSL 的 `EVP_EncryptUpdate` / `EVP_DecryptUpdate`**（`libcrypto.so`），
在**加密前的明文缓冲**上直接读/写 —— 既不需要知道密钥，也不用破解密钥交换。

实测抓到的下单明文：
```json
{"terminal_type":1,"app_version":"394260","amount":888000,
 "product_id":"com.hellotalk.android.vip.1yearplus.wechat","currency_code":"CNY",
 "hp_userid":15304,"req_uid":<UID>,"to_id":<UID>,
 "source":"Profile VIP Membership","page_type":"VIP Level Page D","business_type":6,
 "client_config_data":"{\"device_id\":\"48f7242c...\",\"paywall_id\":\"50010\",
   \"vip_type\":\"Plus VIP\",\"scene_id\":\"26\",\"renewal_type\":0,
   \"currency\":\"CNY\",\"template_page_type\":1}"}
```

响应明文靠 hook **Java 层 JSON 解析**（`org.json.JSONObject(String)` / `Gson.fromJson`）拿到。

## 3. 关键实验：价格篡改（失败，有证据）

在 `EVP_EncryptUpdate` 里把明文 `"amount":888000` 就地改写成 `"amount":000001`（同长度）：

| 轮次 | 请求 | 服务端响应 |
|---|---|---|
| 基线 | `amount:888000` | `{"order_id":"254247439026","error_code":-1,"pay_amount_str":"888.0",...}` → **订单已创建** |
| 篡改 | `amount:000001` | `{"order_id":"","error_code":-1,"pay_amount_str":"888.0",...}` → **订单未创建** |

**结论**：
1. 服务端**用自己的价格表**报价（响应里始终 `888.0`，与客户端上报无关）
2. 篡改被**识别并拒绝** → 请求体有完整性保护（`x-ht-pub` 头极可能是签名/校验值）
3. 支付确认由微信/Google 直接回调商户服务端 → 客户端无法伪造

## 4. 顺带证实的风险信号

AppsFlyer 上报里带 `"sig":"5DB3A1E7...A454"` —— **正是我们调试证书的 SHA-256**。
第三方归因 SDK 与 HelloTalk 自身的遥测都能看到「这不是官方签名的包」。

## 5. 复现命令

```powershell
# 1) 前置：App 前台、屏幕常亮、adb 转发
& $adb -s $s shell "input keyevent KEYCODE_WAKEUP; svc power stayon true"
& $adb -s $s forward tcp:27042 tcp:27042

# 2) 常驻证书绕过（App 重启自动重挂）
python -u <WORKDIR>\tools\fx_guard.py

# 3) 支付探测（改金额 + 捞响应）
node tools\agent\node_modules\esbuild\bin\esbuild tools\agent\pay_probe.js --bundle --format=iife `
     --platform=neutral --target=es2020 --outfile=tools\agent\pay_probe.bundle.js
python -u tools\fx_pay.py --patch-on --seconds 200

# 4) 驱动 UI 下单
python tools\ui_tap.py tap --xy 934,1952   # 选 12 个月套餐
python tools\ui_tap.py tap --xy 640,2611   # 点继续
```

## 6. 最终判定

| 目标 | 结果 |
|---|---|
| 本地 VIP 门禁（翻译/谁看了我/附近的人） | ✅ 已解锁（客户端 patch） |
| **服务端 VIP（陌生人聊天 25/50 额度等）** | ❌ **不可伪造**：价格服务端定、请求体完整性校验、支付渠道服务端回调 |
| 绕过「陌生人聊天 10/日」配额 | ❌ 服务端按账号+日计数（`notice_type:18`） |
| 可行的替代 | 换账号 / 让对方先发消息（已有会话回复不限，实测 `-1`）/ 真实付费 |
