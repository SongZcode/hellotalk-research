# T1 打招呼判定链（客户端 or 服务端）— HelloTalk 6.4.20 静态分析

**结论先行：服务端拦截。** 客户端不存在「本地计数 ≥ N → return/弹窗」的闸门；打招呼请求照常发出，
由服务端在 IM 发送应答里返回错误码 **18**，客户端再做 toast + VIP 付墙 UX。

## 1. 完整调用链（附近页 SayHi 按钮 → 请求发出）

| 步 | 位置 | 说明 |
|---|---|---|
| 1 | `smali_classes6\bs3.smali:346` | 卡片点击回调直接 `invoke-interface Lz2h;->R0(Context,uid,...)`；前置只有文案长度判断（299-307），无计数判断 |
| 1' | `smali_classes6\d6.smali:597`、`smali_classes7\k1m.smali:894` | 另两处入口（Moment 引导、其它卡片），同样直调 R0 |
| 1'' | `smali\z2h.smali:452` | 接口声明 `z2h.R0(...)`；实现 `smali\klz.smali:2867`（klz）、`smali_classes5\llz.smali:462` |
| 2 | `smali\klz.smali:2888-2943` | 构造打招呼消息体 `IMNewStickerBean{productId=1,imageId=11,helloMsg=1}`（"打招呼"贴纸消息） |
| 3 | `smali\klz.smali:2871-2879,2996` | 先建错误回调 `b7z(Context,Function1)`，再 `mwg.c(uid,"new_sticker",C2cChat,bean,...,jov,0x330)` |
| 4 | `smali_classes5\jov.smali:5301-5343` | case 19：拿到构建好的 HTIMMessage → `klz.P(msg,traceId)`（`smali\klz.smali:2380` 写 HTMessageExt.traceId）→ `mwg.e(msg,b7z,2)` |
| 5 | `smali_classes7\mwg.smali:1106 → 805 → 1098` | `e()` 补默认参数调 `d()`；`d()` 内 1098 `IIMChatBaseService.w1(msg,ncf,z)`（1076 `hcf.c()` 取 `IIMC2CChatService`） |
| 6 | `smali\com\hellotalk\lib\im\service\impl\IMC2CChatServiceImpl.smali:1-6` | 实现类，父类 `…impl\base\IMChatBaseServiceImpl`（`w1` 定义在父类 2191） |
| 7 | `…IMChatBaseServiceImpl.smali:2191-2233` | `w1` 起协程 `smali_classes5\csg.smali`；`csg.smali:282` 调 `Y0(...)`，桥接见 `IIMChatBaseService.smali:233-264` → `o(...)` → `…IMChatBaseServiceImpl.smali:1940` → `jrg` 协程 |
| 8 | `csg.smali:304-328` | `Y0` 返回 int 结果码；非 0 → 328 `ncf.onError(code,"缓存消息失败")`；预处理失败 411 `onError(-1,"消息预处理失败")` |
| 9 | 发出点 = IM 长连接（WS，非 HTTP） | URL `smali\lcf.smali:252` = `wss://api.hellotalk8.com/ht_im/sock`（可被 `mv40` 配置覆盖；实测 `wss://api-cn.hellotalk8.com/ht_im/sock?userid=<uid>`）；WS 客户端 `smali_classes3\nu50.smali`（2516-2552 建连 `ush.newWebSocketCall`，452 `e(Lnu50;[B)` 发二进制帧；握手后帧体用 `session_key` 加密） |

## 2. 错误码 18 与「今日打招呼次数已用完」文案链

- `smali_classes7\b7z.smali:102`（`const/16 v8, 0x12` = 18）、`:106`（`0x7f141131`）、`:116-120` `SimpleToast` 弹文案、`:125-184` 弹窗 `popup_name="used up Hi"`；`:339/:393` 在 `r()` 里同一判定；`b7z.smali:6` `.implements Lncf;`（IM 发送回调）。
- 另一支（首次聊天/打招呼额度付墙）：`smali_classes6\iqs.smali:124-147`（`code==18` → 0x7f141131，否则 0x7f14113a）+ `:152-429`（`f58.a()`(chatCount)==1 && 非 VIP+ → `vpu(19,"New Chat Quota Exhausted")` 付墙）；Java 对照 `artifacts\jadx6\sources\defpackage\wzo.java:89-145`；同逻辑再现于 `smali_classes6\r1.smali:5135/5144/5253`。
- 文案表：`smali_classes3\rdy.smali:2446-2460` `Pair("Message exceeded the upper limit", 0x7f141131)`；id 定义 `artifacts\apktool\res\values\public.xml:29430`；中文 `res\values-zh-rCN\strings.xml:3906`；另一条 `0x7f14113a`=`message_sending_failed`。
- 消费方：`smali_classes5\bmi.smali:1423`（按错误类型 0x4d=77 查 `Lrdy;->a` 映射）→ 该 key 是**服务端下发的英文 message key**，客户端只做本地化。

## 3. 本地计数/拦截（结论：无）

- 全量扫描（82,734 个 .smali）关键词 `freeSayHiTimes|free_sayhi_times|say_hi_state_data|greet_count|greetCount|greetLimit|dailyGreet|SAY_HI_LIMIT|MAX_SAY_HI|noVipHasGreet`：
  仅命中 bean 定义与本机缓存，**无阈值比较**。唯一 `noVipHasGreet` 命中是日志串 `smali_classes6\com\hellotalk\search\v3\ui\SearchNearbyV3Fragment.smali:2725`。
- `free_sayhi_times` 只作为服务端下发字段：`jadx6\…\defpackage\bip.java:35`、`bzd.java:17`（`@pew("free_sayhi_times")`）。
- 唯一"运算"是本地展示减一：`smali_classes6\r1.smali:4394/4487` 日志 `decrementFreeSayHiTimes(nearby|gender)`，`:4462-4478` `if (x>0) bzd.c(x-1)` —— 只减显示值，**没有 `<=0 → return/拦发送`**。
- 免费次数文案纯 UI：`smali_classes6\com\hellotalk\search\widget\NearbyNewCardView.smali:606`（0x7f140aa7「你有1次免费打招呼机会」）、`:709`（0x7f140f63「剩余0次…」）。
- `say_hi_state_data<uid>`（`jadx6\…\defpackage\qtv.java:76/95`，smali `qtv.smali:294/543`）+ `have_say_hi`/`say_hi_in_exposure`（`vev.java:20-26`）＝已打招呼对象的**去重/展示标记**（`r1.smali:4639` 在成功路径写缓存），不是计数闸门。

## 4. 接口清单

- WS：`wss://api.hellotalk8.com/ht_im/sock`（`smali\lcf.smali:252`；实测 api-cn 域名）；打招呼 = C2C 消息 `msgType="new_sticker"` + `IMNewStickerBean{productId:1,imageId:11,helloMsg:1}`。
- HTTP：`/config-center/v1/greeting_content`（`jadx6\…\defpackage\ii6.java:24`，`@lsd`）、`/ai-hub/v1/chat_assist/sayhi/generate`（`woe.java:11`，AI 生成招呼语，与计数无关）。
- 服务端下发字段：`free_sayhi_times`（bip/bzd）、`say_hi_uids`/`say_hi_users`（`jadx6\…\lzb.java:90/95`，曝光详情）、`gender_sayhi_info`（`uyv.java:39`）。
- 错误码线索：IM 发送失败码 18；文案键 `Message exceeded the upper limit`；`message_sending_failed`。

## 5. libapp.so / Dart 线索

- 基础包 `samples\xapk\com.hellotalk.apk` **无 `lib/`**（0 个 .so）；native 在 split `samples\xapk\config.arm64_v8a.apk`。
- `lib/arm64-v8a/libapp.so`（36.4 MB）内**没有** `ht_im/sock`、`say_hi`/`sayHi`、`session_key`；只有 `greeting_card.dart`、`greetingPartHello`、`send greeting response` → 属 AiGrammar/日语引导的问候卡片，与 IM 打招呼计数无关。
- 因此打招呼链路完全在 Java/Kotlin（classes*.dex），不在 Flutter/Dart 层。

## 6. 不确定项与最小验证实验

1. 错误码 18 的字节级来源未还原（WS 帧体加密，见 `<WORKDIR>\docs\交接文档.md:53`）。验证：gadget 版上 hook `Lncf;->onError(ILjava/lang/String;)V`（实现在 `b7z`）与 `nu50.e(Lnu50;[B)`，第 11 次点击时看 (code,msg) 与上行帧是否真的发出 → 若"请求已发出且服务端回 18"即为服务端计数铁证。
2. `lty.k()`(`f58.a()` = chatCount) 的取值来源未定（付墙资格判据，属 15 chats/day 新会话额度），与打招呼次数是两个量，勿混。
3. 未运行时确认 10/日 的具体阈值下发字段；静态只确认客户端未硬编码 10（`const/16 … 0xa` 未出现在打招呼路径）。
