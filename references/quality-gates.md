# 质量门槛与复杂模型审查

## 必须通过的门槛

1. **结构**：GLB 2.0 合法，缓冲区和纹理内嵌，至少包含一个网格。
2. **骨架**：骨名唯一、父节点存在、无零长度骨骼、主链方向连续。
3. **蒙皮**：每个顶点至少有一个有效权重，最多保留 4 个影响，权重和为 1。
4. **动作**：重新导入后存在 Armature 和 Action；至少有可见数量的顶点移动超过 1 mm；所有坐标有限。
5. **数值稳定**：完整时间段内无网格爆炸、整体塌缩和非预期根节点漂移。
6. **循环**：循环动作首尾姿态在指定容差内一致。
7. **视觉**：复杂模型必须完成六向正交视图、四个斜向透视视图和动作极值帧审查。
8. **规范**：Khronos glTF Validator 为 0 errors、0 warnings。

## 数值形变验证

默认均匀采样 9 帧，而不是只检查首、中、尾三帧：

```bash
blender --background --factory-startup -P scripts/validate_animation_blender.py -- \
  --input output.glb --samples 9
```

循环动作增加首尾连续性检查：

```bash
blender --background --factory-startup -P scripts/validate_animation_blender.py -- \
  --input output.glb --samples 9 --expect-loop --loop-tolerance 0.001
```

包含刻意整体位移的动作使用 `--allow-root-motion`，避免把正常前进误报为漂移。默认阈值会阻断：

- `mesh-explosion`：变形包围盒对角线超过初始姿态 4 倍。
- `mesh-collapse`：变形包围盒对角线低于初始姿态 20%。
- `unexpected-root-drift`：模型中心漂移超过初始包围盒对角线 3 倍。
- `loop-discontinuity`：循环首尾最大顶点差超过指定容差。

这些检查只捕获明显数值故障，不能替代视觉审查。

## 多视角关键帧审查

复杂模型默认使用 `complex` 预设：

```bash
blender --background --factory-startup -P scripts/render_animation_blender.py -- \
  --input output.glb \
  --output-dir temp_data/review \
  --preset complex --max-frames 9
```

该预设生成：

- 六向正交视图：前、后、左、右、顶、底。
- 四个斜向透视视图：前左、前右、后左、后右。
- 最多 9 个审查帧：优先覆盖实际关键帧，并补充均匀时间采样。
- `review-manifest.json`：记录视图、帧、动画全程包围盒和审查清单。

简单模型或快速迭代可用 `--preset standard --max-frames 5`；最终交付复杂模型时必须恢复 `complex`。

多部件模型可针对高风险网格增加透视特写：

```bash
blender --background --factory-startup -P scripts/render_animation_blender.py -- \
  --input output.glb \
  --output-dir temp_data/review \
  --preset complex \
  --detail-objects Wing_L Wing_R Head
```

对象名必须与 GLB 导入 Blender 后的网格对象名一致。优先特写：薄翼、翼根、头颈、触手根部、爪部、相互贴近的肢体和多个网格连接处。

生成便于完整检查的总览图：

```bash
python3 scripts/build_review_contact_sheets.py --review-dir temp_data/review
```

输出包含两类总览：

- `frame-*-all-views.png`：同一关键帧的全部视角，用于发现遮挡、自穿插和方向相关问题。
- `timeline-*.png`：同一视角的完整时间采样，用于发现抖动、漂移、突跳和循环不连续。

先查看所有总览，再打开可疑区域对应的全分辨率单图；不得只抽查第一帧或单一视角。

## 逐视图审查清单

不要只确认“模型在动”。每个审查帧逐项检查：

1. **轮廓与方向**：动作方向是否符合描述，是否存在反向关节或不自然折线。
2. **关节体积**：弯曲处是否塌陷、鼓包、拉长或产生尖刺。
3. **自穿插**：左右肢体、翼膜、尾巴、触手是否互穿或穿过躯干。
4. **薄片结构**：翼膜、鳍、耳片是否翻面、折错或在单一视角中被遮挡。
5. **稳定区域**：头部、躯干根部和附着点是否出现非预期漂移或抖动。
6. **对称性**：需要对称的振翅、步态和肢体是否在左右/前后视图中一致。
7. **循环连续性**：首尾帧姿态、轮廓和接触关系是否无跳变。
8. **局部连接**：离散网格连接处是否脱节，蒙皮影响是否串到邻近肢体。

一个视角发现疑点时，必须回看相对视图和斜向视图；遮挡区域只看正面不能判定通过。任何一项失败都回到引导点、网格分区、权重或动画阶段修正，然后重新生成整套审查图。

## GLB 规范验证

首次使用缺少依赖时再安装：

```bash
npm ci --ignore-scripts
node scripts/validate_glb.mjs output.glb
```

## 常见问题

### `self is not defined`

Node 版 Three.js GLTFLoader 无法直接解码带纹理图像。生产动作优先在 Blender 内完成，Node 仅做 GLB 字节级验证。

### Draco library not found

Blender 日志可能报告 Draco 导出库缺失。如果未请求压缩且最终 GLB Validator 通过，可忽略；不要宣称输出已使用 Draco。

### `NODE_SKINNED_MESH_NON_ROOT`

导出动画前保留 Armature modifier，但将网格对象解除 Armature 父级并保持世界矩阵，再导出。新版 Blender 可能为此报告 `Armature must be the parent of skinned mesh`：本工具显式限制为单骨架，检查每个网格仍引用同一 Armature modifier，导出后必须重新导入做形变检查并通过 glTF Validator。该导出器提示保留在日志中，不属于 Validator 的 warnings，也不是被静默忽略的任意警告；多骨架和实例化骨架不在这条兼容策略的保证范围内。

### 缺少切线或切线未使用

有法线贴图的材质应启用 `export_tangents=True`；没有法线贴图时可关闭，避免 `UNUSED_MESH_TANGENT` 信息。

### 形变数值通过但视觉失败

距离权重只能保证连续权重，不能保证语义正确。回到骨骼叠加图检查骨骼位置；对邻近肢体使用网格分区或人工权重修正。六向视图仍被遮挡时，为对应网格增加 `--detail-objects` 特写。
