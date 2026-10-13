# APK 静态分析概览

本页根据本地 VIP 研究项目的 `docs/STATUS.md`、`recon/vip_classes.txt` 和 `recon/dex_vip_strings.txt` 整理，补充此前公开仓库没有汇总的静态线索。原记录针对 HelloTalk Android 6.4.20，不包含原 APK、反编译源码或个人工作路径。

## 样本记录

原状态记录记载 base APK 约 139 MB、12,366 个 ZIP 条目、8 个主 DEX 及其他 SDK DEX。不同扫描脚本的选取范围不同：ASCII 扫描记录为 9 个 DEX，不能直接把它等同于主 DEX 数量。

这些数字来自历史记录，本次没有对原 APK 重跑清点。读者可用 `apk_inventory.py` 检查自己的样本，版本、拆分包和 SDK 内容可能不同。

## 候选类

以下类名和方法名可作为在自己样本中定位实现的线索，不代表这些类都能决定服务端权益。

| 方向 | 原记录中的类 | 相关方法 |
| --- | --- | --- |
| 用户基本资料 | `com.hellotalk.api.user.api.model.UserBaseInfo` | `getVipType`、`getVipExpireTime` |
| 用户扩展资料 | `com.hellotalk.api.user.api.model.UserExtraInfo` | `isVipPlus` |
| 权益数据 | `UserPermission`、`UserInfo`、`HTIMUser` | `getPrivileges` |
| 界面展示 | `VipImageView`、`VIPSection` | `getVipType`、`getPrivileges` |
| 群成员资料 | `GroupMember`、`GroupMemberInfoExt`、`HTGroupInfo` | `getVipType`、`isVip`、`hasPrivilege` |
| 混淆类 | `Lcyv;`、`Lqtv;`、`Ltqv;` | `isVip` |

原候选表共列出 13 个类。混淆类名及 DEX 分布只对原样本有意义，不应写成跨版本固定接口。

## 字符串线索

原 ASCII 扫描记录的命中计数包括：`Subscription` 192、`BillingClient` 52、`isVip` 46、`SkuDetails` 24、`VipInfo` 16、`checkVip` 12。

这些是特定扫描规则下的文本片段命中，不是 API 调用次数、用户数据或完整字符串池统计。搜索到关键字只能提供调查线索，不能证明相关路径在运行时被调用。

## 证据边界

静态字段与本地界面状态不能单独证明服务端授权结果。有关权益和支付链路的讨论应结合 [权益卡记录](VIP-CARD-MODULE.md)、[支付链路记录](VIP-PAYMENT-CHAIN.md) 及对应版本的实验条件。

早期记录中的个人环境、在途任务、设备状态及修改客户端的操作计划没有移入本页；它们不是公共工具的使用前提。
