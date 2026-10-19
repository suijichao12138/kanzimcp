---
name: kanzi-binding-expr
description: Kanzi 绑定表达式完整语法（官方参考）。运算符、函数、注释规则、属性/别名/字段引用、类型与构造函数。创建绑定的具体流程见 kanzi-binding。
---

# 绑定表达式完整规则

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

