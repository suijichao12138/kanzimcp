---
name: kanzi-transform
description: Kanzi 节点定位：Node2D.RenderTransformation + @transformation2d: 设置 2D 节点位置/旋转/缩放。
---

## 🌟 节点定位（Node2D.RenderTransformation + @transformation2d:，2026-08-13 实测打通）

Kanzi 2D 节点的位置/缩放/旋转由 **`Node2D.RenderTransformation`**（类型
`Rightware.Kanzi.Studio.PluginInterface.Transformation2D`）编码，属性原始值是
5 段分号分隔：`scaleX; scaleY; rotation; translateX; translateY`（**最后两位 = tx=位置X, ty=位置Y**）。

### 设置 2D 节点位置（X:0, Y:115）

```
# 1. 若节点还没有 RenderTransformation 属性，先 AddProperty
kz_invoke target=<节点> method=AddProperty args=["Node2D.RenderTransformation"]

# 2. 用 @transformation2d: 设值（scaleX,scaleY,rotation,tx,ty —— 逗号分隔）
kz_invoke target=<节点> method=set_Item args=["Node2D.RenderTransformation","@transformation2d:1,1,0,0,115"]
#   → 位置 X:0, Y:115（scalex=1, scaleY=1, rotation=0, tx=0=位置X, ty=115=位置Y）

# 3. 读回验证（应返回非 null 的 Transformation2D）
kz_invoke target=<节点> method=get_Item args=["Node2D.RenderTransformation"]
#   → type=Transformation2D, name=1; 1; 0; 0; 115   ✅

# 4. （可选）读 Translation 分量确认
kz_invoke target=<上面返回的Transformation2D对象> method=get_Translation
#   → Vector(0, 115)  即 X=0, Y=115  ✅
```

### ⚠️ 铁律（踩坑教训 2026-08-13）

- **`@vector:` 会写坏 RenderTransformation**：`@vector:x,y` 只生成 2 分量 `System.Windows.Vector`，
  存进 Transformation2D 属性 → 读回 **null**。
- **裸字符串 `"1; 1; 0; 0; 115"` 也不行**：存成 string → 读回 null。
- **必须用 `@transformation2d:`** 构造真正的 Transformation2D 对象，读回才正常。
- 若已误设坏：`RemoveProperty("Node2D.RenderTransformation")` 恢复干净（重新 AddProperty 默认 `1;1;0;0;0`）。

### 参考：兄弟节点 Transformation2D 原始值（warning prefab，作对照）

| 节点 | RenderTransformation 原始值 | = 位置 |
|------|---------------------------|--------|
| warningBottom | `1; 1; 0; 0; 523` | X:0, Y:523 |
| warningCenter | `1; 1; 0; 0; 233` | X:0, Y:233 |
| right | `1; 1; 0; 1310; 92` | X:1310, Y:92 |
| warning_big | `1; 1; 0; 0; 205` | X:0, Y:205 |
