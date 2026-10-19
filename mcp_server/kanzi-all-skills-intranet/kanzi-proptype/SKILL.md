---
name: kanzi-proptype
description: Kanzi 创建自定义属性类型（Property Types / DynamicProperty）：AddDynamicPropertyType、属性类型创建与使用。
---

## 自定义属性类型 — 创建属性（Property Types）

### 获取属性类型库

```python
r = mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"get_PropertyTypeLibrary","args":[]}}})
# 返回 ref_id = @obj2

ptlib = "@obj2"  # 每次 Studio 重启（仅人工操作，助手绝不重启）后需要重新获取
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
