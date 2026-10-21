# Security policy / 安全说明

这是离线资产处理工具，不是处理不可信输入的安全沙箱。

- 仅使用有权处理的 GLB、引导 JSON 和 `.blend` 文件。
- 处理来源不明的文件时，使用更新的 Blender 和依赖、隔离环境、资源限制及 `--disable-autoexec`。
- 不以管理员权限运行脚本。极大网格或过小 voxel pitch 可能耗尽内存和运行时间。
- 不提交 `.env`、访问令牌、用户模型、个人路径或含敏感资产的日志。
- 程序化 smoke test 只验证有限场景，不能证明所有模型安全或艺术质量合格。

## 报告漏洞

如仓库启用 GitHub Private Vulnerability Reporting，请使用 Security → Report a vulnerability。
若该入口不可用，创建不含利用细节、秘密或私人素材的 issue，请维护者提供私密联系渠道。
不要在公开 issue 或 PR 中披露敏感内容；目前不承诺修复 SLA。

维护主要面向默认分支的最新代码。提交安全修复时加入回归测试及受影响版本说明。
