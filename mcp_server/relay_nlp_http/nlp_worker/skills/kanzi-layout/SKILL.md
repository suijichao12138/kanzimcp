---
name: kanzi-layout
description: Kanzi 布局节点：StackLayout2D 创建、方向设置（StackLayoutConcept.Direction 用 @int 强转）、要点。节点创建基础见 kanzi-node-create。
---

# 布局节点

### 🌟 布局节点（StackLayout2D 横向/纵向，2026-08-10 实测打通）

> 在 2D 界面里做横向/纵向自动排布，用 **`StackLayout2D`** 节点（不是 3D 的 `StackLayout3D`）。方向由 `StackLayoutConcept.Direction` 控制。

### 创建（kz_create_node type=StackLayout2D）
```python
# 横向布局节点
kz_create_node parent=/Screens/Screen/RootPage type=StackLayout2D name=layout_h   # → @obj10358
# 纵向布局节点
kz_create_node parent=/Screens/Screen/RootPage type=StackLayout2D name=layout_v   # → @obj10359
```

### 设方向（⚠️ 必须用 @int: 强转整数）
> `StackLayoutConcept.Direction` 是 **CustomEnum**，枚举值（get_Options 查到）：**X=0(横向) / Y=1(纵向) / Z=2**。
> ⚠️ **唯一能设成功的方式是 `set_Item` + `@int:` 前缀**。裸 `int`、`@enum:Y`、字符串 `"Y"`、`Set` 方法**全部报错** `cannot be converted to studio internal property value`。

```python
# layout_h 横向 = X = 0（默认即是 0）
# layout_v 纵向 = Y = 1 → 必须 @int:1
kz_invoke target=/Screens/Screen/RootPage/layout_v method=set_Item args=["StackLayoutConcept.Direction", "@int:1"]  # ✅
# 读回 get_Item → 1 即成功
kz_invoke target=.../layout_v method=get_Item args=["StackLayoutConcept.Direction"]  # → 1
```

### 要点
- 类型 `StackLayout2D`（2D），方向属性是 `StackLayoutConcept.Direction`（不是 `Layout2D.Orientation`）。
- 方向枚举：X=横向排 / Y=纵向排 / Z。查询用 `get_Properties` 拿 Direction 属性 → `get_Options` 看 KeyValuePair [X,0]/[Y,1]/[Z,2]。
- 设值铁律：CustomEnum + `set_Item` → **必须 `@int:枚举值`**。

