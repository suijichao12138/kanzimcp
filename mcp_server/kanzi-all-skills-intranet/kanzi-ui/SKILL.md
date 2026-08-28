---
name: kanzi-ui
description: Kanzi Studio UI 节点创建/配置。EmptyNode2D、TextBlock2D、插件节点类型（PluginTextscroll 等，含类型名查找方法）、节点的属性添加/设置/删除。字体（FontFamily）、字号（FontSize）、状态机（StateManager）等属性配置。
---

# Kanzi UI 节点操作

## 🚀 多工程切换（2026-08-17 实测打通，v12）

bridge 支持多工程操作。默认 `@project` 指向 ActiveProject，可在多工程间随时切换，两种方式：

**① `kz_select_project` 切换 `@project` 作用目标（推荐）**
```json
{"name":"kz_select_project","arguments":{"name":"hmi-alarm"}}
// ✅ 已切换到工程: hmi-alarm（之后 @project 相关操作作用于该工程；ActiveProject 不变）

{"name":"kz_select_project","arguments":{"name":""}}
// ✅ 已切回 ActiveProject: cluster_hmi
```

**② `@proj:<工程名>[/路径]` 前缀独立引用某工程（不切 @project）**
```json
{"name":"kz_invoke","arguments":{"target":"@proj:hmi-alarm/Prefabs/warning","method":"get_Name","args":[]}}
```

**要点：**
- `kz_list_projects` 列出所有已打开工程（标 `[Active]` / `[Primary]`）。
- **select 到哪个工程就操作哪个；与工程是否 Active 无关**——次级工程上读写（建节点/保存）都正常。
- 切到某工程后，`/Screens/...`、`/Prefabs/...` 等路径都指该工程；要回 ActiveProject 再 select 空串。
- 全程 **ActiveProject 不变**（方案 A 承诺），不打扰你在 Studio 正编辑的工程。



## MCP 协议基础

**MCP (Model Context Protocol)** 通过 WebSocket JSON-RPC 调用 Kanzi Studio 插件。

### 接入（内网 HTTP MCP）

内网 HTTP MCP server（`relay_nlp_http/kz_mcp_http.py`）：`http://10.10.118.152:9001/mcp`（请求头 `X-Kanzi-User: <用户名>`，如 `suijichao`；中继通道 `ws://10.10.118.152:58080/<用户名>`）。直接调用 MCP 工具 `kz_invoke` 等，无需本地客户端脚本。MCP 工具返回 `ref_id = @objN` 自动进缓存，重启 Studio 后编号失效须重新枚举。

### 基本请求格式

```python
{
  "jsonrpc": "2.0",           # 固定
  "id": "请求编号",           # 任意字符串，用于匹配响应
  "method": "tools/call",     # 固定，表示调用 MCP 工具
  "params": {
    "name": "kz_invoke",      # 工具名：kz_invoke / kz_create_node / ...
    "arguments": { ... }      # 参数
  }
}
```

### 关键特殊标识符（v4）

| 标识符 | 说明 |
|--------|------|
| `@project` | 自动注入的当前工程对象（Kanzi Studio 插件自动识别） |
| `@obj123` / `@obj:123` | 对象缓存引用（`@obj:` 新格式等价，每次连接 Studio 后动态分配，重启后失效） |
| `"/Screens/..."` | 节点路径字符串（不要带 `cluster_hmi/` 前缀） |
| `@string:` / `@int:` / `@float:` / `@bool:` / `@null` / `@enum:` / `@type:` / `@node:` / `@vector:` / `@vector3d:` / `@quaternion:` / `@transformation2d:` / `@dict:` | v4 参数标识符（见文末总表） |

### 对象引用缓存机制

`@objXXX` 引用必须先在 `_objectStore` 中**缓存**才能使用。触发缓存的方式：

1. **自动缓存**：`kz_create_node` / `kz_invoke` 的返回值中的 ref_id 会自动缓存
2. **手动缓存**：用 `kz_invoke` 调用一个对象上的方法，如：
   ```
   kz_invoke({"target": "@obj10", "method": "get_Name", "args": []})
   ```
   一旦调用成功，`@obj10` 就被缓存了
3. **未缓存的引用会报错**：`对象引用 '@objXXX' 不存在或已失效`

> 每次重启 Kanzi Studio 后，所有 `@obj` 引用都会失效，需要重新获取。

本 skill 用到的工具：`kz_invoke`（反射调用）、`kz_create_node`、`kz_delete_node`、`kz_set_property` 等，参数遵循 v4 标识符 @type/@int/@string/@enum/@obj/@color 等。

## 核心原则

### 设置属性值：kz_invoke set_Item

```python
# 简单类型（int/bool/float/string）直接传值，或用 v4 标识符强制类型
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/path/to/node","method":"set_Item","args":["FontStyleConcept.Size", "@float:36"]}}})
# 字符串含数字时用 @string: 强制字符串（避免自动转 int）
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/path/to/node","method":"set_Item","args":["TextConcept.Text", "@string:123"]}}})
# ✅ 实测: @string:123 回读为字符串 "123" (不是 int)

# ResourceReference 类型（FontFamily, StateManager）：传 @obj 引用
mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/path/to/node","method":"Set","args":["Node.FontFamily", "@obj:308"]}}})
```

> ⚠️ ResourceReference 属性用 `Set`（不是 `set_Item`），`@obj:` 从项目资源文件夹 get_Children 获取

### 获取属性值：kz_invoke get_Item

```python
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:1873","method":"get_Item","args":["TextConcept.Text"]}}})
```

### 添加属性：AddProperty

```python
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:238","method":"AddProperty","args":["@string:warning.value"]}}})
# 也支持传 PropertyType 对象引用
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:238","method":"AddProperty","args":["@obj:248"]}}})
```

### 删除属性：RemoveProperty

```python
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:238","method":"RemoveProperty","args":["@obj:248"]}}})
```

### 批量操作（必须成对）

批量操作必须在同一 batch 内创建嵌套的项目层级，**BeginBatchModification 和 CommitBatchModification 必须成对出现**，否则 Kanzi Studio 会卡死。

```python
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"BeginBatchModification","args":["描述"]}}})
# 多个操作...
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"CommitBatchModification"}}})
```

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
| PluginTextscroll | **插件注册的滚动文本节点**（老隋需求，见下方专节） |

### 🌟 在 Prefabs 模板库下创建节点（2026-08-17 实测打通，老隋逐次确认）

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

> **背景**：老隋要求"创建 `plugin_textscroll` 类型的节点"。直接传 `plugin_textscroll` 会失败（`不支持的节点类型或方法`）。**正确类型名是 `PluginTextscroll`** —— 插件在工程里注册的节点类型名是 `Plugin` + 名字（无点、无 2D 后缀），不是下划线的 `plugin_xxx`。

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

### 设对齐（Node.HorizontalAlignment / Node.VerticalAlignment，老隋给的枚举表）
> 对齐是**枚举属性**，设置同样**必须 `@int:`**（与 Direction 同理，不支持 `@enum:`/裸字符串）。枚举值对照表（老隋提供，2026-08-19）：

| 属性 | 枚举项 | MCP 数值 |
|------|--------|----------|
| `Node.HorizontalAlignment` | `LEFT` | `@int:0` |
| `Node.HorizontalAlignment` | `RIGHT` | `@int:1` |
| `Node.HorizontalAlignment` | `CENTER` | `@int:2` |
| `Node.HorizontalAlignment` | `STRETCH` | `@int:3` |
| `Node.VerticalAlignment` | `BOTTOM` | `@int:0` |
| `Node.VerticalAlignment` | `TOP` | `@int:1` |
| `Node.VerticalAlignment` | `CENTER` | `@int:2` |
| `Node.VerticalAlignment` | `STRETCH` | `@int:3` |

```python
# 水平居中
kz_invoke target=.../节点 method=set_Item args=["Node.HorizontalAlignment", "@int:2"]  # CENTER
# 垂直居中
kz_invoke target=.../节点 method=set_Item args=["Node.VerticalAlignment", "@int:2"]  # CENTER
```

## 🌟 九宫格图片（NinePatchImage2D 节点，2026-08-10 实测打通）

> ⚠️ **正确做法：创建 `NinePatchImage2D` 类型的节点**（不是 `Image2D` 节点上设 NinePatch 属性）。`NinePatchImage2D` 是真九宫格节点类型。
> （曾走弯路：在 Image2D 上 AddProperty 设 `NinePatchImage2D.Image*` —— 错，应直接建 NinePatchImage2D 节点。）

### 创建（真实类型名是 NinePatchImage2D，带 2D 后缀）
```python
kz_create_node parent=/Screens/Screen/RootPage type=NinePatchImage2D name=bg_9slice  # → @obj11125
```
> ⚠️ 不存在的名：`Node9Slice2D` / `Image9Slice2D` / `NinePatchImage`（都报“不支持的节点类型”）。真名只有 `NinePatchImage2D`。

### 该节点自带属性（无需 AddProperty，创建即带）
- 9 块图（ResourceReference，引用图片）：`NinePatchImage2D.ImageTopLeft/Top/TopRight/Left/Center/Right/BottomLeft/Bottom/BottomRight`
- 拉伸类型：`NinePatchImage2D.StretchTypeTop/Bottom/Left/Right/Center`
- 图片引用暂不填时，只建节点即可（9 块属性已自带上）。
- 以后设图用 `set_Item(属性, KzResourceID:xxx 或 @obj图片)`。

## 删除节点

```python
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_delete_node","arguments":{"node_path":"/Screens/Screen/RootPage/Info/warning/text"}}})
```

## 引用模板（Prefab Placeholder，2026-08-07 实测打通）

> ⚠️ **关键坑**：Kanzi 里"节点引用模板/预制体"**不是**给节点设 `Node.Prefab` 属性（不支持），而是把节点创建为 **`Node2DPrefabPlaceholder`** 类型。这类节点天然带 `Node2DPrefabPlaceholderTemplate` 属性（ResourceReference，指向 Node2DPrefabTemplate），设置成目标模板即可。工程现有实例：`gear_mini_default` / `gear_driving` 都引用 gear 模板。

```python
# 1. 定位模板（Prefabs 库 @obj121 = Prefabs）
mcp kz_invoke target=@obj121 method=get_Children
# → 找目标 Node2DPrefabTemplate, 如: @obj342 POP / @obj331 TextPrefab_pop / @obj325 ImagePrefab / @obj329 gear / @obj324 TextPrefab_text
# 模板根节点类型看 get_RootNode2D: TextPrefab_* 的 root 是 TextBlock2D(文本), ImagePrefab 的 root 是 Image2D(图片)

# 2. 创建 Node2DPrefabPlaceholder 类型节点（在 Info 或任意节点下）
mcp kz_create_node parent=/Screens/Screen/RootPage/Info type=Node2DPrefabPlaceholder name=warning_pop
# → ✅ 节点已创建: @obj5279 (类型=Node2DPrefabPlaceholderPluginWrapper)

# 3. 设 Node2DPrefabPlaceholderTemplate = 模板引用（ResourceReference！用 set_Item, 不用 Set）
mcp kz_invoke target=@obj5279 method=set_Item args=["Node2DPrefabPlaceholderTemplate","@obj342"]
# → ✅ 读回 get_Item = "POP" 即可确认成功
```

**📌 同一方法可引用任意模板（2026-08-07 实测，Info 下）：**
- `warning_pop` → **POP**（Node2DPrefabPlaceholder）✅
- `test_text` → **TextPrefab_text**（模板 root=TextBlock2D 文本）✅
- `test_image` → **ImagePrefab**（模板 root=Image2D 图片）✅
- 已有参考：`gear_mini_default` → gear 、`gear_driving` → gear_driving

> ⚠️ 若用 EmptyNode2D 建节点再 AddProperty("Node2DPrefabPlaceholderTemplate") 会失败（"ProjectItem of type..."），因为该属性不属于普通 EmptyNode2D。**必须用 Node2DPrefabPlaceholder 类型创建。**
> ⚠️ `kz_delete_node` 按路径能删除冲突/错误的占位节点（如误建的 EmptyNode2D warning_pop）。

## TextBlock2D 完整配置流程

```python
# 1. 创建节点
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_create_node","arguments":{"parent":"/Screens/Screen/RootPage/Info/warning","type":"TextBlock2D","name":"text"}}})

# 2. 字号
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"AddProperty","args":["FontStyleConcept.Size"]}}})
mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"set_Item","args":["FontStyleConcept.Size", 36]}}})

# 3. 字体（ResourceReference 类型 — 先扫描项目找到资源）
# 步骤3a：扫描项目，找到 Font Families 文件夹
r = mcp({"jsonrpc":"2.0","id":"4","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"get_Children"}}})
# 从 r 中找到 "Font Families" 行的上一个 ref_id，如 @obj47

# 步骤3b：在字体文件夹中找 MiSans-Medium
r = mcp({"jsonrpc":"2.0","id":"5","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj47","method":"get_Children"}}})
# 从 r 中找到 "MiSans-Medium" 行的上一个 ref_id，如 @obj308

# 步骤3c：缓存这个 @obj 引用（发一次 get_Name 确认）
mcp({"jsonrpc":"2.0","id":"6","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj308","method":"get_Name","args":[]}}})
# 返回 MiSans-Medium 即为缓存成功

# 步骤3d：设置 FontFamily
mcp({"jsonrpc":"2.0","id":"7","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"AddProperty","args":["Node.FontFamily"]}}})
mcp({"jsonrpc":"2.0","id":"8","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"Set","args":["Node.FontFamily", "@obj308"]}}})

# 4. 状态机（同样 ResourceReference 类型）
# 步骤4a：在 "State Managers" 文件夹找目标 StateManager
r = mcp({"jsonrpc":"2.0","id":"9","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj47","method":"get_Children"}}})
# 找 "warning State Manager" 的 ref_id，如 @obj107

# 步骤4b：缓存 + 设置
mcp({"jsonrpc":"2.0","id":"10","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj107","method":"get_Name","args":[]}}})
mcp({"jsonrpc":"2.0","id":"11","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"AddProperty","args":["Node.StateManager"]}}})
mcp({"jsonrpc":"2.0","id":"12","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"Set","args":["Node.StateManager", "@obj107"]}}})

# 5. 自定义属性
mcp({"jsonrpc":"2.0","id":"13","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"AddProperty","args":["warning.value"]}}})
```

## TextBlock2D 可用属性

| 属性名 | 类型 | 设置方式 |
|--------|------|----------|
| TextConcept.Text | string | set_Item("TextConcept.Text", "内容") |
| FontStyleConcept.Size | float | set_Item("FontStyleConcept.Size", 36) |
| FontStyleConcept.Style | - | set_Item |
| FontStyleConcept.Weight | - | set_Item |
| FontStyleConcept.FontHintingPreference | - | set_Item |
| Node.FontFamily | ResourceReference | AddProperty → Set("Node.FontFamily", "@objXXX") |
| Node.StateManager | ResourceReference | AddProperty → Set("Node.StateManager", "@objXXX") |
| **Node2D.ForegroundBrush** | ResourceReference | AddProperty → set_Item("...", "@objXXX") 或 `KzResourceID:资源名` |
| **Node2D.BackgroundBrush** | ResourceReference | AddProperty → set_Item("...", "@objXXX") 或 `KzResourceID:资源名` |
| **Image2D.Image**（Image2D节点） | ResourceReference | set_Item("Image2D.Image", "@objXXX") 或 `KzResourceID:资源名` |
| Foreground | ResourceReference | Set |

## 文本 / 图片 / 前景色 / 背景色 设置 + ResourceID 引用原理（2026-08-07 实测打通）

老隋要求梳理文本、图片、文字前景色、文字背景色四类属性的设置，重点是 **resourceID（资源引用）** 的用法。全部在 Info 下用 4 个测试节点实测：`text`/`text_1`（TextBlock2D）与 `image`/`image_1`（Image2D）。

### 🌟 最重要的规则（老隋强调，务必记住）

> **无论你看到/想用的是 `resource:xxx`、`KzResourceID:xxx` 还是 `resourceID:xxx`，实际设置时一律写成 `KzResourceID:xxx`。**
> 使用 resource（资源引用）的形式，设置的字符串就是 **`KzResourceID:xxx`**。
> （⚠️ 不要写 `resourceID:xxx`——少 `Kz` 前缀会失败！这个坑实测踩了很久。）

### 4 节点标准示例（全部读回验证通过）

| 节点 | 类型 | 文本 | 前景色 | 背景色 | 图片 |
|------|------|------|--------|--------|------|
| **text** | TextBlock2D | `123` | `Color Brush_FFFFFF` | `Color Brush_000000` | - |
| **text_1** | TextBlock2D | `KzResourceID:123` | `KzResourceID:FFFFFF` | `KzResourceID:000000` | - |
| **image** | Image2D | - | - | - | `green_sig_num`(路径/@obj) |
| **image_1** | Image2D | - | - | - | `KzResourceID:green_sig_num` |

上面区分了两种写法：`text`/`image` 用**直接值**，`text_1`/`image_1` 用 **`KzResourceID:` resource 形式**。两者效果相同，resource 形式更通用。

### 属性名（TextBlock2D / Image2D，GetAddableProperties 确认）

- **文本内容**：`TextConcept.Text`（string）
- **文字前景色**：`Node2D.ForegroundBrush`（ResourceReference）⚠️ 需先 AddProperty
- **文字背景色**：`Node2D.BackgroundBrush`（ResourceReference）⚠️ 需先 AddProperty（不是 `Background`/`BackgroundColor`/`BackdropBrush`，那些都不存在）
- **图片**：`Image2D.Image`（ResourceReference，仅 Image2D 节点）

### 设置语法（set_Item 实测）

```python
# ================= 文本 TextConcept.Text（string）=================
# 直接值：用 @string: 前缀（裸文本会失败）
mcp kz_invoke target=@节点 method=set_Item args=["TextConcept.Text","@string:123"]   # → 显示 "123"
# resource 形式：
mcp kz_invoke target=@节点 method=set_Item args=["TextConcept.Text","KzResourceID:123"]  # → 存 "KzResourceID:123"

# ================= 前景色/背景色（ResourceReference，需先 AddProperty）=================
# 添加属性
mcp kz_invoke target=@节点 method=AddProperty args=["Node2D.ForegroundBrush"]
mcp kz_invoke target=@节点 method=AddProperty args=["Node2D.BackgroundBrush"]
# 设置（两种等价写法）：
# 写法A：直接用 @obj 刷资源对象引用（@obj5736/@obj5735 这个引用怎么获取见下方说明）
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.ForegroundBrush","@obj5736"]   # Color Brush_FFFFFF
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.BackgroundBrush","@obj5735"]   # Color Brush_000000
#    ▶ 获取颜色刷引用：Brushes 库 get_Children → Color Brush_FFFFFF = @obj5736
#      （完整流程见下方「### 资源定位（在工程里找 brush 和图片）」章节）
# 写法B：resource 形式（KzResourceID:）
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.ForegroundBrush","KzResourceID:FFFFFF"]
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.BackgroundBrush","KzResourceID:000000"]

# ================= 图片 Image2D.Image（ResourceReference，仅 Image2D 节点）=================
# 写法A：@obj 图片资源对象引用（最稳；@obj5831 这个引用怎么获取见下方说明）
mcp kz_invoke target=@节点 method=set_Item args=["Image2D.Image","@obj5831"]   # green_sig_num
#    ▶ 获取图片引用：Textures 库 → 子库 adas → get_Children → green_sig_num = @obj5831
#      （完整流程见下方「### 资源定位（在工程里找 brush 和图片）」章节）
# 写法B：resource 形式（KzResourceID:资源名）
mcp kz_invoke target=@节点 method=set_Item args=["Image2D.Image","KzResourceID:green_sig_num"]
# 写法C：完整路径字符串
mcp kz_invoke target=@节点 method=set_Item args=["Image2D.Image","Textures/adas/green_sig_num"]
```

### ResourceReference 属性（ForegroundBrush/BackgroundBrush/Image）设值规则

| 写法 | Foreground/Bg Brush | Image |
|------|:---:|:---:|
| **`KzResourceID:资源名`** | ✅ | ✅ |
| **`@obj资源对象引用`** | ✅ | ✅（最稳） |
| **完整路径** `Textures/adas/xxx` | ❌ | ✅ |
| `resourceID:xxx`（无Kz） | ❌ | ❌ |
| `@brush:`/`@image:`/`@texture:` | ❌ | ❌ |
| 相对路径 `adas/xxx` | ❌ | ❌（Null） |

> ⚠️ **读回 Null 可能是时序延迟**：设完立即读回可能显示 `< Null >`，延迟约 1 秒再读就稳定为资源名。别被瞬时 Null 误导判定失败。

### 🌟 创建 Resource 资源条目（ResourceDictionary + CreateResourceEntry，2026-08-07 v6 实测打通）

> **背景**：之前 `CreateResourceDictionary()` 返回空、拿不到对象去调 `CreateResourceEntry` 的根因，已在 **v6** 修复：`WrapResult` 增加 `ResourceDictionary` 特判（类型名含 ResourceDictionary 时 `RegisterObject` 返回对象引用，不再被当成空集合展开）。**v6 之后可用此方法在节点/页面上创建资源条目**（如颜色刷、图片）。

#### 核心流程（两步）

**第1步：在目标节点上创建（或取）ResourceDictionary**
```python
# 写法A：新建 — 节点调用 CreateResourceDictionary()
mcp kz_invoke target=/Screens/Screen/RootPage/Info/text_1 method=CreateResourceDictionary args=[]
# → 返回 ref_id = @objXXX (类型 ResourceDictionaryWrapper)

# 写法B：取已有 — 节点调用 get_ResourceDictionary()
mcp kz_invoke target=@节点 method=get_ResourceDictionary args=[]
```

**第2步：往字典里加资源条目 CreateResourceEntry(resourceID, 资源对象)**
```python
mcp kz_invoke target=@objRD method=CreateResourceEntry args=["@string:FFFFFF", "@obj9"]
```

#### ⚠️🌟 最关键的坑：resourceID 纯数字必须加 `@string:` 前缀！

> **resourceID 是数字字符串（如 `000000`）时，必须写 `@string:000000`**，否则会被插件的参数解析层 `int.TryParse` 误转成整数 `0`，导致 `CreateResourceEntry` 匹配失败报错：*"类型 System.Int32 的对象无法转换为类型 System.String"*。
> `FFFFFF` 这类含字母的不是数字，不转 int，但**统一加 `@string:` 前缀最稳**。

#### 完整实测示例（cluster_hmi，2026-08-07）

```python
# 1. 先拿到要注册的资源对象引用（颜色刷 / 图片）
#    颜色刷：Brushes 库 get_Children → Color Brush_FFFFFF = @obj9, Color Brush_000000 = @obj8
#    图片：   Textures 库 → adas 子库 → get_Children → green_sig_num = @obj384

# 2. text_1 节点：创建 RD 并加颜色刷
mcp kz_invoke target=/Screens/Screen/RootPage/Info/text_1 method=CreateResourceDictionary args=[]   # → @obj2
mcp kz_invoke target=@obj2 method=CreateResourceEntry args=["@string:FFFFFF", "@obj9"]          # ✅ (第二次报 already exists 正常)
mcp kz_invoke target=@obj2 method=CreateResourceEntry args=["@string:000000", "@obj8"]          # ✅

# 3. image_1 节点：创建 RD 并加图片
mcp kz_invoke target=/Screens/Screen/RootPage/Info/image_1 method=CreateResourceDictionary args=[] # → @obj1066
mcp kz_invoke target=@obj1066 method=CreateResourceEntry args=["@string:green_sig_num", "@obj384"] # ✅

# 4. 验证：get_Resources 应列出 KeyValuePair 条目 [resourceID, 资源名]
mcp kz_invoke target=@objRD method=get_Resources args=[]
# → name = [FFFFFF, ... Name = Color Brush_FFFFFF]
# → name = [000000, ... Name = Color Brush_000000]
# → name = [green_sig_num, ...SingleTexturePluginWrapper Name = green_sig_num]
```

#### 要点
- `CreateResourceDictionary()` 返回 `ResourceDictionaryWrapper` ref；**重复创建同 ID 的条目报 "Another entry with the same Resource ID already exists"（正常保护）**。
- 资源 ref 每次连接 Studio 动态分配，需重新定位，不能硬编码。
- **保存用正规路径**：`@studio.get_Commands()` → `GeneratedCommandInvoker` → `SaveProject(@project)`（⚠️ 不要用 `kz_save_project`，那个工具是坏的/残缺的，见 kanzi-save-export skill）。

### 🌟 创建颜色笔刷（Color Brush，2026-08-07 v6 实测打通）

> 在工程 **Brushes 库** 里新建一个颜色笔刷（Color Brush），并给它设置 RGBA 颜色。颜色刷是 UI 前景色/背景色的常用资源。

#### 核心：CreateBrush 是在 `@project`（ActiveProject）上调，不是在 BrushLibrary 上！

> ⚠️ 最容易踩的坑：`CreateBrush` 是 **Project 的方法**，不是 BrushLibrary 的方法。在 BrushLibrary 上调会报 "找不到方法 CreateBrush"。
>
> 签名（老隋提供的官方插件 API 文档）：`CreateBrush(string name, BrushLibrary parent, BrushTypeEnum brushType)`，颜色刷用 `BrushTypeEnum.COLOR`。

#### 两步流程

**第1步：创建 Color Brush**
```python
# 定位 Brushes 库（拿 BrushLibrary 引用）
mcp kz_invoke target=@project method=get_BrushLibrary        # → @obj2 (BrushLibraryPluginWrapper)

# 在 @project 上调 CreateBrush：名字, Brushes库, BrushTypeEnum.COLOR
mcp kz_invoke target=@project method=CreateBrush args=["@string:Color Brush_9BA014", "@obj2", "@enum:COLOR"]
# → 返回 ref_id = @obj49 (BrushPluginWrapper)
# 名字用 GenerateUniqueChildName；重名会自动加 _1/_2 后缀（如 Color Brush_9BA014_1）
```

**第2步：设置颜色 `Set("ColorBrush.Color", "@color:AARRGGBB")`**
```python
mcp kz_invoke target=@obj49 method=Set args=["ColorBrush.Color", "@color:#FF9BA014"]   # ✅ R155 G160 B20 A255
# @color: 前缀是 v6 新加的，解析成 System.Windows.Media.Color（WPF Color 对象）
# 读回验证：get_Item → Color 对象，再 ToString() → #FF9BA013 之类 #AARRGGBB
```

#### ⚠️🌟 关键坑

**1. `CreateBrush` 的三个必要参数**
- `name`：笔刷名，用 `@string:` 前缀（有空格）。
- `parent`：Brushes 库对象引用（`@project.get_BrushLibrary` 拿到）。
- `brushType`：**用 `@enum:COLOR`**（或 BrushType 对象引用）。裸字符串 `ColorBrush`、`@enum:ColorBrush` 都报 "找不到与参数匹配的 CreateBrush"。
  - 枚举值对照：**COLOR**(颜色刷)、CONTENT、MATERIAL、TEXTURE；枚举名要看 BrushTypeEnum。

**2. 颜色属性名是 `ColorBrush.Color`（只存在于 Color Brush）**
- 它是 `System.Windows.Media.Color` 类型（验证：`get_PropertyTypes` 里有 `name = ColorBrush.Color`，fullType 含 `System.Windows.Media.Color`）。
- **只接受 Color 值对象**，不接受字符串！试遍 `@string:#FF9BA014`、`@color:`、裸字符串、`@int:` 全报 "given value cannot be converted to studio internal property value"。
- **必须用 `@color:` 前缀传**（v6 新加，解析成 WPF Color）。

**3. ⚠️ 平台舍入：B 通道可能差 1**
- `@color:#FF9BA014`（A=FF R=9B G=A0 B=14）读回 `#FF9BA013`（B=13）。
- **原因**：WPF/Kanzi 内部 Color 走 sRGB→scRGB→sRGB 浮点往返的固有舍入，**不是 `@color:` 解析问题**。
- 验证：纯黑 `#FF000000`、纯白 `#FFFFFFFF`、纯红 `#FFFF0000` 边界色全部精确（0x00/0xFF 无舍入）；只有中间值（如 0x14=20）会舍入 ±1。
- 如需严格精确，可传相邻值补偿（如 #FF9BA01B），但一般 UI 用途差 1 可忽略。

#### 完整实测示例（cluster_hmi，2026-08-07）

```python
# 1. 拿 Brushes 库
mcp kz_invoke target=@project method=get_BrushLibrary   # → @obj2

# 2. 创建颜色刷（@project 上调 CreateBrush，BrushTypeEnum.COLOR）
mcp kz_invoke target=@project method=CreateBrush args=["@string:Color Brush_9BA014", "@obj2", "@enum:COLOR"]   # → @obj49

# 3. 设颜色 R=155 G=160 B=20 A=255（@color:AARRGGBB）
mcp kz_invoke target=@obj49 method=Set args=["ColorBrush.Color", "@color:#FF9BA014"]   # ✅ 调用成功

# 4. 读回验证（Color 对象 @obj54）
mcp kz_invoke target=@obj49 method=get_Item args=["ColorBrush.Color"]        # → @obj54 (System.Windows.Media.Color)
mcp kz_invoke target=@obj54 method=ToString args=[]                             # → #FF9BA013
mcp kz_invoke target=@obj54 method=get_A args=[]   # A=255
mcp kz_invoke target=@obj54 method=get_R args=[]   # R=155
mcp kz_invoke target=@obj54 method=get_G args=[]   # G=160
mcp kz_invoke target=@obj54 method=get_B args=[]   # B=19 (目标20, 平台舍入差1)

# 5. 保存（否则重启丢失）：@studio.get_Commands() 拿 GeneratedCommandInvoker
mcp kz_invoke target=@studio method=get_Commands   # → @obj67 (GeneratedCommandInvoker)
mcp kz_invoke target=@obj67 method=SaveProject args=["@project"]   # ✅ 保存落盘
```

#### 要点
- **`CreateBrush` 是 @project 的方法**（ActiveProject），不是 BrushLibrary！
- **brushType 用 `@enum:COLOR`**（颜色刷）；设色用 `Set("ColorBrush.Color", "@color:#AARRGGBB")`。
- **`@color:` 前缀**（v6 新加）：解析 `AARRGGBB`（8位）或 `RRGGBB`（6位，A=255），`#` 可有可无。
- 颜色刷的 BrushType 枚举：COLOR=颜色刷；Content/Material/Texture 对应其他刷子类型。
- 删除多余测试 brush：对 brush 引用调 `Delete()` 成功。
- 保存路径：`@studio.get_Commands()`（不是 @project）→ `SaveProject(@project)`。

### 🌟 创建纹理（Texture / SingleTexture，2026-08-07 v6 实测打通）

> 创建一个 `SingleTexture`（纹理）资源，并绑定图片文件。纹理是图片在工程 Textures 库里的资源项（实例是 `SingleTexturePluginWrapper`）。

#### ⚠️🌟 最关键的坑：泛型 T 必须用**完整类型名**，短名 / 错命名空间都解析失败

老隋给的是 `CreateProjectItem<SingleTexture>(name, textureLibrary)`。MCP 里泛型 T 用 `@type:` 前缀传入，**必须是完整类型名**：

| 写法 | 结果 |
|---|---|
| `@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture` | ✅ 成功 |
| `@type:SingleTexture`（短名）| ❌ 报 `Argument projectItemType must extend...` |
| `@type:Rightware.Kanzi.SingleTexture`（少 Studio.PluginInterface）| ❌ ResolveTypeByName 失败，找不到方法 |

---

#### 一、纹理创建到【文件夹下】（如 adas 文件夹）

```python
# 1. 拿 TextureLibrary + 目标文件夹（adas）引用
mcp kz_invoke target=@project method=get_TextureLibrary   # → @obj69（顶层库）
mcp kz_invoke target=@obj69 method=get_Children           # → 子库 adas = @obj221

# 2. 创建纹理（父容器 = adas 文件夹 @obj221）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture", "@string:green_sig_num", "@obj221"]
# → ✅ @obj1094，Path = Textures/adas/green_sig_num（建在文件夹 adas 下）
# 第3参(父容器)传哪个库，纹理就建在哪个库下
```

---

#### 二、纹理创建到【根目录下】（Texture 顶层）

```python
# 父容器 = 顶层 TextureLibrary @obj69（不是 adas）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture", "@string:green_sig_num_tl", "@obj69"]
# → ✅ @obj1095，Path = Textures/green_sig_num_tl（建在 Texture 顶层）
```

> **对比**：传 `@obj221`（adas 文件夹）→ `Textures/adas/xxx`；传 `@obj69`（顶层）→ `Textures/xxx`。**第 3 参（父容器）决定位置**。

---

#### 三、创建文件夹（子库）及子文件夹

> 创建纹理文件夹 = `CreateProjectItem` + 泛型 T 用 **`TextureLibrary`** 完整类型名（TextureLibrary 既是顶层库类型，也是子库/文件夹类型）。

```python
# 1. Texture 顶层建文件夹（父 = @obj69 顶层库）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.TextureLibrary", "@string:__texdir_test__", "@obj69"]
# → ✅ @obj1097，Path = Textures/__texdir_test__

# 2. 文件夹内再建子文件夹（父 = 刚建的文件夹 @obj1097）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.TextureLibrary", "@string:__sub_dir__", "@obj1097"]
# → ✅ @obj1098，Path = Textures/__texdir_test__/__sub_dir__（嵌套验证 get_Children 确认）
```

| 创建目标 | 泛型 @type: 完整类型名（只差这一处！） |
|---|---|
| 纹理 | `Rightware.Kanzi.Studio.PluginInterface.**SingleTexture**` |
| 文件夹(子库) | `Rightware.Kanzi.Studio.PluginInterface.**TextureLibrary**` |

> 结构确认：adas 的 ProjectItemType name=`TextureLibrary`，FullName=`Rightware.Kanzi.Studio.PluginInterface.TextureLibrary` → 子库就是这个类型。

---

#### 四、获取图片（不走磁盘路径，全部在 Kanzi Studio 内拿）

> ⚠️ **图片、字体等资源必须从 Kanzi Studio 里获得**（老隋强调），**不能用磁盘路径**。`ImageDirectory.GetChild("xxx.png")` 目前会报「不明确的匹配」（反射桥重载歧义），**用 `get_Children` 遍历最可靠**。

```python
# 1. 拿 ImageDirectory（图片目录）
mcp kz_invoke target=@project method=get_ImageDirectory   # → @obj882

# 2. 找图片所在子文件夹（如 adas）
mcp kz_invoke target=@obj882 method=get_Children          # → adas = @obj891

# 3. 找目标图片（green_sig_num.png）
mcp kz_invoke target=@obj891 method=get_Children          # → green_sig_num.png = @obj1071
# 图片的 get_Path = Resource Files/Images/adas/green_sig_num.png
```

#### 🌟 怎么识别 image 下的资源是【图片】还是【文件夹】（用 get_Children 逐个判断）

> 遍历 ImageDirectory 时，每项可能是图片，也可能是子文件夹（如 adas 下的 `day`/`night`）。**必须区分**，图片才建纹理，文件夹要递归进去。判断依据（两种都可靠）：

```python
# get_Children 输出里直接看 fullType 行：
#   ▪ fullType = ...ImageFilePluginWrapper     → 图片（如 acc.png）
#   ▪ fullType = ...ImageDirectoryPluginWrapper → 子文件夹（如 day）

# 或用 ProjectItemType name 判断：
mcp kz_invoke target=@ref method=get_ProjectItemType     # → 返回一个 RuntimeType 对象
mcp kz_invoke target=@它的ref method=get_Name             # → ImageFile(图片) / ImageDirectory(文件夹)
```

| 特征 | 图片文件 | 子文件夹 |
|---|---|---|
| **ProjectItemType name** | `ImageFile` | `ImageDirectory` |
| **CLR fullType** | `...ImageFilePluginWrapper` | `...ImageDirectoryPluginWrapper` |
| **名字带扩展名** `.png/.jpg/.dds` | ✅ 是 | ❌ 是文件夹 |
| **名字无扩展名**（如 day/night） | ❌ | ✅ 是 |

> **推荐判断**：先看名字有无扩展名（快），再配合 `fullType`/`ProjectItemType` 确认。枚举时遇到文件夹就**递归**进去，为里面的图片也建纹理（子文件夹结构要同步建到纹理库，见上文「创建文件夹」）。

---

#### 五、设置图片（绑定到纹理）

> 属性名是 **`TextureImage`**，不是 `SingleTexture.Image` / `Image`（那两个都不存在）。

```python
# 创建出纹理后（如 @obj1094），设 TextureImage = 图片引用
mcp kz_invoke target=@obj1094 method=Set args=["TextureImage", "@obj1071"]   # ✅ 调用成功

# 读回验证：get_Item("TextureImage") → @obj1071 (green_sig_num.png) 即成功
mcp kz_invoke target=@obj1094 method=get_Item args=["TextureImage"]
```

> 纹理可用属性（get_Properties 确认）：`TextureImage`、`ImportedFrom`、`IDInImportSource`、`GpuResourceMemoryType`、`TextureMinificationFilter`、`TextureMagnificationFilter`、`TextureFormat`、`TextureWrapMode`、`TextureAnisotropyType`、`Name`。

---

#### 六、完整流程示例（建夹→建纹理→绑图）

```python
# 前提：已定位 TextureLibrary=@obj69, adas=@obj221, ImageDirectory=@obj882, adas图=@obj891
# 1. 确认/取图片引用
green_sig_num.png = @obj1071  （得先 get_Children 遍历拿到）
# 2. 在 adas 下创建纹理
@project.CreateProjectItem("@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture", "@string:green_sig_num", "@obj221")  # → @obj1094
# 3. 绑图
@obj1094.Set("TextureImage", "@obj1071")   # ✅
# 4. 读回验证
@obj1094.get_Item("TextureImage") → @obj1071 ✅
# 5. 保存
@studio.get_Commands() → SaveProject("@project")
```

> **重名规则**（老隋强调）：同一文件夹下不能有同名纹理；重名报 `A child with the name "xxx" already exists`。不同文件夹（如 adas 与顶层）重名不冲突。创建前可用 `GenerateUniqueChildName(name)` 拿唯一名。
> 资源 ref（@obj69/@obj1094 等）每次连接 Studio 动态分配，需重新定位，不能硬编码。

### 🌟 创建字体 Font Family（FontFamily，2026-08-07 v7 实测打通）

> 在 Font Families 库里创建 `FontFamily`（字体）资源，并绑定字体文件（FontFiles = List<FontFile>）。两条链路：创建字体 + 绑字体文件。

#### 1. 定位字体相关资源
```python
@project.get_FontFamilyLibrary()   # → FontFamilyLibrary (现有字体: MiSans-Medium等) ref, 如 @obj2
@project.get_FontDirectory()        # → FontDirectory (字体文件: xxx.ttf) ref, 如 @obj9
# FontDirectory 里是字体文件: MiSans-Medium.ttf / MiSans-Regular.ttf 等
# 每个字体文件 ref 需 get_Children 遍历拿到, 如 @obj10 / @obj11
```

#### 2. 创建字体（FontFamily 完整类型名）
```python
# 泛型 T = 完整类型名 Rightware.Kanzi.Studio.PluginInterface.FontFamily
# 用法完全同纹理套路: @project.CreateProjectItem("@type:完整类型名", "@string:唯一名", 父容器Ref)
@project.CreateProjectItem(
    "@type:Rightware.Kanzi.Studio.PluginInterface.FontFamily",  # ★完整类型名(同纹理 SingleTexture 套路)
    "@string:__font_test__",        # 唯一名(重名会报 existing, 可先用 GenerateUniqueChildName)
    "@obj2")                         # 父容器 = FontFamilyLibrary (注意: 不是 get_FontDirectory! 字创建在库下)
# → @obj8 (FontFamilyPluginWrapper) ✅
# 字体属性只有 2 个: FontFiles、Name
# ⚠️ 第一参必须带 @type: 前缀 + 完整类型名; ref 每次连都变, 示例里的 @obj2/@obj8 需现场重取
```

#### 3. 绑定字体文件（FontFiles = List<FontFile>，用 @list: 前缀）
```python
# ⚠️ FontFiles 是【集合类型 List<FontFile>】，不能直接 Set 单个 @obj 引用！
# v7 起反射桥支持 @list: 前缀构造 List<T>:
#   @list:类型名@obj1,@obj2  → List<T>
#   @list:@obj1,@obj2        → List<object> (无类型名)
# 类型名 = 元素类型(接口/类), 如 Rightware.Kanzi.Studio.PluginInterface.FontFile(接口, 可收实现类型)
@obj8.Set("FontFiles", "@list:Rightware.Kanzi.Studio.PluginInterface.FontFile@obj10,@obj11")  # 绑 2 个字体 ✅
```

#### 4. 读回验证 + 保存
```python
@obj8.Get("FontFiles")  # 返回 refs 列表, 单绑 ['@obj10'], 双绑 ['@obj10','@obj11'] → 都成功!
# 注意: get_Item/Get 对集合属性只显示尾部一个(反射桥摊开), 要看完整需看返回的 refs 列表
@studio.get_Commands()  # → GeneratedCommandInvoker
invoker.SaveProject("@project")  # ✅ 保存(注意:@project 上无 SaveProject 方法, 必须走 invoker!)
```

> ⚠️ **@obj 引用每次连接/重启 Studio 动态重新编号**：上轮存的 @obj1263 在新进程里完全不同（可能指向别的对象）。每次连上后必须先用 get_FontFamilyLibrary / get_FontDirectory / get_Children 重新枚举定位，不能用旧 ref。
> **@list: 支持任意集合属性**（不只 FontFiles）：凡文档要求传 List<T> 的参数，都能用 `@list:类型名@obj1,@obj2` 构造。


### 资源定位（在工程里找 brush 和图片）

```python
# 颜色刷资源：Brushes 库（@obj113）
mcp kz_invoke target=@obj113 method=get_Children
# → Color Brush_FFFFFF = @obj5736, Color Brush_000000 = @obj5735

# 图片资源：Textures 库（@obj140）→ 子库 adas（@obj5784）
mcp kz_invoke target=@obj5784 method=get_Children
# → green_sig_num = @obj5831 (get_Path = Textures/adas/green_sig_num)
# 注意：资源 ref 每次连接 Studio 动态分配，需重新定位，不能硬编码
```

### 关键点回顾
- 文本（string）用 `@string:` 直接值，或用 `KzResourceID:`；图片/颜色（ResourceReference）用 `@obj` 或 `KzResourceID:`。
- **一律用 `KzResourceID:` 前缀**表示 resource 引用（勿用 `resourceID:`）。
- 创建普通节点用 `kz_create_node type=TextBlock2D/Image2D`（非占位符）。

## 查询

```python
# 节点属性列表
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/path/to/node","method":"get_Properties"}}})

# 可添加的属性列表
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/path/to/node","method":"GetAddableProperties"}}})
```

## ⚠️ 中文/Unicode 属性值设置注意事项

### 问题背景
通过 MCP 传参给 CreateIntProperty / CreateCustomEnumProperty 时，displayName 等字符串参数中的中文如果被转义为 `\uXXXX`（Unicode 转义序列），需要看转义的层数：

- **单层转义** `\u521b`：JSON 标准行为，Python `json.dumps(ensure_ascii=True)` 会自动转，C# 的 `UnescapeJsonString` 能正确还原
- **双重转义** `\\u521b`：Python 中先 `json.dumps` 再嵌套一次序列化，或者字符串本身已有转义序列又被再次序列化，会被错误显示为 `mcp\创建\属性\测试`

### 根因
Python → C# 的传输链路：
```
MCP Client → json.dumps(ensure_ascii=True) → 
  WebSocket → server_ws.py → httpx POST → 
  KzMCPHttpServer → manual parser → Invoke → Kanzi SDK
```
如果参数已经包含了 `\uXXXX` 这样的转义序列文字，`json.dumps` 会再转一次，导致 `\u521b` 变成 `\\u521b`（双反斜杠）。

### 解决方案

#### 方案一：传原始 UTF-8 中文（推荐）
```python
# ✅ 直接传中文字符串，不要预转义
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"CreateIntProperty","args":["mcptest.value", "mcp创建属性测试", "mcptest", 0, 255, 1]}}})

# 不需要写成："mcp\\u521b\\u5efa\\u5c5e\\u6027\\u6d4b\\u8bd5"
```

#### 方案二：用 `ensure_ascii=False`
```python
# 请求时让 json.dumps 保留中文原样
ws.send(json.dumps(req, ensure_ascii=False))
```

#### 方案三：使用原始字符串（避免嵌套序列化）
```python
# 如果从其他 AI 获取到的参数是转义过的，先用 unicode-escape 解码后再传
# Python 示例：
def fix_escaped_chinese(s):
    try:
        return s.encode().decode('unicode-escape')
    except:
        return s  # 如果已经是正常中文，直接返回
```

### 判断方法
查看 DisplayName 的值：
- `mcp创建属性测试` ✅ 正常
- `mcp\\创建\\属性\\测试` ❌ 双反斜杠乱码 — 说明传参时发生了双重转义
- `mcp\\u521b\\u5efa...` ❌ 双重 Unicode 转义 — 原始字符串还是 \uXXXX 形式

### 补救（仅限手动修复现有损坏的属性）
```python
# 对已经创建但乱码的 DisplayName，可以用 set_DisplayName 覆盖
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj333","method":"set_DisplayName","args":["mcp创建属性测试"]}}})
```

## 常见错误处理

| 错误信息 | 原因 | 解决 |
|----------|------|------|
| `对象引用 '@objXXX' 不存在或已失效` | ref 未缓存或 Studio 重启过 | 重新触发缓存（调一次 get_Name 等方法） |
| `The given value "@objXXX" was not a valid value` | ResourceReference 属性传的 @obj 未缓存 | 先 `get_Name` 触发缓存再 Set |
| `不支持的节点类型或方法` | kz_create_node/kz_delete_node 在新版插件中不可用 | 当前版本可用；如不可用则用 kz_invoke 替代 |

## 自定义属性类型 — 创建属性（Property Types）

### 获取属性类型库

```python
r = mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"get_PropertyTypeLibrary","args":[]}}})
# 返回 ref_id = @obj2

ptlib = "@obj2"  # 每次重启 Studio 后需要重新获取
```

### 1. 创建 String / Text 属性（v4 实测通过）

用 `CreateProperty` + `@type:string` 创建 string 类型属性。

`CreateProperty(Type dataType, string name, string displayName, string category)` — 4 参数（泛型 `CreateProperty<T>(name,displayName,category)` 也可）

```python
# @type:string → 解析成 System.String 类型，泛型<T> 构造成功（实测 ✅）
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"CreateProperty","args":["@type:string", "mcptest.text", "文本属性", "mcptest"]}}})
# 返回 PropertyTypePluginWrapper`1[[System.String]] 的 ref_id，即创建成功
# 等价泛型写法（若想走泛型重载）:
#   args:["mcptest.text", "文本属性", "mcptest"]  → CreateProperty<string>
```

**其他数据类型也可用 `@type:` 创建**（`@type:int`/`@type:float`/`@type:bool` 等 CLR 类型，及 `Vector2`/`Vector3` 等 Kanzi 数学类型）。

> 提示：给节点加 string 属性实例用 `AddProperty` + `@string:属性名`（见上方核心原则），这里 `CreateProperty` 是**创建属性类型**。

### 2. 创建 IntProperty

`CreateIntProperty(name, displayName, category, lowerBound, upperBound, step)` — 6 参数，**没有 Description 参数**。

**可空边界参数用 `@null`（v4 实测通过）**：

```python
# 带上界/下界/步长
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"CreateIntProperty","args":["mcptest.value", "mcp创建属性测试", "mcptest", 0, 255, 1]}}})

# 边界/步长全部不限制（传 @null）— 实测通过
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"CreateIntProperty","args":["V4Test.intNull", "Int Null", "V4Test", "@null", "@null", "@null"]}}})
# 同理 CreateFloatProperty 也可用 @null 省略 bounds
```

### 3. 创建 CustomEnumProperty

`CreateCustomEnumProperty(name, displayName, category, Dictionary<string,int>)` — 4 参数

```python
# 用 @dict:k=v,k=v 传 options（v4 实测通过）
mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"CreateCustomEnumProperty","args":["mcptest.state", "mcp创建属性测试", "mcptest", "@dict:off=0,on=1,ss=3"]}}})
# 也兼容直接传 dict: args:["...", "...", "...", {"off":0,"on":1,"ss":3}]
```

### 3b. 创建 Vector 属性（v4 实测通过）

```python
# Vector2D — @vector:x,y
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"CreateVector2DProperty","args":["V4Test.vec2","Vec2","V4Test","@vector:0,0","@vector:50,50","@vector:1,1"]}}})

# Vector3D — @vector3d:x,y,z
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"CreateVector3DProperty","args":["V4Test.vec3","Vec3","V4Test","@vector3d:0,0,0","@vector3d:10,10,10","@vector3d:1,1,1"]}}})

# Vector4 / 四元数 — @quaternion:x,y,z,w
mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"CreateVector4DProperty","args":["V4Test.quat","Quat","V4Test","@quaternion:0,0,0,1","@quaternion:0,0,0,1","@quaternion:0,0,0,0.1"]}}})
```

> 注意：没有 `CreatePointProperty` 这个 API，Point 类型用 `CreateVector4DProperty` + `@quaternion:`。

### 4. 删除属性类型

```python
# 先列出
r = mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"get_ProjectPropertyTypes","args":[]}}})
# 找到 ref_id，再删除
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":ptlib,"method":"DeleteProperty","args":["@obj333"]}}})
```

### 5. 读取属性字段值

```python
# 方法签名：get_Name, get_DisplayName, get_Category, get_Description, get_Options
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj333","method":"get_DisplayName","args":[]}}})

# 批量查看所有属性
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_ref_properties","arguments":{"ref_id":"@obj333"}}})
```

### 6. 设置 Description（单独设置）

CreateIntProperty 没有 Description 参数，创建后单独设：

```python
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj333","method":"set_Description","args":["这是一个测试属性"]}}})
```

## 调试工具

```python
# 列出所有已缓存的引用
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_list_refs","arguments":{}}})

# 查看对象可调用的方法
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_ref_methods","arguments":{"target":"@obj123"}}})

# 查看对象实现的接口
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_ref_interfaces","arguments":{"target":"@obj123"}}})

# 查看对象的属性/字段
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_ref_properties","arguments":{"target":"@obj123"}}})
```

## v4 参数标识符总表（通用，已实测）

### 基础类型

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@string:值` | 强制字符串 | `@string:123` → `"123"` |
| `@int:` / `@long:` | 强制整数 | `@int:255` |
| `@float:` / `@double:` / `@decimal:` | 强制浮点 | `@float:36` |
| `@bool:true` | 强制布尔 | `@bool:true` |
| `@byte:` / `@char:` | 字节 / 字符 | `@byte:200` |
| `@null` | 可空参数置 null | `CreateIntProperty(...,"@null")` |

### 引用 / 对象

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@obj:X` | 对象缓存引用（等价 `@objX`，target/args 均可） | `@obj:238` |
| `@node:/path` | 节点路径（target/args 均可） | `@node:/Screens/.../text` |
| `@project` / `@studio` | 工程/Studio 对象（args 已修复） | `@project` |
| `@type:名字` | .NET Type 对象 | `@type:string` |
| `@enum:名字` | 精准枚举转换 | `@enum:WHOLE_PROPERTY` |
| `@dict:k=v,k=v` | 字典（CreateCustomEnumProperty） | `@dict:off=0,on=1` |

### 向量

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@vector:x,y` | Vector2 | `@vector:0,0` |
| `@vector3d:x,y,z` | Vector3 | `@vector3d:0,0,0` |
| `@quaternion:x,y,z,w` | Vector4/四元数 | `@quaternion:0,0,0,1` |
| `@transformation2d:sx,sy,rot,tx,ty` | Transformation2D（v11 新加） | `@transformation2d:1,1,0,0,115` |

> **`@transformation2d:` 说明（v11 2026-08-13 实测打通）**：
> - 构造 `Rightware.Kanzi.Studio.PluginInterface.Transformation2D`，**不是**普通 Vector。
> - 格式：`scaleX,scaleY,rotation,tx,ty`（逗号分隔 5 个 double），对应属性原始值 `scaleX; scaleY; rotation; tx; ty`。
> - **构造函数签名是反编译 PluginInterface.dll 确认的**（非脑补）：`(System.Windows.Vector scale, double rotation, System.Windows.Vector translation)`，另有一个 `(Matrix)` 重载。
> - 用于 `Node2D.RenderTransformation` 等**只接受 Transformation2D 类型值**的属性（Kanzi 2D 节点定位就是用这个）。
> - ⚠️ **不要用 `@vector:` 或裸字符串设 RenderTransformation**：会存错类型（2 分量 Vector / string）导致读回 null，污染属性。必须用 `@transformation2d:`（详见文末「节点定位」章节）。
> - 示例：位置 X:0, Y:115（无缩放无旋转）→ `@transformation2d:1,1,0,0,115`

### 颜色（v6 新加）

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@color:AARRGGBB` | System.Windows.Media.Color（WPF Color 对象） | `@color:#FF9BA014`（R=9B G=A0 B=14 A=FF） |

> **`@color:` 说明**：
> - 解析成 `System.Windows.Media.Color`（WPF Color 对象），**不是字符串**——用于 `ColorBrush.Color` 等只接受 Color 值的属性。
> - 格式：8 位 `AARRGGBB` 或 6 位 `RRGGBB`（A 默认 255），`#` 前缀可有可无。
> - 颜色值（R/G/B）用 16 进制：`@color:#FF9BA014` = A=FF(255) R=9B(155) G=A0(160) B=14(20)。
> - ⚠️ 平台舍入：中间色值读回可能差 1（如 B=0x14→读回 0x13），边界色(00/FF)精确，非解析问题。
> - 配套：`Set("ColorBrush.Color", "@color:#FF9BA014")` 设颜色笔刷（见「创建颜色笔刷」章节）。

> **规则**：有标识 → 按标识解析；无标识 → 自动猜测兜底。

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
