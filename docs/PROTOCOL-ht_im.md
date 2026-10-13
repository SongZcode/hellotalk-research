# HelloTalk `ht_im/sock` 协议解析（2026-10-11 突破）

> **结论先行**：握手之后的帧 **不是加密**，而是 **zlib 压缩的 JSON**（外加少量二进制控制帧）。
> 之前的「应用层加密 / 需要 session_key 解密」结论作废 —— 抓包即可读全协议，不需要 frida。

---

## 1. 帧结构（20 字节头，128+ 帧实测）

```
magic(4) | opcode(4) | uid(8, LE) | body_len(4, LE) | body
 0..3      4..7        8..15          16..19            20..
```

| 字段 | 说明 |
|---|---|
| magic | `f0 04 00 01` 客户端上行 / `f1 04 00 01` 服务端下行 / `f5 04 01 00` 服务端推送 |
| opcode | `[type, marker, counter_lo, counter_hi]`，见 §2 |
| uid | 账号 ID（小端 u64，例：<UID>） |
| body_len | 帧体字节数（**在 offset 16**，不是 20；老版本工具在这里错过一次） |
| body | 明文 JSON（握手）或 zlib 压缩 JSON（业务帧，`78 9c` 开头，尾部 4B 是 adler32）或二进制控制帧 |

## 2. opcode 表（从 4 个 dump、128 帧统计得出，100% 一致）

| type | marker | 方向 | 含义 | body |
|---|---|---|---|---|
| 0x25 | 0x10 | UP | **握手**（jwt + 设备信息） | 明文 JSON |
| 0x26 | 0x10 | DN | 握手应答 | 明文 JSON：`status/msg/data{session_id,session_key,server_ts,translate_api_ts,area_code,wns_config_ts,jwt}` |
| 0x0F | 0x75 | UP | 拉消息 | `{"last_id":0}` |
| 0x10 | 0x75 | DN | 拉消息应答 | `{"code":0,...,"msgs":...}` |
| 0x45 | 0x40 | UP | 拉收件箱/包列表 | `{"last_id":0}` |
| 0x46 | 0x40 | DN | 收件箱应答 | `{"code":0,...,"packet_list":[]}` |
| 0x01 | 0x40 | UP | **发消息（含打招呼）** | 见 §3 |
| 0x02 | 0x40 | DN | 发消息应答 | `{code,msg,data{mid,msg_id,send_count,recv_count,remaining_new_chat_count,server_time_ns}}` |
| 0x01 | 0x90 | UP | 发消息后确认 | 8B：`uid + 计数器` |
| 0x02 | 0x90 | DN | 确认应答 | 13B：`服务器时间(4B) + 8B 0` |
| 0x21 | 0x20 | UP | 轨迹/会话心跳 | 8B：`uid + 自增计数器` |
| 0x22 | 0x20 | DN | 轨迹应答 | 35B 位图 |
| 0x15 | 0x40 | UP | 上报消息 ID | 36B uuid + 状态 |
| 0x16 | 0x40 | DN | 上报应答 | 空 |
| 0x17 | 0x40 | UP | 状态位（前台/在线） | 2B |
| 0x18 | 0x40 | DN | 状态应答 | 空 |
| 0x01 | 0x61 | DN | 服务端推送 | 20B |
| 0x03 | 0x61 | DN | 服务端推送 | 60B |

> **marker 与 type 绑定**（实测）：`0x10`=握手、`0x20`=轨迹、`0x40`=收件箱/发送/上报、`0x75`=消息拉取、`0x90`=发送确认、`0x61`=推送。
> 写错 marker 的代价：服务端**原样 echo 你的 opcode + 4 字节 0**（=拒绝），连接随后被关。

## 3. 发送帧（打招呼走这条）

`op=01404309`（UP，zlib JSON，实测 309 字节）：
```json
{"msg":{"msg_id":"<uuid4>","send_ts":<毫秒时间戳>,"msg_type":"text",
  "text":{"reportIndex":0,"reportText":"","text":"OK"},
  "chat_follow_notify":0,"correction_gift_notify":0,"cost_diamonds":0,
  "pay_chat_cost_virtual_val":0,"pay_chat_switch":0,"recv_diamonds":0,
  "source":"Chat List","to_payer":false,"valid_time":0,"bubble":{"id":0},
  "from_nickname":"Sz","from_profile_ts":1776434582},
 "version":394260,"client_lang":"Chinese"}
```
服务端应答 `op=02404309`：
```json
{"code":0,"msg":"ok","data":{"mid":"6acb897f8f9f0f38274d6fd2","msg_id":"<原 uuid>",
  "send_count":6,"recv_count":3,"remaining_new_chat_count":-1,
  "server_time_ns":1791723903568967404}}
```

### 打招呼（new_sticker）—— 实测原始帧（2026-10-11 22:22:15）

**客户端上行 `op=0140d81a`（459 字节 WS 帧，zlib JSON，无 to_uid 字段）**：
```json
{"msg":{"msg_id":"eb7eb164-fd64-472f-acb0-90d2d31b7ce7","send_ts":1791728535001,
  "msg_type":"new_sticker",
  "new_sticker":{"hasStartedAnim":false,"hello_msg":1,"image_id":11,
    "image_url":"https://ali-global-cdn.hellotalk8.com/prod/application/attachment/1e7ff6ec65b6c6be8aac9d8ff5f2f967.webp",
    "product_id":1},
  "chat_follow_notify":0,"correction_gift_notify":0,"cost_diamonds":0,
  "pay_chat_cost_virtual_val":0,"pay_chat_switch":0,"recv_diamonds":0,
  "source":"All Hand","sub_source":"en","to_payer":false,"valid_time":0,
  "bubble":{"id":0},"from_nickname":"Sz","from_profile_ts":1776434582,
  "ext":"{\"trace_id\":\"61fa0809a94eacf9c5ba6f48886b4241\"}"},
 "version":394260,"client_lang":"Chinese"}
```

**服务端应答 `op=0240d81a`（204 字节）**：
```json
{"code":100002,"msg":"bad request","data":{
  "mid":"6acb9b9729cce7d0cf416d92","msg_id":"eb7eb164-fd64-472f-acb0-90d2d31b7ce7",
  "send_count":0,"recv_count":0,
  "remaining_new_chat_count":0,
  "server_time_ns":1791728535127974341,
  "notice_type":18}}
```

### 🎯 结论（判定闭环，证据充分）

| 问题 | 答案 | 证据 |
|---|---|---|
| 第 11 次打招呼客户端有没有发请求？ | **发了** | `op=0140` + `msg_type=new_sticker` 完整帧在抓包里 |
| 客户端有本地计数拦截吗？ | **没有** | 请求照发，客户端只处理应答 |
| 拦截在哪一层？ | **服务端** | 应答 `code:100002, msg:"bad request"` |
| 客户端凭什么显示「今日打招呼次数已用完」？ | **`data.notice_type = 18`** | 对应 `b7z.smali:102(0x12)` → `rdy.smali:2446` key → `message_exceeded_the_upper_limit` |
| 配额字段 | **`remaining_new_chat_count: 0`** | 普通文本消息应答里是 `-1`（不限），打招呼超限时是 `0` |
| 消息投递了吗？ | **没有** | `send_count: 0, recv_count: 0` |
| 之后发生什么？ | 客户端埋点 `PayFlow / step: enter_vip_shop` | 确认跳 VIP 付费墙 |

**字段命名注意**：`new_sticker` 内部是 **snake_case**（`hello_msg` / `image_id` / `image_url` / `product_id`），
顶层 `msg_type` 为字符串 `"new_sticker"`；打招呼记 `source: "All Hand"`（普通聊天消息是 `"Chat List"`）。

### 配额来源实验（2026-10-11 22:27，`tools/quota_probe.py`）

| 实验 | 做法 | 结果 | 说明 |
|---|---|---|---|
| A 基线 | 原始 device_id + `source:"All Hand"` | 应答 `op=0240`，body 12B = **u32 357** | 见下「357 的含义」 |
| B 轮换设备 | `device_id` 换成随机值 | **握手就被拒**：`{"status":105,"msg":"sessionid not match device"}` | 服务端把会话绑定到设备，**轮换 device_id 无效** |
| C 换入口 | `source:"Chat List"` | 同样 357 | 缺会话上下文时一律 357 |
| D 换入口 | `source:"Nearby"` | 同样 357 | 同上 |

**357 的含义**：非 App 会话（没有真实聊天上下文/目标）时，发送帧一律得到 12 字节二进制应答
`65 01 00 00 00 00 00 00 00 00 00 00`（前 4 字节小端 = 357）。
⇒ **发送必须有服务端认可的会话上下文**（App 通过开聊天/开资料页时建立，可能走 HTTP，所以纯协议复刻需要先解出这一步）。

**已确认**：`-1`（不限）只出现在**已有会话**的消息上；`0` + `notice_type:18` 出现在**发起新会话**的打招呼上
⇒ 限制只作用于「发起新会话」，已有会话里聊天不限。

**未解（下一步）**：发送帧里**没有 `to_uid`**，目标路由靠什么？候选：连接态（此前打开的会话）、
opcode 计数字段、或 HTTP 侧会话。若要纯协议复刻打招呼，需先解出这一点。

### 帧复刻精度（已做到字节级一致）

客户端的 JSON 序列化方式（实测反推）：
- **紧凑分隔符**：`{"a":1,"b":2}`（无空格）
- **斜杠转义**：`/` → `\/`（`json.dumps` 默认不转义，必须手动替换）

验证：用 `tools/ht_frame.py` 的 `dumps_ht()` + `zlib.compress(level 6)` 复刻打招呼帧：
```
复刻帧 len=459  ←→ 抓包实测 459
帧头 f0040001 0140d81a 02d4f90900000000 b7010000
     magic    opcode   uid=<UID>    bodylen=439（压缩体）
解回 JSON 与原始对象完全相同 ✅
```
⇒ 现在可以**逐字节复刻任意帧**（`tools/verify_ht_frame.py` 可复验）。

**静态分析对照**（历史记录，`docs/archive/codex/T1-打招呼判定链-sub.md`）：
点击 → `z2h.R0` → `klz.smali:2867` 构造 `IMNewStickerBean{productId=1,imageId=11,helloMsg=1}` → IM WS；
客户端 82734 个 smali 全量扫描无阈值比较 → 无本地闸门（与实测一致）。

## 4. 连接要求（漏一个就静默失败）

1. URL：`wss://api-cn.hellotalk8.com/ht_im/sock?userid=<uid>`
2. 升级请求头必须带（抓包实测）：
   `x-ht-token: Bearer <JWT>`、`x-ht-did`、`x-ht-uid`、`X-Ht-Channel: google`、`X-Ht-Build: 11674`、
   `x-ht-device`、`x-ht-version: 6.4.20`、`x-ht-os-version: 16`、`x-ht-tzid: Asia/Shanghai`、`devMode: false`
   （`x-ht-token` 里的 JWT 与握手帧里的 JWT **是同一个**）
3. 首帧 = 握手帧：**明文 JSON，不要压缩**，20 字节头 + 702 字节 body
4. 连上后固定动作：`pull_msg` → `pull_inbox` → `trace`（顺序/内容见 §2；本客户端已实现）
5. 同一账号只认当前活跃会话（App 在线上时，第三方连接的后续帧可能被丢）

## 5. 工具清单（`<WORKDIR>\tools`）

| 工具 | 用途 |
|---|---|
| `ht_frame.py` | **协议库**：帧编解码、opcode/marker 表、`body_off`/`body_of`/`parse`/`pack`/`pack_json` |
| `ht_client.py` | **独立协议客户端**：`login` / `session`（握手+固定动作）/ `inbox` / `pull` / `send` |
| `ht_live.py` | mitmdump addon：实时把 WS 帧解成明文写 `api.log` + `ws.jsonl` |
| `ht_dump.py` | 离线解 dump 里的全部帧为明文（UTF-8 安全，可 `--out` 落文件） |
| `ht_ops.py` | 从 dump 统计 `(type, marker)` 表 |
| `ht_report.py` / `ht_bin.py` | 帧统计 / 二进制帧探查 |
| `extract_jwt.py` | 从 dump 抽最新 JWT → `artifacts/mitm/jwt.txt` |
| `extract_hello.py` | 抽「原样 hello 模板」（字段不多不少） |
| `ht_headers.py` | 抽 WS 升级请求头 → `ws_headers.json` |
| `save_hello_orig.py` | 存一条原始握手帧 → `hello_orig.bin`（对照用） |
| `probe_*.py` / `replay_session.py` | 一组对照实验脚本（原样重放 / marker 扫描 / 发送探测） |
| `greet_test.py` | 打招呼实验器（`self-test` / `scan` / `greet` / `greet-many`） |

**典型用法**
```powershell
$py='<WORKDIR>\tools\venv\Scripts\python.exe'
$env:PYTHONIOENCODING='utf-8'
& $py -u tools\ht_client.py login
& $py -u tools\greet_test.py self-test
& $py -W ignore tools\ht_dump.py artifacts\mitm\flows_run1.mitm --out artifacts\mitm\run1.dec.txt
```

## 6. 已打通的验证

- ✅ 握手（原样重放 / 用最新 JWT 重放都能 406B 应答，`session_key=<SESSION_KEY>`）
- ✅ `pull_inbox` / `pull_msg` / `trace` 均能拿到正常应答（复用抓包帧或自造帧皆可，marker 必须对）
- ✅ 发送帧（`0140`）服务端应答；发送确认（`0190`）返回服务器时间戳
- ⏳ 打招呼 `new_sticker` 帧：**待抓到 App 的真实帧**（见 §7）

## 7. 下一步（打招呼配额判定）

**A. 抓真实打招呼帧（当前首选）**
1. mitmdump 已按 `-s tools/ht_live.py -w artifacts/mitm/flows_greet.mitm` 运行，手机代理已指向 PC
2. 手机 App 里点一次「打招呼」（朋友/陌生人聊天页右上角或找语伴卡片）
3. 看 `api.log` 里是否出现 `op=0140` + `new_sticker` 的 UP 帧
4. 拿到真实帧后：用 `greet_test.py` 复刻 + 换 uid 连发，观察第 N 次的应答码（18 = 超限）

**B. 若页面因 HTTPS 证书失败打不开**（已知：`Trust anchor for certification path not found`）
- 症状：App 部分页面报「网络出错」，HTTPS API 请求被 cronet 校验挡掉
- 绕过：hook cronet/Conscrypt 证书校验（需 frida 会话可用）；或改抓 `pull_msg` 里的 new_sticker 推送

**C. 纯协议侧（不依赖 App 操作）**
- 用 `pull_msg` 拉取别人的打招呼（`new_sticker` 消息）验证字段格式
- 找到目标 uid 后直接发 `new_sticker` 帧，观察服务端返回的配额错误码
