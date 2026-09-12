# 动作设计模式

## 从描述到骨骼曲线

先把自然语言拆成动作阶段，再设置骨骼职责、幅度、方向、相位和节奏。不要直接把关键词映射到一个统一正弦波。

## 周期动作

### 蜿蜒/游动

沿主链设置递增相位延迟：

```text
angle(i, t) = amplitude(i) * sin(2π * cycles * t - i * phaseDelay)
```

- 头部幅度小，尾部逐渐放大。
- 同时使用两个旋转轴形成三维轨迹。
- 根骨骼只叠加轻微升沉、俯仰和横滚。
- 首尾关键帧数值完全一致。

`scripts/animate_chain_blender.py --profile undulate` 适合蛇、长尾、东方龙和藤蔓。

### 探查/摆动

让波动从根部传播到尖端，叠加二次谐波避免机械感。使用 `--profile probe`。

### 振翅飞行

翼根先发力，翼肘、翼腕、翼指依次减幅并延迟。`scripts/animate_wing_blender.py` 依赖标准翼骨命名；完整飞行生物可额外使用 `tail_*` 和 `root` 获得尾部配平与身体升沉。

## 非周期动作

### 拍打/抽击

动作阶段：静止 → 反向蓄力 → 根部启动 → 波峰传向尖端 → 命中/跟随 → 回弹。关键点：

- 击打时间短于蓄力与恢复。
- 各段命中帧按骨骼编号延迟，产生鞭梢速度。
- 累积旋转受骨骼数量影响；长链每段角度应更小。
- 使用 `--profile slap`，不要强制循环。

## 旋转轴校正

引导骨骼方向和 Blender bone roll 会影响局部轴。首次生成后必须渲染前、侧、透视关键姿态：

- 方向相反：反转对应轴角度符号。
- 只在平面内折叠：增加垂直于模型平面的旋转轴。
- 形变过大：先降低单骨幅度，而不是减少关键帧。
- 动作僵硬：增加相位差与末端跟随，不要只增加幅度。

## 运行示例

```bash
blender --background work/rigged.blend -P scripts/animate_chain_blender.py -- \
  --output output.glb --profile undulate --prefix dragon_ --amplitude 8
```

```bash
blender --background work/rigged.blend -P scripts/animate_wing_blender.py -- \
  --output output.glb --amplitude 28
```
