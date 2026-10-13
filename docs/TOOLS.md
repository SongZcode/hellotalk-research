# 工具说明

本仓库包含可执行的离线模块、依赖本地样本的分析工具，以及保留供阅读的实验脚本。语法可解析不代表脚本可直接运行或在真实环境中有效。

## 离线示例

```sh
python examples/offline_frame.py
```

只依赖 Python 标准库，使用合成数据验证 `ht_frame.py` 的压缩与明文 JSON 载荷往返。不涉及网络、账号或设备。

`ht_frame.py` 可以读取本地帧文件：

```sh
python tools/ht_frame.py path/to/frame.bin
```

它是研究实现：部分头字段输出仍沿用早期命名，没有完整验证长度、magic 或压缩载荷大小。请勿将其当作面向不可信输入的完整协议校验器。

## 本地抓包分析

下列工具读取你提供的本地 mitmproxy 文件。可先创建虚拟环境并安装依赖：

```sh
python -m venv .venv
```

Windows PowerShell 使用 `.\.venv\Scripts\Activate.ps1`；其他环境使用对应的虚拟环境激活方式。然后执行：

```sh
python -m pip install mitmproxy
python tools/ws_decode.py path/to/capture.mitm --tail 20
python tools/ht_report.py path/to/capture.mitm
python tools/ht_bin.py path/to/capture.mitm
```

以上命令根据现有脚本入口整理，需要有效的本地样本和兼容的 mitmproxy 版本。本次整理未执行真实抓包分析，不保证所有历史 dump 格式均兼容。

`ws_decode.py` 包含历史探索分支，其 `split_frames` 尚未实现；不要将它理解为完整 TCP 流重组工具。

## 实验脚本

`dex_*`、`scan_*`、`ui_*`、`fx_*`、探测与重放脚本中的部分文件写死了 `<WORKDIR>`、`<WORKDIR2>` 或外部工具路径。它们保留的是研究过程，需要自行检查依赖与输入，不能按整个目录批量执行。

本次静态审阅检查了 `tools/` 内 93 个 Python 文件，其中 80 个可通过语法解析；以下 13 个因脱敏占位符等内容存在语法错误：

| 文件 | 状态 |
| --- | --- |
| `card_probe.py`、`card_probe2.py`、`card_probe3.py`、`card_probe4.py`、`card_probe5.py` | 实验模板 |
| `ht_client.py` | 脱敏后的客户端研究源码，不能直接运行 |
| `probe_fair.py`、`probe_min.py`、`probe_sweep.py`、`probe_verbatim.py` | 实验模板 |
| `replay_session.py`、`ws_replay_probe.py` | 实验模板 |
| `verify_ht_frame.py` | 依赖真实证据文件与脱敏 UID，不能作为公共自检入口 |

不在这个列表中的脚本也可能缺少依赖或输入文件。本次没有恢复真实标识、凭据或在线重放流程。

## 动态观测源码

`tools/agent/` 保存动态观测源码和 Node.js 构建依赖，构建产物未入库。历史环境使用 Frida 17、frida-java-bridge 和 esbuild，具体环境参考对应分析文档。

这部分不属于离线快速开始，也没有在本次文档整理中进行设备验证。请结合目标版本与现有 LICENSE 阅读其用途和适用范围。
