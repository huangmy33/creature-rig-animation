# Creature Rig Animation

[English](#english) · [中文](#中文) · [MIT](LICENSE)

## 中文

把无骨骼、非人形生物的静态 GLB 转成可播放的骨骼动画。
面向触手、蛇、长尾和双翼等结构，提供引导点设计、距离蒙皮、程序化动作、
重新导入后的形变检查与多视角审查。既可作为独立命令行工具，也可让支持
本地 Skill 文件夹的 AI 编码助手读取 [SKILL.md](SKILL.md) 来执行。

**早期项目，不是“任意生物一键完美绑定”。不需要 API key，不依赖私有服务。**

### 主要能力

- 从管状网格提取体素骨架中心路径，生成带坐标约定的引导 JSON。
- 根据引导点建立骨骼；最多四骨骼影响、归一化距离权重，可按网格名称限定影响范围。
- 长链动作：`undulate` 蜿蜒、`probe` 探查、`slap` 抽击；标准命名双翼振翅。
- 对输出 GLB 重新导入，抽样检查顶点运动、非有限值、明显爆炸/塌缩、漂移和首尾循环差。
- 关键帧多视图渲染、接触表总览，以及 Khronos glTF Validator 校验。
- 纯程序生成示例模型、回归测试、GitHub Actions 自动化。

### 环境和安装

需要 Python 3.11+、Node.js 20+ 和单独安装的 Blender。本地实际验证环境为
macOS、Python 3.14.7、Node.js 22.23.2、Blender 5.2.1。
代码包含旧版及新版分层 Action 的兼容层；未实测的版本不视为已保证支持。
CI 的 Blender 版本以每次运行日志为准，渲染需要可用的图形环境。

```bash
git clone https://github.com/huangmy33/creature-rig-animation.git
cd creature-rig-animation
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm ci --ignore-scripts
```

Windows PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活环境。
`package.json` 中的 `private: true` 只防止误发布到 npm，不表示 GitHub 仓库私有。
Python 依赖声明兼容范围，npm 校验器及间接依赖通过 lockfile 固定。

### 一条命令验证完整流程

```bash
python examples/run_demo.py --output-dir temp_data/first-run --render
```

没有图形环境时去掉 `--render`，仍会执行绑定、三种长链动画、重新导入形变检查
和 glTF 校验。Blender 不在 PATH 时使用 `--blender /path/to/blender` 指定可执行文件。

每次必须选择尚不存在的输出目录，脚本不会清空或覆盖旧素材。
成功后查看输出目录中的 `smoke-results.json`、各阶段日志、`undulate.glb`、
`probe.glb`、`slap.glb`、`guides-overlay.png` 和 `review/contact-sheets/`。
GLB 可用 Blender 的 glTF 导入功能打开；`.blend` 是中间绑定工程。
示例管状体由本仓库代码生成，可按 MIT 使用，不涉及第三方角色素材。

### 处理自己的模型

完整步骤和可复制命令见 [SKILL.md](SKILL.md)。建议先阅读：

- [骨架引导与坐标约定](references/guide-design.md)
- [动作设计与调参](references/motion-design.md)
- [质量门槛和视觉审查](references/quality-gates.md)

所有 Blender 批处理加 `--disable-autoexec --python-exit-code 1`。
不要把私有模型、渲染图、`.blend`、访问凭据或完整本地路径提交进源码。
`temp_data/`、虚拟环境和生成资产默认由 `.gitignore` 排除。

### 已知限制

- 长链提取依赖几何尺度和 `--pitch`；角、须、交叉或离散部件需要人工修正引导。
- 距离蒙皮不是语义权重求解器；相邻肢体、翼膜和复杂关节可能需要人工修权重。
- 数值检查是抽样启发式，不证明没有穿插，也不能替代艺术审查。
- 当前程序化端到端样例覆盖三种长链动作；双翼与复杂多部件角色仍需真实资产回归。
- 双翼脚本目前仅支持 `--cycles 1`；不支持的值会明确报错。循环长链要求正整数周期。
- Blender 5.2.1 的动画导出日志会报告解除网格父级的骨架选择提示；脚本限定单骨架并复核 modifier，最终 GLB 独立校验应为零警告。原因和验证方法见质量门槛文档。
- 没有发布 Python/npm 包、下载遥测或大规模采用声明。

### 开发与协作

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts examples tests
node --check scripts/validate_glb.mjs
```

参见 [贡献指南](CONTRIBUTING.md)、[安全政策](SECURITY.md)、
[版本记录](CHANGELOG.md)、[第三方声明](THIRD_PARTY_NOTICES.md)。
问题与建议请使用仓库 Issues；提交 PR 时附复现方法及实际验证结果。
本仓库内容按 [MIT](LICENSE) 开放；Blender 和其他依赖保留各自许可证。
用户输入的模型仍受其自身授权约束。

## English

**Guide-driven rigging and procedural animation for non-humanoid GLB creatures.**
An early-stage, local-first toolkit for Blender users, technical artists and AI coding
agents. It is not a universal auto-rigger and does not require an API key.

The pipeline combines voxel centerline extraction, JSON bone guides, distance-based
skinning, chain/wing animation, re-imported deformation checks, multi-view rendering,
and Khronos glTF validation. Scene-node transforms and mesh instances are respected.

Install Python 3.11+, Node.js 20+ and Blender, create a virtual environment, then run:

```bash
python -m pip install -r requirements.txt
npm ci --ignore-scripts
python -m unittest discover -s tests -v
python examples/run_demo.py --output-dir temp_data/demo-en --render
```

Use a fresh output directory. Omit `--render` for a headless smoke test; supply
`--blender /path/to/blender` when needed. All example geometry is generated locally
from MIT-licensed source. Output logs, review sheets and animated GLBs remain in the
chosen directory. See [SKILL.md](SKILL.md) for the agent workflow and detailed commands.

Local end-to-end verification uses Blender 5.2.1 on macOS. CI records its actual
Blender version. Compatibility helpers also cover legacy Action APIs, but untested
versions and complex production creatures are not guaranteed. The procedural smoke
test covers three chain profiles, not the wing/full-creature quality matrix.

Contributions should include reproducible fixtures, regression tests and honest
limitations. Do not contribute proprietary assets or credentials. See
[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [LICENSE](LICENSE).
