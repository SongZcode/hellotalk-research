# 贡献指南

欢迎提交文档修正、离线分析工具改进和带明确实验条件的研究记录。

## 提交内容

- 说明解决的问题、涉及的文件，以及验证方式。
- 新结论写明样本版本、数据来源、实验条件，并区分观察、推测和已验证结论。
- 新工具优先接受命令行路径参数，避免写死个人磁盘目录或设备标识。
- 保留实验脚本时，在工具说明中明确其依赖和可用状态。

## 本地验证

```sh
python examples/offline_frame.py
python -m unittest discover -s tests -v
python -m py_compile examples/offline_frame.py tools/ht_frame.py
```

测试覆盖合成帧的载荷往返、长度与压缩边界，以及临时 ZIP 的 APK 清点和 ASCII 片段扫描，不代表整个协议实现或全部实验脚本已通过测试。CI 使用 Windows/Linux、Python 3.10/3.13，无需安装第三方分析依赖。

涉及本地抓包工具时，使用合成或经过脱敏的样本验证；请在 Pull Request 中记录命令、Python 版本和第三方依赖版本。

## 数据与许可

不要提交账号凭据、真实请求头、聊天记录、个人标识、抓包原件、第三方 APK 或签名密钥。`.gitignore` 用于减少误提交，并不能替代人工检查。

贡献适用仓库现有 [LICENSE](LICENSE)。该许可限制商业使用，请勿将其描述为 MIT 或其他宽松开源许可。
