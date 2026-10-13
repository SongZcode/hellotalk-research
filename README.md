# HelloTalk Research

HelloTalk Android 客户端与通信协议的研究资料和分析工具，面向移动安全学习、协议分析和客户端实现研究。

现有记录以 **HelloTalk Android 6.4.20** 为主要样本。分析结果反映记录中的版本和测试条件，不代表所有版本或所有服务端路径都具有相同行为。本项目与 HelloTalk 官方无关联。

## 从哪里开始

| 你想做什么 | 入口 |
| --- | --- |
| 先了解项目内容 | [文档导航](docs/README.md) |
| 不连接设备或服务，运行一个示例 | [离线帧示例](#快速开始) |
| 分析已有的本地抓包文件 | [工具说明](docs/TOOLS.md#本地抓包分析) |
| 了解 IM 帧结构和分析结果 | [IM 协议分析](docs/PROTOCOL-ht_im.md) |
| 查阅客户端、授权与支付链路资料 | [文档导航](docs/README.md#分析文档) |
| 修改工具或补充研究记录 | [贡献指南](CONTRIBUTING.md) |

## 项目内容

- IM 帧结构、opcode 与压缩载荷的分析记录。
- HTTP 应用层数据处理、客户端观测点及测试环境记录。
- 会员权益、额度和支付链路的客户端与服务端边界分析。
- 本地流量分析脚本、帧编解码模块，以及保留供阅读的实验脚本。

**工具的可用程度不同。** 部分实验脚本仍依赖个人测试环境，13 个 Python 脚本因脱敏占位符无法直接通过语法检查；请先查看 [工具说明](docs/TOOLS.md)，不要把整个 `tools/` 目录当作已发布的可执行工具套件。

## 快速开始

需要 Python 3.10 或更新版本；本次离线验证使用 Python 3.13。下面的示例只用 Python 标准库，不需要账号、设备、APK、抓包文件或网络连接。

```sh
git clone https://github.com/SongZcode/hellotalk-research.git
cd hellotalk-research
python examples/offline_frame.py
```

示例使用虚构的 UID 和合成 JSON，调用已有的帧模块完成编码、解析和载荷往返检查。它不会连接 HelloTalk 或发送消息；成功时输出 `Offline round-trip: OK`。

要查看自己准备的本地帧文件，可以运行：

```sh
python tools/ht_frame.py path/to/frame.bin
```

现有解析器是研究实现，不能视为完整协议校验器。具体限制见 [工具说明](docs/TOOLS.md)。

## 目录结构

```text
examples/          可直接运行的合成数据示例
docs/              分析文档、文档导航和工具说明
docs/archive/      历史交接和阶段性研究记录
tools/             分析模块、抓包工具和实验脚本
tools/agent/       动态观测脚本源码及构建依赖
CONTRIBUTING.md    贡献和验证方法
LICENSE            研究用途许可
```

历史交接文档保留在 archive，便于追溯结论；其中的个人目录、设备状态和待办事项不是当前用户的安装要求。

## 适用范围

按现有记录，观察到的部分 IM 业务载荷是 zlib 压缩的 JSON；会员、额度和支付权益涉及服务端判定。更多证据与实验条件请阅读对应分析文档，不应把一次实验结果扩大为对所有接口的保证。

涉及真实样本、设备或账号的研究，须符合 [LICENSE](LICENSE) 的授权范围。不要提交真实令牌、会话信息、聊天内容、账号标识或第三方安装包。报告工具问题时，可优先提供合成或脱敏样本。

## 反馈

通过 [Issues](https://github.com/SongZcode/hellotalk-research/issues) 提交问题或建议，请说明工具名称、Python 和依赖版本、复现命令及经过脱敏的报错。欢迎提交文档修正与工具改进，流程见 [贡献指南](CONTRIBUTING.md)。

## 许可

本项目使用 [Research-Only License / 仅供学习研究许可](LICENSE)，包含非商业使用限制。源码公开，但该许可不等同于 MIT、Apache 等标准开源许可；使用和再分发请以 LICENSE 为准。
