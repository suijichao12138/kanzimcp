---
name: kanzi-binding
description: Kanzi Studio 动态数据绑定创建。CreateBinding 的 Property/枚举/Code 参数。绑定表达式格式。绑定查询/删除。属性 ref 的获取。
---

# Kanzi 数据绑定

> 📖 **属性查询指引**：具体属性的绑定表达式写法（属性名去空格驼峰、路径写法）统一查 **`kanzi-properties-all`**（合并全量版，含绑定写法）+ 常驻 **`kanzi-properties-highfreq`**（39 高频属性）。绑定表达式语法本身见本 skill 的「绑定表达式完整规则」章节。

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

## 绑定表达式完整规则（官方参考，2026-10-14 kanzidocmcp 核对）

> 官方文档：`docs.kanzi.com → Working with → Bindings → Bindings expressions reference`（4.1.0）。本节是**完整语法参考**：注释、`@` 含义、运算符、类型、全部可用函数。

### ① 注释规则
- 注释用 **`#` 开头**，写到该行末尾，可独立成行也可跟在表达式后：
```python
# 这是注释
A = 2.0        # 行尾注释
#MOD(CLAMP(0,1,ABS(A-(1)))+1,2)   # 整行注释掉的表达式
```
- 绑定表达式里**多个语句用换行 `\n` 分隔**（CreateBinding 的 code 里写 `\n`）。

### ② `@` 符号代表什么
`@` 出现在 `{[path]/[property]}` 花括号里的**路径开头**，作用是：

| 作用 | 说明 |
|------|------|
| **校验路径** | 路径无效时 Binding Editor 直接报错（不带 @ 则只在运行期失效） |
| **跟随移动** | 源/目标节点在节点树里移动时，绑定路径自动更新 |
| **限同 prefab** | 只能引用**同一个 prefab** 内的节点，不能跨 prefab |

- `{@./Node.Width}` —— 当前节点自身（`./` 相对路径）
- `{@../Camera/Fov}` —— 父级下的兄弟节点
- 不带 @：`{../Camera/Fov}` 只按路径取值，**不校验、不跟随移动**。
- 别名绑定用 `{#别名/属性}`（`@` 和 `#` 是两套前缀：`@`=相对路径，`#`=别名）。
- ⚠️ 注意区分：**MCP v4 参数标识符里的 `@string:`/`@obj:`/`@enum:` 是调用层语法**，跟绑定表达式里的 `@` 不是一回事。

### ③ 属性绑定 / 别名 / 字段
```python
"{@../Camera/Fov}"                          # 相对路径绑定
"{#Info/warning.value}"                     # 别名绑定（已实测）
"{@../Image/Node2D.RenderTransformation}.x"  # 花括号外点号取字段
"getCurrentValue().translationX + 10"        # 修改当前属性值必须用 getCurrentValue()
"{##Self/[targetPropertyName]}"              # material type 临时变量引用
```

### ④ 运算符（完整列表）

| 类别 | 运算符 | 说明 |
|------|--------|------|
| 赋值 | `=` | 给变量/标识符赋值 |
| 条件 | `? :` | 三目：`(A < B) ? A : B` |
| 括号 | `()` | 分组、函数调用、类型构造 |
| 算术 | `+ - * /` | 加减乘除 |
| 比较 | `== != > < >= <=` | 相等/不等/大小 |
| 逻辑 | `&& \|\| !` | 与 / 或 / 非 |
| 位运算 | `~ & \| ^ << >>` | 按位非/与/或/异或/左移/右移 |

- 支持**变量**：`A = 2.0` 后可用 `A`；未赋值就使用报 `Assign a value to the identifier before you use it`。
- 绑定取**最后一个表达式**的值。

### ⑤ 类型与构造函数

| 类型 | 构造语法 | 说明 |
|------|----------|------|
| Color4 | `Color4(r, g, b, a)` | 颜色（也可用 float/Vector4 隐式转换） |
| Vector2 | `Vector2(x, y)` | 二维向量 |
| Vector3 | `Vector3(x, y, z)` | 三维向量 |
| Vector4 | `Vector4(x, y, z, w)` | 四维向量（四元数） |
| Matrix3 | `Matrix3(m0..m8)` | 3x3 矩阵（9 个数） |
| Matrix4 | `Matrix4(m0..m15)` | 4x4 矩阵（16 个数） |
| Srt2D | `Srt2D(scaleX, scaleY, rotation, translationX, translationY)` | 2D 变换（缩放/旋转/位移） |
| Srt3D | `Srt3D(...)` | 3D 变换 |
| bool / int / float / string | 字面量 | 基本类型 |

- **类型规则**：只能绑定相似数据类型（color→color、vector2→vector2）；int/float/bool 隐式转换；字符串转换显式；绑定取最后表达式值。
- 小写 `color4`/`vector2`/`matrix3x3` 等也可用（与类型构造同名）。

### ⑥ 数学函数

| 函数 | 语法 | 说明 |
|------|------|------|
| **abs** | `abs(value)` | 绝对值（int/float/Color4/Vector2-4） |
| **ceil** | `ceil(value)` | 向上取整（≥参数的最近整数） |
| **floor** | `floor(value)` | 向下取整（≤参数的最近整数） |
| **round** | `round(value)` | 四舍五入取最近整数 |
| **clamp** | `clamp(low, high, value)` | 约束到 [low, high]，= `min(max(value, low), high)`；向量/颜色分量级约束 |
| **min** | `min(value1, value2)` | 取较小值；向量/颜色分量级 |
| **max** | `max(value1, value2)` | 取较大值；向量/颜色分量级 |
| **mod** | `mod(value1, value2)` | 取模（数学模运算） |
| **rem** | `rem(value1, value2)` | 取余（向零取整的余数） |
| **pow** | `pow(n, e)` | 幂运算 n^e |
| **sqrt** | `sqrt(n)` | 平方根（int 入参返回 float） |

### ⑦ 插值函数

| 函数 | 语法 | 说明 |
|------|------|------|
| **mix** | `mix(value1, value2, weight)` | 线性混合/插值 |
| **step** | `step(threshold, value)` | 阶跃：value < threshold → 0，否则 1 |
| **linearStep** | `linearStep(low, high, value)` | = `clamp(0, 1, (value-low)/(high-low))`，把 value 从 [low,high] 映射到 [0,1] |
| **smoothStep** | `smoothStep(low, high, value)` | 平滑阶跃插值（缓入缓出） |
| **smootherStep** | `smootherStep(value)` | 更平滑的阶跃（6 次多项式） |

### ⑧ 三角函数

| 函数 | 语法 | 说明 |
|------|------|------|
| **sin** | `sin(value)` | 正弦，返回 float（-1..1） |
| **cos** | `cos(value)` | 余弦，返回 float（-1..1） |
| **tan** | `tan(value)` | 正切，返回 float |
| **asin** | `asin(value)` | 反正弦，返回**角度（度）** |
| **acos** | `acos(value)` | 反余弦，返回**角度（度）** |
| **atan** | `atan(value)` | 反正切，返回**角度（度）** |
| **atan2** | `atan2(value1, value2)` | 双参反正切，返回**角度（度）** |
| **sinc** | `sinc(value)` | 非归一化辛格函数：value=0 时 1，否则 sin(rad)/rad |

> ⚠️ 反三角函数（asin/acos/atan/atan2）返回**度**，不是弧度；sin/cos/tan 的入参是**度**（文档未标但 Kanzi 惯例为度）。

### ⑨ 特殊/控制函数

| 函数 | 语法 | 说明 |
|------|------|------|
| **acquire** | `acquire(resourceId)` | 按资源 ID 获取资源（须在节点资源字典中） |
| **animate** | `animate(...)` | 绑定到 Animation Data 的分段函数（piecewise function） |
| **continueIf** | `continueIf(condition)` | 条件为真才继续执行绑定；用于数据源无效时跳过更新 |
| **format** | `format(formatString, args...)` | 格式化值为字符串（TextBlock 显示用） |
| **getCurrentValue** | `getCurrentValue()` | 取目标属性当前值（改自己属性时必须用它） |
| **getField** | `getField(matrix, index)` | 取向量/矩阵第 index 个元素（float） |
| **setField** | `setField(matrix, index, value)` | 设向量/矩阵元素 |
| **getRow** | `getRow(matrix, index)` | 取矩阵第 index 行向量（Matrix3→Vector3，Matrix4→Vector4） |
| **setRow** | `setRow(matrix, index, vector)` | 设矩阵行向量 |
| **getColumn** | `getColumn(matrix, index)` | 取矩阵第 index 列向量 |
| **setColumn** | `setColumn(matrix, index, vector)` | 设矩阵列向量 |

### ⑩ 纹理查询函数（texture 资源）

| 函数 | 返回 | 说明 |
|------|------|------|
| `textureGetWidth(texture)` | integer | 纹理宽；非纹理返回 -1 |
| `textureGetHeight(texture)` | integer | 纹理高；非纹理返回 -1 |
| `textureGetSize(texture)` | Vector2 | 纹理尺寸；非纹理返回 (-1, -1) |
| `textureGetPixelFormat(texture)` | integer | 像素格式（GraphicsFormat 枚举值）；非纹理返回 -1 |
| `textureGetAnisotropyLevel(texture)` | integer | 各向异性等级 2/4/8/16；无则 0 |
| `textureGetFilterMode(texture)` | integer | 过滤模式 |
| `textureGetMipmapMode(texture)` | integer | mipmap 模式（0=Base，1=...） |
| `textureGetAddressingMode(texture)` | integer | 寻址模式 |
| `textureGetDepthCompareFunction(texture)` | integer | 深度比较函数；0=无 |

### ⑪ 完整示例（Info 上已有，带转换）
```python
"#A = {#Info/sys.ignState}\n#MOD(CLAMP(0,1,ABS(A-(1)))+1,2)\nA = {#Info/charge.state}"
# 等价写法：
"# 注释\nA = {#Info/sys.ignState}\nB = CLAMP(0, 1, ABS(A - 1)) + 1\nMOD(B, 2)"
```

> ⚠️ 函数名大小写不敏感（`CLAMP`/`clamp` 均可，官方示例两种都有）；`? :` 三目、`#` 注释、`\n` 换行语句是编写 code 时的核心规则。

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