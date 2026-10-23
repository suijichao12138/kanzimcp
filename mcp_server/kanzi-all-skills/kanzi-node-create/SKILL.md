---
name: kanzi-node-create
description: Kanzi 节点创建：kz_create_node 创建 EmptyNode2D/TextBlock2D/插件节点/九宫格，Prefabs 模板库下创建，删除节点。布局节点见 kanzi-layout。不含属性设置（见 kanzi-prop-set）。
---

## 🚫 命名铁律（创建前必读）

> 创建任何东西（节点/资源/动画/别名/条目）时，**名字禁止特殊字符**：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格。
> **允许中文，推荐英文**（中文名可用，但英文更稳妥，避免跨工具编码问题）。
> 不要以数字开头（部分 API 限制）。
> 错误：`text/header` `bg.1` `a|b` `C:\temp` `new node`；正确：`text_header` `bg_1` `标题文本` `header-text`。

## 创建节点

### kz_create_node（推荐，最简单）

```python
# 创建 EmptyNode2D
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_create_node","arguments":{"parent":"/Screens/Screen/RootPage/Info","type":"EmptyNode2D","name":"warning"}}})
# 返回：✅ 节点已创建: @obj2

# 创建 TextBlock2D
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_create_node","arguments":{"parent":"/Screens/Screen/RootPage/Info/warning","type":"TextBlock2D","name":"text"}}})
# 返回：✅ 节点已创建: @obj3
```

### 可用节点类型

| 类型 | 说明 |
|------|------|
| EmptyNode2D | 空容器节点 |
| TextBlock2D | 文本块（支持 FontFamily、StateManager 等属性） |
| Node2DPrefabPlaceholder | **Prefab 占位符节点**（引用模板，如 gear/POP） |
| PluginTextscroll | **插件注册的滚动文本节点**（见下方专节） |

### 🌟 在 Prefabs 模板库下创建节点（2026-08-17 实测打通）

> **背景**：`/Prefabs/...`（模板库）里也能建节点，但**父路径必须写到真实 UI 节点那一层，不能停在「模板条目」上**——否则创建的节点在 API 层「成功」、UI 工程树里却**不可见（幽灵节点）**。

#### ⚠️ 关键坑：Prefabs 是两层结构

`/Prefabs/<模板名>` 解析到的是**模板条目**（`Node2DPrefabTemplatePluginWrapper`），它下面还有一个**模板内部根节点**（常与模板同名，`EmptyNode2D`）。

```
/Prefabs/tireItem          ← 模板条目（Node2DPrefabTemplate）—— ✗ 在这一层建会成幽灵
/Prefabs/tireItem/tireItem ← 模板内部根节点（EmptyNode2D）—— ✓ 真实 UI 节点，在这里建才可见
```

> 怎么找内部根：枚举 `/Prefabs/<模板名>` 的 `get_Children`，第一个子项往往是**同名 EmptyNode2D** 即模板内部根；其他子项是模板里的真实内容（如 `tirePre`/`tireTem`/`NO ID` 等）。

#### ① 在 Prefabs 模板内部根节点下建节点（✅ 可见）

```python
# 在模板 tireItem 的内部根节点下建（父 = /Prefabs/tireItem/tireItem）
mcp kz_create_node parent=/Prefabs/tireItem/tireItem type=EmptyNode2D name=xxx
# → ✅ 节点已创建: @obj17（UI 可见）
```

#### ② 在 Prefabs 下的节点里继续嵌套建节点（✅ 可见）

**父路径必须写全完整层级**：`/Prefabs/<模板名>/<模板内部根>/<子节点>/...`。

> ⚠️ 只写到中间层（如 `/Prefabs/tireItem/KZMCP_in_105051`，漏了模板内部根那层）会报 `父节点 '...' 不存在`，因为路径解析把 `/Prefabs/tireItem` 当模板条目，再往下一层对不上。

```python
# 在已建节点 KZMCP_in_105051（挂在 /Prefabs/tireItem/tireItem 下）下面再建
mcp kz_create_node parent=/Prefabs/tireItem/tireItem/KZMCP_in_105051 type=EmptyNode2D name=xxx
# → ✅ 节点已创建: @obj25（UI 可见）
```

#### ③ 直接在 Prefabs 库根下建节点（✅ 可见）

```python
mcp kz_create_node parent=/Prefabs type=EmptyNode2D name=xxx
# → ✅ 节点已创建（UI 可见，会作为模板条目出现在库根）
```

#### 规则总结

1. **建节点父路径必须写到「真实 UI 节点」层级**（`/Screens/...` 的真实节点、或 `/Prefabs/<模板名>/<模板内部根>`）。
2. **停在模板条目**（`/Prefabs/<模板名>`）会建出**幽灵节点**：API 层 `get_Children` 能枚举到、路径能解析，但 **UI 工程树里看不到、同名可再建**。
3. 嵌套建节点父路径要写**完整层级**，不能漏中间的模板内部根那层。
4. 判断是否真建成功：**以 Kanzi UI 工程树为准**（或让老隋在 UI 确认），别只看 API 枚举返回值。
5. `kz_create_node` 本身在 `/Screens/...` 和 `/Prefabs/...` 都能真实建节点；`kz_create_node` 无需区分工程激活与否（多工程 select 到哪个工程就操作哪个）。

### 🌟 创建插件节点类型（PluginXxx，2026-08-08 实测打通）

> **背景**：要求"创建 `plugin_textscroll` 类型的节点"。直接传 `plugin_textscroll` 会失败（`不支持的节点类型或方法`）。**正确类型名是 `PluginTextscroll`** —— 插件在工程里注册的节点类型名是 `Plugin` + 名字（无点、无 2D 后缀），不是下划线的 `plugin_xxx`。

#### ⚠️ 找插件节点类型的正确方法（关键！）

**先查工程运行时注册的 ComponentTypeLibrary**，看真名，不要猜：

```python
# 1. 拿 ComponentTypeLibrary（组件类型库，含所有可创建节点类型）
mcp kz_invoke target=@project method=get_ComponentTypeLibrary   # → @obj19 (ComponentTypeLibraryPluginWrapper)

# 2. 列出库内所有注册类型，末尾即插件自定义类型
mcp kz_invoke target=@obj19 method=get_Items
# → 输出 "▪ name = ..." 行:
#   Kanzi.Activity2D / Kanzi.TextBlock2D / ...  (库内自带 2D/3D 节点类型)
#   ...
#   PluginTextscroll          ← 插件注册的节点类型！真名在此
```

> 📌 区分两个库：
> - **ComponentTypeLibrary**（`@project.get_ComponentTypeLibrary`）→ 可创建为节点的类型（TextBlock2D、Button2D、**PluginXxx** 等），路径需带/不带 `Kanzi.` 前缀都能匹配。
> - **NodeComponentTypeLibrary**（`@project.get_NodeComponentTypeLibrary`）→ 只有**组件**类型（ClickManipulatorComponent、OnPropertyChangedTrigger、AnimationPlayer 等），**不含**视觉节点类型，找节点类型别来这里。

#### 用查到真名创建节点

```python
# 用从 ComponentTypeLibrary 查到的真名（本例 PluginTextscroll）
mcp kz_create_node parent=/Screens/Screen/RootPage/Info type=PluginTextscroll name=TextScroll
# → ✅ 节点已创建: @obj69 (类型 = ComponentNode2DPluginWrapper)
# 树: Info → PluginTextscroll → TextScroll
```

#### 规则总结

1. **`plugin_textscroll`（下划线小写）必失败** → 正确名 `PluginTextscroll`（`Plugin` + 首字母大写的类型名）。
2. 不确定插件类型名时，**先 `get_ComponentTypeLibrary` → `get_Items` 枚举**，认准 `Plugin` 开头的条目名再创建。**不要脑补/猜类型名**（曾多次因脑补枚举/类型名踩坑）。
3. 插件视觉节点创建后包装类型是 `ComponentNode2DPluginWrapper`。

### 设对齐（Node.HorizontalAlignment / Node.VerticalAlignment）
> 创建后如需设对齐 → **`kanzi-prop-set` skill**（枚举属性用 `@int:` 设置，枚举表见那里）。

## 🌟 九宫格图片（NinePatchImage2D 节点，2026-08-10 实测打通）

> ⚠️ **正确做法：创建 `NinePatchImage2D` 类型的节点**（不是 `Image2D` 节点上设 NinePatch 属性）。`NinePatchImage2D` 是真九宫格节点类型。
> （曾走弯路：在 Image2D 上 AddProperty 设 `NinePatchImage2D.Image*` —— 错，应直接建 NinePatchImage2D 节点。）

### 创建（真实类型名是 NinePatchImage2D，带 2D 后缀）
```python
kz_create_node parent=/Screens/Screen/RootPage type=NinePatchImage2D name=bg_9slice  # → @obj11125
```
> ⚠️ 不存在的名：`Node9Slice2D` / `Image9Slice2D` / `NinePatchImage`（都报“不支持的节点类型”）。真名只有 `NinePatchImage2D`。

### 该节点自带属性（无需 AddProperty，创建即带）
- 9 块图：`NinePatchImage2D.ImageTopLeft/Top/TopRight/Left/Center/Right/BottomLeft/Bottom/BottomRight`
- 拉伸类型：`NinePatchImage2D.StretchTypeTop/Bottom/Left/Right/Center`
- 图片暂不填时，只建节点即可（9 块属性已自带上）。
- **设图 → `kanzi-prop-set` skill**（直接设置图片，见「图片 / 九宫格设置」）。

> 布局节点（StackLayout2D 等）→ `kanzi-layout` skill。
> 属性增删改查 → `kanzi-prop-set` skill。

## 删除节点

```python
# 按路径删除节点（含子节点）
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_delete_node","arguments":{"node_path":"/Screens/Screen/RootPage/Info/warning/text"}}})
```

> ⚠️ 若 `kz_delete_node` 不可用（新版插件报“不支持的节点类型或方法”）→ 用 `kz_invoke` 调节点的 `Delete()` 方法：
> ```python
> mcp kz_invoke target=@节点 method=Delete args=[]
> ```
> ⚠️ 注意：`Delete()` 删除的是整个项目项（含子层级），确认目标再删；误删无法撤销。