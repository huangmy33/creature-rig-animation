---
name: creature-rig-animation
description: 将无骨骼 GLB 异形模型自动或半自动转换为可播放的骨骼动画 GLB，支持模型检查、触手/蛇/东方龙等长链中心线提取、双翼与完整生物骨架设计、Blender 自动绑骨、自然语言动作分解、程序化关键帧、形变渲染验收和 glTF 规范校验。适用于用户要求给异形、怪物、触手、翅膀、飞龙、长尾或非人形生物绑骨、生成攻击/摆动/振翅/蜿蜒飞行动画并交付最终 GLB 的场景。
author: huangmengyang
---

# 异形模型绑骨与动画

将静态 GLB 变成最终动画 GLB。把语义判断和骨架设计留给 Agent，把重复、脆弱的几何处理、绑骨、关键帧写入和验证交给脚本与 Blender。

## 能力边界

- 适合结构清晰的单体网格：触手、蛇、藤蔓、尾巴、双翼、飞龙、东方龙和常见异形生物。
- 长链结构可自动提取中心路径；双翼和完整生物通常需要根据多视图生成或调整引导 JSON。
- 距离权重是可靠初值，不等于最终艺术权重。肢体贴近、薄翼交叠、多个离散部件或高要求角色可能需要人工权重修正。
- 不把流程描述成“任意模型全自动”。未完成多视图与形变验收时，不交付最终资产。

## 环境与工作目录

需要：Python 3.10+、Blender 3.4+、Node.js 18+。

在 Skill 根目录执行脚本；所有中间结果放到 `temp_data/<task-name>/`：

```bash
cd user_skills/creature-rig-animation
python3 -m pip install trimesh numpy scipy networkx scikit-image pillow
npm install --prefix temp_data/node gltf-validator@2.0.0-dev.3.10
```

不要把用户模型、渲染图、`.blend` 或最终 GLB 写入 Skill 源码目录；只写 `temp_data/` 或用户指定的交付目录。

核心脚本：

- [inspect_glb.py](scripts/inspect_glb.py)：检查 GLB 结构与几何。
- [extract_chain_guides.py](scripts/extract_chain_guides.py)：提取长链中心路径。
- [render_guides_overlay.py](scripts/render_guides_overlay.py)：绘制骨骼叠加图。
- [auto_rig_blender.py](scripts/auto_rig_blender.py)：在 Blender 中创建骨架并计算权重。
- [animate_chain_blender.py](scripts/animate_chain_blender.py)：生成蜿蜒、探查和拍击动作。
- [animate_wing_blender.py](scripts/animate_wing_blender.py)：生成对称振翅动作。
- [validate_animation_blender.py](scripts/validate_animation_blender.py)：验证顶点确实发生形变。
- [render_animation_blender.py](scripts/render_animation_blender.py)：渲染多视角关键帧。
- [validate_glb.mjs](scripts/validate_glb.mjs)：执行 glTF 规范校验。

## 完整工作流

### 1. 检查原始 GLB

```bash
python3 scripts/inspect_glb.py <input.glb> --geometry
```

确认：

- GLB 2.0 合法，文件声明长度一致。
- 至少有一个网格，纹理/缓冲区无外部 URI。
- 是否已有 `skins` 或 `animations`；已有骨架时优先复用，不重复绑骨。
- 记录边界、长宽高和主轴方向，后续所有引导点必须匹配实际比例。

### 2. 选择骨架策略

- **单链结构**：触手、蛇、藤蔓、长尾、东方龙 → 自动提取中心路径。
- **对称双翼**：左右翼独立或附着在躯干 → 设计 shoulder/elbow/wrist/finger 镜像层级。
- **完整生物**：先建立 spine/neck/head/tail 主链，再添加左右翼和四肢分支。
- **不规则多部件**：先分网格或使用 `meshNames` 限定骨骼影响范围。

详细骨架 schema、坐标转换和形态规则见 [guide-design.md](references/guide-design.md)。

### 3. 生成并验收引导点

单链示例：

```bash
python3 scripts/extract_chain_guides.py \
  --input <input.glb> \
  --output temp_data/<task>/guides.json \
  --bones 19 --prefix dragon --kind custom
```

默认最长路径进入角、须、肢体等分支时，使用 `--start minx|maxx|miny|maxy|minz|maxz`、`--end ...`、`--reverse` 和 trim 参数约束端点或调整主链方向。

生成四视图叠加图：

```bash
python3 scripts/render_guides_overlay.py \
  --input <input.glb> \
  --guides temp_data/<task>/guides.json \
  --output temp_data/<task>/guides-overlay.png
```

必须查看叠加图。骨链未穿过几何中心、进入装饰分支、翼根偏离连接处或左右不对称时，修改引导点后重画；不要带着错误引导进入权重阶段。

### 4. Blender 自动绑骨

```bash
blender --background --factory-startup -t 1 \
  -P scripts/auto_rig_blender.py -- \
  --input <input.glb> \
  --guides temp_data/<task>/guides.json \
  --output temp_data/<task>/rigged.glb \
  --save-blend
```

输出：

- `rigged.glb`：已绑骨模型。
- `rigged.blend`：后续动画源工程。
- `rigged.rigging.json`：网格、顶点、骨骼和权重摘要。

脚本使用距离平方反比权重、每顶点最多 4 个骨骼影响并归一化。若相邻肢体被错误骨骼吸附，回到引导设计或对网格做 `meshNames` 分区。

### 5. 把动作描述拆成动画结构

先定义：

1. 动作阶段：蓄力、主动作、跟随、恢复或循环。
2. 骨骼职责：哪些骨骼先动、哪些延迟、哪些稳定。
3. 幅度与相位：根部小/先动，末端大/后动，或按具体形态反转。
4. 时序：攻击类非循环；飞行、游动和探查类首尾一致。
5. 局部轴：首次结果需通过多视图判断旋转方向，不能只凭骨名假定。

动作模式和调参原则见 [motion-design.md](references/motion-design.md)。

### 6. 生成动画 GLB

长链动作：

```bash
blender --background temp_data/<task>/rigged.blend \
  -P scripts/animate_chain_blender.py -- \
  --output <final.glb> \
  --profile undulate \
  --prefix dragon_ \
  --amplitude 8
```

可用 profile：

- `undulate`：蛇、东方龙、长尾的循环蜿蜒。
- `probe`：触手探查/摆动循环。
- `slap`：触手蓄力并向前抽击，非循环。

标准双翼动作：

```bash
blender --background temp_data/<task>/rigged.blend \
  -P scripts/animate_wing_blender.py -- \
  --output <final.glb> --amplitude 28
```

对于复杂动作，复制最接近的脚本到任务临时目录并按动作分镜修改；不要修改 Skill 内源脚本来适配单一模型。

### 7. 数值与视觉验收

```bash
blender --background --factory-startup \
  -P scripts/validate_animation_blender.py -- \
  --input <final.glb>
```

```bash
blender --background --factory-startup \
  -P scripts/render_animation_blender.py -- \
  --input <final.glb> \
  --output-dir temp_data/<task>/review
```

查看前、侧、透视关键帧。形变数值通过但出现拉裂、塌陷、穿模、方向相反、翼膜折错或头部失稳，仍视为失败，回到引导或动作阶段调整。

完整门槛与故障处理见 [quality-gates.md](references/quality-gates.md)。

### 8. glTF 规范校验

```bash
node scripts/validate_glb.mjs <final.glb>
```

只有 `0 errors / 0 warnings` 才交付。Validator 的 info/hint 也应阅读；可无损消除时再重新导出。

## 交付要求

默认只交付一个最终动画 GLB，并说明：

- 动画名称、时长和是否循环。
- 骨骼数量、顶点形变验证结果。
- Validator 的 errors/warnings 数量。
- 是否为原地运动；游戏中的整体前进通常由角色控制器负责。

用户明确要求源码时，再交付对应任务的引导 JSON、动画脚本和一键流水线目录。
