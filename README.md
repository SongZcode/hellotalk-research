# HelloTalk 客户端与协议安全研究

> ⚠️ **本项目仅供安全研究与学习交流使用。请先完整阅读下方的 [免责声明](#免责声明) 与 [使用警告](#使用警告)。**

对 HelloTalk Android 客户端（v6.4.20）通信协议、加密方案与客户端授权机制的**静态与动态分析记录**。
全部结论均来自对**自己账号、自己设备、自有APK样本**的本地测试环境，用于理解移动应用的协议设计与风控设计。

---

## 📌 这个仓库是什么

一份**技术分析笔记 + 复现工具**，包含：

| 方向 | 内容 |
|---|---|
| **IM 协议** | `ht_im/sock` WebSocket 帧格式、opcode 表、握手流程、消息收发，以及一个可独立运行的协议客户端 |
| **HTTP 加密** | `ht/encbin` / `ht/binary` 应用层加密的定位与解密方式（含 `libsscronet` + BoringSSL 层面的处理） |
| **客户端 Hook** | frida 环境搭建（含 Android 14+ 进程冻结等坑）、证书绕过、自定义加解密的观测点 |
| **授权机制** | 会员判定链路、被服务端管控的额度机制（如打招呼次数）的判定过程与结论 |
| **支付链路** | 下单 → 支付渠道 → 回调的完整性校验分析（结论：客户端侧无法伪造） |
| **逆向工具** | smali/dex 扫描、Retrofit 接口反射、UI 自动化、抓包分析等一批脚本 |

### 结论摘要

- 握手后的 IM 帧**不是加密**，而是 **zlib 压缩的 JSON**（早期"需要会话密钥解密"的判断是错误的）
- 会员状态、额度计数、订单价格 **全部由服务端权威判定**；客户端本地状态仅用于展示
- 客户端侧的本地改动**可以改变界面表现**，但**无法**改变服务端计数、价格与权益发放
- 支付渠道回调 + 请求完整性校验，使客户端伪造订单不可行

---

## ⚠️ 使用警告

**在使用本仓库任何内容之前，请确认你理解并接受以下几点：**

1. **不要在自己不拥有的账号或设备上使用**
   本仓库的工具涉及对运行中 App 进程的注入与流量拦截。对**他人账号、他人设备、他人网络**进行任何操作都可能构成违法，且会侵害他人隐私。

2. **不要用于任何商业用途或牟利行为**
   包括但不限于：出售破解版、代充、代注册、账号交易、刷量、薅取平台补贴等。

3. **可能违反目标服务的使用条款**
   修改客户端、拦截流量、绕过授权校验等行为，通常被服务条款明确禁止，**可能导致账号被限制或封禁**。本仓库作者已对此做出实测记录，但**不承担你因此产生的任何后果**。

4. **不要用于骚扰、诈骗或任何侵犯他人的行为**
   本项目**与**任何形式的骚扰、诈骗、身份冒用、非法获取他人信息**无关**，也**不支持**此类用途。

5. **法律风险自负**
   不同司法辖区对逆向工程、流量拦截、客户端修改的规定差异很大。**在你所在地区是否合法，请自行评估并咨询专业意见。** 继续使用即表示你自行承担全部责任。

6. **随时可能失效**
   目标应用会持续更新，本文所有结论**只对特定版本（v6.4.20）在特定时间点的行为负责**，不保证未来有效。

7. **不包含任何第三方资产**
   本仓库**不包含**目标应用的 APK、二进制、图片、字体或其他受版权保护的内容（它们属于其各自权利人）。复现所需样本请自行从官方渠道获取。

---

## 🧪 研究方法与边界

- 全部测试在**自有设备 + 自有账号 + 官方渠道下载的样本**上进行
- 抓包环境为本地 mitmproxy + 自签名 CA，仅拦截本人设备流量
- 所有涉及真实标识（用户 ID、设备号、会话密钥、令牌、IP）的内容**已脱敏为占位符**
- 未包含任何可用于攻击他人账号的自动化流程（不含批量注册、撞库、短信绕过等）

**研究目的**：理解协议设计、加密边界与风控思路，为防御侧与移动安全学习提供参考。

---

## 📁 目录结构

```
docs/                      分析文档
  PROTOCOL-ht_im.md        IM 协议完整解析（帧结构 / opcode / 握手 / 收发）
  FRIDA-HTTPS.md           frida 环境搭建 + HTTPS 解密方案
  VIP-PAYMENT-CHAIN.md     支付链路与完整性校验分析
  VIP-CARD-MODULE.md       权益卡 / 激励视频模块接口分析
  HELLOTALK-HANDOFF.md     总交接文档
  codex/                   静态分析（smali/dex）记录

tools/                     复现工具
  ht_frame.py              IM 帧编解码库（构造 / 解析 / 校验）
  ht_client.py             独立协议客户端（握手 / 收件箱 / 拉取 / 发送）
  ht_live.py               mitmproxy 插件：协议明文实时解码
  agent/                   frida agent 源码（证书绕过 / 加解密观测 / 模型反射）
  fx_*.py                  frida agent 加载器（guard / 观测 / 反射）
  dex_*.py / scan_*.py     dex、smali 静态扫描
  ui_*.py                  UI 自动化（元素定位 / 文本提取 / 点击）
```

> 注：`tools/agent/*.bundle.js` 为 esbuild 构建产物，未入库；本地执行
> `esbuild <x>.js --bundle --format=iife --platform=neutral --target=es2020 --outfile=<x>.bundle.js` 即可生成。

---

## 🛠 复现环境（供学习参考）

- Windows + PowerShell，Python 3.13（venv）
- mitmproxy（抓包与协议解码）
- frida 17 + `frida-java-bridge`（需要自行 bundle）
- frida-gadget（用于免 root 注入，自行下载对应架构版本）
- Android SDK（adb / apktool / zipalign / apksigner）

**仅描述所用工具链，不提供任何第三方二进制。**

---

## 📄 许可与声明

本仓库内容以「**仅供学习研究，保持原样**」形式提供。
See [LICENSE](LICENSE) —— 详见其中关于**禁止商业使用**与**免责**的条款。

---

## Disclaimer (English)

**This repository is for security research and educational purposes only.**

- Do **not** use anything here against accounts, devices, or networks you do not own.
- Do **not** use it for harassment, fraud, or any illegal activity.
- Modifying a client or intercepting traffic may violate the target service's Terms of Service and may result in account restrictions. **You assume all consequences.**
- Reverse engineering and traffic interception laws differ by jurisdiction — **evaluate legality in your own region before use**.
- No third-party assets (APKs, binaries, media) are included. All findings are version-specific (v6.4.20) and may become obsolete at any time.
- Provided "AS IS", without warranty of any kind.

---

*本仓库为个人学习记录，与 HelloTalk 官方无任何关联。*
