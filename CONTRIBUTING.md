# Contributing / 参与贡献

感谢帮助改进非人形生物的开放动画工具链。

## 开始之前

- 查阅 README 的能力边界及 `references/quality-gates.md`。
- 先开 issue 描述可复现问题或目标；较大架构改动先讨论。
- 不要上传私有角色、客户素材、个人信息、凭据或没有再分发授权的模型。
- 最好用 `examples/make_tube.py` 生成的模型复现，或提供自己创作的最小样例生成脚本。

## 本地验证

```bash
python -m pip install -r requirements.txt
npm ci --ignore-scripts
python -m unittest discover -s tests -v
python examples/run_demo.py --output-dir temp_data/contribution --render
```

输出目录不得预先存在；重新运行时使用新目录，避免覆盖素材。

PR 应说明问题、实现方式、实际测试环境、已运行的检查及仍未覆盖的场景。
涉及绑定、导出和动画时，请附 glTF 校验结果和匿名化渲染审查结果。
数值阈值或测试失败不得通过删除检查、静默忽略参数来处理。

## 评审与版本

维护者人工评审 PR；自动化不代替合并决定。请保持改动聚焦，补回归测试，更新相关文档。
早期版本使用 `0.x` 版本号，发布说明应列出已验证环境、修复和已知限制。
不存在响应时间保证。

## 许可证与行为

提交贡献即表示你有权按本项目 MIT 许可证授权该贡献。
第三方代码必须注明来源和原许可证，不能仅因放入本仓库就重新授权。
讨论保持尊重、聚焦技术，不骚扰、不公开他人私人信息。
