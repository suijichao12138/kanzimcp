---
name: kanzi-binding
description: Kanzi Studio 动态数据绑定创建。CreateBinding 的 Property/枚举/Code 参数。绑定表达式格式。绑定查询/删除。属性 ref 的获取。
---

# Kanzi 数据绑定

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

### 接入（本机中继桥）

客户端 `kanzi-mcp-client.mjs`（workspace 根目录）：中继 `ws://123.57.85.81:58080`，channel `openclaw-main`，调用 `node kanzi-mcp-client.mjs '<tools/call 参数 JSON>'`。返回 `ref_id = @objN` 自动进缓存，重启 Studio 后编号失效须重新枚举。

### 基本请求格式

```python
{
  "jsonrpc": "2.0",           # 固定
  "id": "请求编号",           # 任意字符串
  "method": "tools/call",     # 固定
  "params": {
    "name": "kz_invoke",      # 工具名
    "arguments": {
      "target": "...",        # @objXXX 或节点路径
      "method": "...",        # 方法名
      "args": [...]           # 参数列表
    }
  }
}
```

### 特殊标识符（v4）

| 标识符 | 说明 |
|--------|------|
| `@project` | 自动注入的当前工程对象（target 与 args 均可用） |
| `@obj123` / `@obj:123` | 对象缓存引用（`@obj:` 新格式等价，每次连接 Studio 后动态分配，重启后失效） |
| `@string:` / `@int:` / `@float:` / `@bool:` / `@null` / `@enum:` / `@type:` / `@node:` / `@vector:` / `@vector3d:` / `@quaternion:` / `@dict:` | v4 参数标识符（见文末总表） |

### 对象缓存机制

`@objXXX` 必须先进入 `_objectStore` 缓存才能使用。通过 `kz_invoke` 调用一个对象上的方法就能触发缓存。

下面的调用统一走 `kz_invoke`（工具名，参数遵循 v4 标识符 @type/@int/@string/@enum/@obj/@color 等）。

## CreateBinding 签名

```
CreateBinding(Property property, AnimationTargetPropertyAttributeEnum attribute, string code)
CreateBinding(Property property, AnimationTargetPropertyAttributeEnum attribute, string code, BindingTypeEnum bindingMode)   // 4参重载
CreateBinding(Property property, AnimationTargetPropertyAttributeEnum attribute, string code, BindingTypeEnum bindingMode, NodeReferenceBase pushTarget)  // 5参重载
```

### 参数说明

| 参数 | 说明 |
|------|------|
| property | 目标节点上要绑定的属性对象（从 get_Properties 获取 @obj ref） |
| attribute | 属性字段枚举（通常是 `@enum:WHOLE_PROPERTY`） |
| code | 绑定表达式，用 `@string:` 强制字符串（如 `@string:{#Info/warning.value}`） |
| bindingMode | **（可选）绑定模式枚举，默认 ONE_WAY（单向）** |
| pushTarget | **（可选）TO_SOURCE 模式下的推送目标节点引用** |

> ✅ **v4 实测**：三个必填参数推荐用标识符 `@obj:属性ref` + `@enum:WHOLE_PROPERTY` + `@string:{#code}`，避免枚举/字符串被误解析。
> ⚠️ **双向绑定**：需要 TWO_WAY 时用 4 参重载 `args=["@obj:属性ref", "@enum:WHOLE_PROPERTY", "@string:{#code}", "@enum:TWO_WAY"]`。

### `BindingTypeEnum` 枚举（官方文档）

| 值 | 含义 |
|----|------|
| 0 | NONE |
| **1** | **ONE_WAY（单向，默认）** |
| 2 | TWO_WAY（双向） |
| 3 | TO_SOURCE（反向推送） |
| 4 | EXPRESSION |
| 5 | ANIMATION |

### 枚举值 `AnimationTargetPropertyAttributeEnum`

> ⚠️ **数值必须按官方文档（2026-10-14 kanzidocmcp 核对修正）**。旧版把 SCALE 和 ROTATION 的数字写反了！

| 值 | 含义 |
|----|------|
| -1 | NONE |
| 0 | TRANSLATION_X |
| 1 | TRANSLATION_Y |
| 2 | TRANSLATION_Z |
| **3** | **SCALE_X** |
| **4** | **SCALE_Y** |
| **5** | **SCALE_Z** |
| **6** | **ROTATION_Z** |
| **7** | **ROTATION_Y** |
| **8** | **ROTATION_X** |
| **9** | **WHOLE_PROPERTY（最常用，操作整个属性值）** |
| 10 | COLOR_R |
| 11 | COLOR_G |
| 12 | COLOR_B |
| 13 | COLOR_A |

> 建议直接用 `@enum:WHOLE_PROPERTY` / `@enum:SCALE_X` 等符号名，**避免手写数字出错**。
> 官方文档：`kanzi-studio-plugin-api` → `AnimationTargetPropertyAttributeEnum`（a00260 页）。
> ⚠️ 注意：这是**插件侧**枚举（CreateBinding 用），和运行时 API 的 `PropertyField` 枚举数值**不同**（运行时 Whole=0/TranslationX=1…），别混。

## 完整流程

```python
# ===== 第1步：确保目标属性已在节点上 =====
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"AddProperty","args":["warning.value"]}}})

# ===== 第2步：获取节点属性列表，找到目标属性的 ref_id =====
r = mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"get_Properties"}}})
# 从 r 的返回值中提取 warning.value 对应的 ref_id
# 解析示例：返回文本如 "▪ ref_id = @obj10 ... name = warning.value" 则 ref_id=@obj10

# ===== 第3步：缓存属性 ref =====
# 发一个 get_Name 调用来确保 @obj10 在 _objectStore 中
mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj10","method":"get_Name","args":[]}}})
# 返回 "warning.value" 即确认缓存成功

# ===== 第4步：创建绑定 =====
# 三个参数用 v4 标识符：@obj: 属性ref + @enum:WHOLE_PROPERTY + @string:code
mcp({"jsonrpc":"2.0","id":"4","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"CreateBinding","args":["@obj:" + obj10num, "@enum:WHOLE_PROPERTY", "@string:{#Info/warning.value}"]}}})
# 成功返回：BindingWrapper 的 ref_id，如 @obj11
# 注释: @obj:10 = @obj10 新格式; obj10num 为去掉 @obj 前缀后的数字
# 也兼容旧写法: args:["@obj10", 9, "{#Info/warning.value}"]
```

## 查询绑定

```python
# 列出节点所有绑定
r = mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"get_Bindings"}}})

# 从返回中找到绑定对象的 ref_id（如 @obj11）
# 查看绑定的属性
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj11","method":"get_Property"}}})
# 查看绑定的 code
mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj11","method":"get_Code"}}})
# 查看绑定的类型/开关
mcp({"jsonrpc":"2.0","id":"4","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj11","method":"get_BindingType"}}})
mcp({"jsonrpc":"2.0","id":"5","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj11","method":"get_IsBindingEnabled"}}})
```

### Binding 接口其它可查属性（官方文档，2026-10-14 补充）

| 方法 | 返回 | 说明 |
|------|------|------|
| `get_Property` | Property | 绑定的目标属性 |
| `get_Code` | string | 绑定表达式 |
| `get_BindingType` | BindingTypeEnum | 绑定方向（ONE_WAY/TWO_WAY/…） |
| `get_IsBindingEnabled` | bool | 是否启用 |
| `get_IsCodeValid` | bool | 表达式是否合法（诊断用） |
| `get_IsBindingActive` | bool | 绑定当前是否生效 |
| `get_PropertyAttribute` | AnimationTargetPropertyAttributeEnum | 绑定的属性字段 |

## 删除绑定

```python
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"DeleteBinding","args":["@obj12"]}}})
```

## 注意事项

### ⚠️ ref 格式 — 常见陷阱
- `get_Properties` 返回的 ref_id 是 `@obj10` 格式（含 "obj" 前缀）
- **传参时必须写完整 `@obj10`，不要丢掉 `obj` 变成 `@10`**
- 脚本解析 ref_id 时：
  ```python
  # ✅ 正确
  m = re.search(r'@obj(\d+)', line)
  ref = '@obj' + m.group(1)
  
  # ❌ 错误 — 会变成 @10 而不是 @obj10
  ref = '@' + m.group(1)
  ```

### ⚠️ 必须先 AddProperty
- CreateBinding 前必须确保目标属性已在节点上（先 AddProperty）
- Studio 重启后所有 ref 失效，需要重新获取

### ⚠️ 绑定表达式语法 — 斜杠 vs 点号（2026-10-14 文档核对澄清）

**两条规则分开记，之前混在一起了：**

**① 节点路径分隔用斜杠 `/`**
- ✅ `{#Info/warning.value}` —— 别名 + 斜杠 + 属性（Kanzi 标准）
- ✅ `{../Camera/Fov}` —— 相对路径 + 斜杠 + 属性
- ❌ ~~`{#Info.warning.value}`~~ —— 节点路径里用点号不可用

**② 属性字段（property field）用点号 `.`**
- ✅ `{@../Box/LayoutTransformation}.scaleY` —— 花括号外点号取字段
- ✅ `x = {@./Node3D.RenderTransformation}.translationX`
- ✅ `getCurrentValue().translationX`
- 所以「点号」本身不是不能用，是**用错位置**（当路径分隔符才错；当字段访问就对）

**变换属性字段名对照（官方）：**

| 字段 | 名称（花括号外点号） |
|------|------|
| 2D/3D 位移 X | `x` / `translationX` |
| 位移 Y | `y` / `translationY` |
| 位移 Z | `z` / `translationZ` |
| 缩放 X | `scaleX` |
| 缩放 Y | `scaleY` |
| 缩放 Z | `scaleZ` |
| 3D 旋转（四元数） | `rotation` |
| 2D 绕 Z 旋转 | `rotationZ` |

**通用字段**：非颜色/变换属性用 `N` 或 `VectorN`（N=X/Y/Z/W）。

## 绑定表达式格式参考（官方语法）

### ① 属性绑定 `{[path]/[property]}`
```python
# 绑定当前节点自身属性（@ 符号=校验路径+跟随移动）
"{@./Node.Width}"

# 绑定父级/兄弟节点属性
"{@../Camera/Fov}"
"{../Camera/Fov}"          # 不带 @ 则不跟踪节点移动
"{@../Box/LayoutVerticalMargin}"

# 相对路径 + 别名 + 运算符混合
"{@../Camera/Fov} * {../Box/RenderTransformation}.scaleX"
"{#MainCamera/Fov} * {../Box/RenderTransformation}.scaleX"
```

> **`@` 符号的作用**：① 校验路径是否有效（无效在 Binding Editor 报错）② 源/目标节点在节点树中移动时自动更新路径 ③ **只能在同一个 prefab 内用 @，不能跨 prefab**。

### ② 别名绑定 `{#[aliasName]/[property]}`（已实测）
```python
# 绑定别名指向节点的属性
"{#Info/warning.value}"
"{#Grid/Node.Width}"
```

### ③ 属性字段绑定（点号）
```python
"{@../Image/Node2D.RenderTransformation}.x"
"{../Box/LayoutTransformation}.scaleY"
"{@../Camera/Fov} * {../Box/RenderTransformation}.scaleX"
```

### ④ 变量 / 注释 / 运算符
```python
# 注释用 # 开头
A = 2.0
B = 4
(A < B) ? A : B          # 条件运算 ? :
mod(23, 27)              # 函数
({../Camera/Fov} + {../Box/RenderTransformation}.scaleX) / 2   # 括号分组
```

### ⑤ 临时变量（material type 绑定专用）
```python
# 引用同 material type 里临时变量绑定的结果
"{##Self/[targetPropertyName]}"
```

### ⑥ 修改当前属性值时用 getCurrentValue()
```python
# 绑定表达式要修改当前目标属性的值时，不能直接引用目标属性，必须用 getCurrentValue()
"getCurrentValue().translationX + 10"
```

### ⑦ 类型规则（官方）
- **只能绑定相似数据类型**：color→color、vector2→vector2 等
- 绑定取**最后一个表达式**的值
- int/float/bool 之间**隐式转换**（取决于目标属性类型）；字符串转换**显式**
- 四个基本类型互转：integer / float / boolean / string

### ⑧ 完整示例（Info 上已有，带转换）
```python
"#A = {#Info/sys.ignState}\n#MOD(CLAMP(0,1,ABS(A-(1)))+1,2)\nA = {#Info/charge.state}"
```

## 常见错误处理

| 错误信息 | 原因 | 解决 |
|----------|------|------|
| `调用线程无法访问此对象，因为另一个线程拥有该对象` | 在非 UI 线程调用了线程敏感方法（如 CreateBinding） | ✅ 新版已修：所有反射调用统一调度到 UI 线程执行，不再报此错 |
| code 为 null 或空 | `{#...}` 被当成节点路径解析 | ✅ 新版已修：绑定表达式（`{` 开头）不再被误判为节点路径，保留 code 原字符串 |
| `找不到与参数匹配的方法` | ref 格式错误（@10 而非 @obj10） | 检查 ref 组装代码，用完整 `@obj10` |
| `Cannot find item`（找不到项） | 绑定里的相对路径/别名指向了不存在的节点 | 检查路径；用 `@` 前缀让 Studio 校验路径有效性 |
| `Invalid argument data type` | 函数参数类型不对（如 rotateX 传了整数） | 查函数签名；rotateX 第一参要是属性字段，第二参整数 |
| `The attribute is not a valid property field` | 属性用了不存在的字段名（如 LayoutTransformation 没有 Translation） | 用 `translationX/Y/Z`、`scaleX/Y/Z` 等正确字段名 |
| `Invalid result data type` | 函数返回值类型与目标属性不匹配 | 改目标属性/字段支持返回类型（如 ROTATION 支持四元数） |
| `Cannot use target property in the binding expression` | 表达式里直接引用了目标属性（自己绑自己） | 用 `getCurrentValue()` 取当前值 |
| `Assign a value to the identifier before you use it` | 变量未赋值就使用 | 先 `A = ...` 赋值再引用 |

## 调试工具

```python
# 查看对象可调用的方法
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_ref_methods","arguments":{"target":"@obj123"}}})

# 查看对象实现的接口
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_ref_interfaces","arguments":{"target":"@obj123"}}})
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
| `@null` | 可空参数置 null | `...,"@null"` |

### 引用 / 对象

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@obj:X` | 对象缓存引用（等价 `@objX`，target/args 均可） | `@obj:10` |
| `@node:/path` | 节点路径（target/args 均可） | `@node:/Screens/.../text` |
| `@project` / `@studio` | 工程/Studio 对象（args 已修复） | `@project` |
| `@type:名字` | .NET Type 对象 | `@type:string` |
| `@enum:名字` | 精准枚举转换 | `@enum:WHOLE_PROPERTY` |
| `@dict:k=v,k=v` | 字典 | `@dict:off=0,on=1` |

### 向量

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@vector:x,y` | Vector2 | `@vector:0,0` |
| `@vector3d:x,y,z` | Vector3 | `@vector3d:0,0,0` |
| `@quaternion:x,y,z,w` | Vector4 | `@quaternion:0,0,0,1` |

> **规则**：有标识 → 按标识解析；无标识 → 自动猜测兜底。
