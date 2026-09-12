# 质量门槛与排障

## 必须通过的门槛

1. **结构**：GLB 2.0 合法，缓冲区和纹理内嵌，至少包含一个网格。
2. **骨架**：骨名唯一、父节点存在、无零长度骨骼、主链方向连续。
3. **蒙皮**：每个顶点至少有一个有效权重，最多保留 4 个影响，权重和为 1。
4. **动作**：重新导入后存在 Armature 和 Action；至少有可见数量的顶点移动超过 1 mm；所有坐标有限。
5. **循环**：循环动作的首尾骨骼通道数值一致。
6. **视觉**：前、侧、透视关键帧无明显拉裂、塌陷、左右反向、翼膜穿体或头部失稳。
7. **规范**：Khronos glTF Validator 为 0 errors、0 warnings。

## 推荐命令

### 数值形变验证

```bash
blender --background --factory-startup -P scripts/validate_animation_blender.py -- \
  --input output.glb
```

### 关键帧渲染

```bash
blender --background --factory-startup -P scripts/render_animation_blender.py -- \
  --input output.glb --output-dir temp_data/review
```

### GLB 规范验证

首次使用先安装依赖到临时目录：

```bash
npm install --prefix temp_data/node gltf-validator@2.0.0-dev.3.10
node scripts/validate_glb.mjs output.glb
```

## 常见问题

### `self is not defined`

Node 版 Three.js GLTFLoader 无法直接解码带纹理图像。生产动作优先在 Blender 内完成，Node 仅做 GLB 字节级验证。

### Draco library not found

Blender 日志可能报告 Draco 导出库缺失。如果未请求压缩且最终 GLB Validator 通过，可忽略；不要宣称输出已使用 Draco。

### `NODE_SKINNED_MESH_NON_ROOT`

导出动画前保留 Armature modifier，但将网格对象解除 Armature 父级并保持世界矩阵，再导出。

### 缺少切线或切线未使用

有法线贴图的材质应启用 `export_tangents=True`；没有法线贴图时可关闭，避免 `UNUSED_MESH_TANGENT` 信息。

### 形变数值通过但视觉失败

距离权重只能保证连续权重，不能保证语义正确。回到骨骼叠加图检查骨骼位置；对邻近肢体使用网格分区或人工权重修正。
