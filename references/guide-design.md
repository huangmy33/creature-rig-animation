# 骨骼引导设计

## 坐标约定

输入 GLB 通常为 glTF Y-up；引导文件固定使用 Blender Z-up。转换关系：

```text
GLB (x, y, z) -> Blender (x, -z, y)
Blender (x, y, z) -> GLB (x, z, -y)
```

引导 JSON 顶层：

```json
{
  "version": 1,
  "kind": "custom",
  "coordinateSystem": "BLENDER_Z_UP",
  "bones": []
}
```

每根骨骼至少包含：

```json
{
  "name": "chain_00",
  "parent": "root",
  "head": [0, 0, 0],
  "tail": [0, 0, 0.2],
  "role": "chain",
  "order": 0,
  "side": 0,
  "limits": {"x": [-30, 30], "y": [-30, 30], "z": [-35, 35]}
}
```

可选 `meshNames` 将骨骼限制到指定网格，适合多网格角色。

## 形态分类

### 单链结构

适用于触手、蛇、藤蔓、尾巴、无翼东方龙。优先运行 `scripts/extract_chain_guides.py`，再用四视图叠加检查中心线。

默认最长骨架路径适合端点明确的管状体。模型包含角、须、四肢等分支时，显式指定 `--start` 和 `--end`，并调整 `--trim-start` / `--trim-end`，避免主链进入装饰分支。

### 对称双翼

建立命名稳定的左右镜像层级：

```text
root
├─ wing_L_shoulder
│  └─ wing_L_elbow
│     └─ wing_L_wrist
│        ├─ wing_L_finger_0
│        ├─ wing_L_finger_1
│        └─ wing_L_finger_2
└─ wing_R_shoulder ...
```

- shoulder 放在翼根并承担最大上下拍幅。
- elbow 沿主翼梁中段放置。
- wrist 靠近翼尖。
- fingers 从翼根/腕部指向翼膜主要支撑方向。
- 左右 `side` 分别使用 `-1` 和 `1`。

### 完整生物

先建立躯干主链，再添加功能分支：

```text
root -> spine -> neck -> head
             ├─ left wing chain
             ├─ right wing chain
             ├─ front/hind limbs
             └─ tail chain
```

自动距离权重无法理解关节语义。骨骼必须位于对应结构内部；相邻肢体距离很近时使用 `meshNames` 分区，或在 Blender 中人工修正权重。

## 叠加图验收

运行 `scripts/render_guides_overlay.py` 后检查：

- 主链沿几何中心连续穿过，不进入角、须、牙齿或薄片装饰。
- 左右翼根落在真实连接处，左右层级镜像。
- 头部至少有稳定骨段，避免整个头部被颈部拉长。
- 尾端骨骼覆盖到主要可见尾梢，但不必进入极细装饰。
- 骨骼长度不过短，父子链没有反向跳跃或自交。

叠加不合格时先修正引导点；错误骨架进入权重阶段后会放大问题。
