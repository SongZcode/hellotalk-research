# VIP 体验卡 / 激励视频模块分析（2026-10-12）

> 结论：**体验卡机制需要真实赠卡（VIP 好友赠送）；伪造 card_id / record_id 一律被拒。**
> 激励视频的「领取」接口在加密通道后面（`ht/encbin`）。

---

## 1. 接口全清单（frida 反射 Retrofit 接口 `f7s` 所得）

| 方法 | 接口 | 请求模型 | 字段 |
|---|---|---|---|
| a | `/member_privilege_center/v3/vip_experience_card/incentive_video_watch_quota` | `khh` | `user_id`, `scenes` |
| b | `.../vip_experience_card/query_user_record` | `o930` | (空) |
| c | `.../v3/selfie/config` | `g8w` | — |
| d | `.../vip_experience_card/query_user_feature_right` | `hct` | `card_type`, `feature_id`, `scene_id`, `user_id` |
| e | `.../vip_experience_card/receive_friend_sent_card` | `k930` | `record_id` |
| **f** | **`.../vip_experience_card/incentive_video_obtain_right`** | `yb30` | `feature_id`, `incr_times`, `scene_id`, `user_id`, `advertising_id` — **标 `ht-content-type: ht/encbin`（加密）** |
| g | `.../vip_experience_card/batch_query_receive_status` | `m930` | `record_ids` |
| h | `.../vip_experience_card/write_off_card` | `yb30` | 同 f（明文） |
| i | `.../vip_experience_card/user_use_card` | `eh20` | `card_id`, `feature_id`, `scene_id`, `user_id`, `version` |

其余相关：`vip_trial/{banner,popup,card_detail,unlock}`、`vip_privilege/{receive,course_win}`、
`v1/activity/boost_first_purchase/{info,claim}`、`v1/user/resubscribe`。

**注意：没有「发卡」HTTP 接口** → 送卡走 IM 礼物消息（`TalkGiftVIPExperienceCardDialog` / `startGiftVipCardAnim`）。

## 2. 反射方法（可复用）

```powershell
$py='<WORKDIR>\tools\venv\Scripts\python.exe'
& $py -u tools\fx_reflect.py iface f7s      # 读接口 → URL + 参数模型
& $py -u tools\fx_reflect.py fields yb30    # 读模型字段名（@pew 注解）
$py -W ignore tools\show_f7s.py             # 汇总表
```
原理：frida + frida-java-bridge，`Java.use(cls).class.getDeclaredMethods()/getDeclaredFields()`
+ 读注解 → 直接拿到 Retrofit 的 URL 与字段名，**比扫 smali 快上百倍**。

## 3. 账号实测状态

| 项 | 值 |
|---|---|
| 卡记录 `query_user_record` | `{"id":"0000...","content":{"cards":null},"vip_status":0,"feature_used_counts":[]}` → **无卡** |
| 试用 `vip_trial/banner` / `popup` | `null` → **无资格** |
| 激励视频位 | **20 个**（scene 20000/30000/40000/60000/70000/70001/70002 × feature 00001~00006），`today_watched` 全 0 |

## 4. 授权强度测试（全被拒）

| 试探 | 结果 |
|---|---|
| `user_use_card` + card_id=`000000000000000000000000` | `100002 bad request` |
| `user_use_card` + 随机 card_id | `100002 bad request` |
| `receive_friend_sent_card` + 占位 record_id | `100002 bad request` |
| `write_off_card` + `incr_times=1`（无卡） | 返回 ok 但 `left_timeleft` 仍为 0 → **不发权益** |
| 改 `user_id` 查他人权益 | `100002 bad request` → **绑定认证用户** |
| `incentive_video_obtain_right` 直接调 | `400 missing or malformed encryption public key` → **强制加密** |

## 5. 机制还原（UI 文案 + 接口语义）

```
非VIP用户  ──看激励视频──▶ 获得体验卡/次数（incentive_video_obtain_right，加密接口）
VIP会员    ──每月3张──▶ 赠送好友体验卡（走 IM 礼物消息）
好友(非VIP) ──领取──▶ receive_friend_sent_card(record_id) ──▶ user_use_card(card_id) 解锁一项特权
                                                              └─ 可选「更多语伴沟通」= 陌生人聊天次数
```

「更多语伴沟通」正是额度受限那一项 → **体验卡是官方给的免费额度路径**，但需要：
① 看到激励视频入口（非会员状态下才有），或 ② 有 VIP 好友送卡。

## 6. 副作用记录：补丁会让非会员入口消失

把 VIP 状态还原成服务端真实值（frida 挂钩 `ia30.i/n/r`）后，聊天页文案由
`VIP每日可发送25个陌生人聊天…` 变为 `非VIP每日可发送10个陌生人聊天…` →
**客户端"自称 VIP"会隐藏所有面向非会员的促活入口（含激励视频）**。
