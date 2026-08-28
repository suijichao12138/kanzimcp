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
```

### 参数说明

| 参数 | 说明 |
|------|------|
| property | 目标节点上要绑定的属性对象（从 get_Properties 获取 @obj ref） |
| attribute | 属性字段枚举（通常是 `@enum:WHOLE_PROPERTY`） |
| code | 绑定表达式，用 `@string:` 强制字符串（如 `@string:{#Info/warning.value}`） |

> ✅ **v4 实测**：三个参数推荐用标识符 `@obj:属性ref` + `@enum:WHOLE_PROPERTY` + `@string:{#code}`，避免枚举/字符串被误解析。

### 枚举值 `AnimationTargetPropertyAttributeEnum`

| 值 | 含义 |
|----|------|
| -1 | NONE |
| 0 | TRANSLATION_X |
| 1 | TRANSLATION_Y |
| 2 | TRANSLATION_Z |
| 3 | ROTATION_X |
| 4 | ROTATION_Y |
| 5 | ROTATION_Z |
| 6 | SCALE_X |
| 7 | SCALE_Y |
| 8 | SCALE_Z |
| **9** | **WHOLE_PROPERTY（最常用，操作整个属性值）** |

> 可用 `@enum:WHOLE_PROPERTY` 精准转换，或直接传数字 `9`（两者等价）。

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

### ⚠️ 绑定表达式中的 `/`
- ✅ **正确格式**: `{#Info/warning.value}`（**斜杠**路径）—— Kanzi 标准绑定语法，**必须用斜杠**
- ❌ ~~`{#Info.warning.value}`（点号路径）~~ —— **点号格式不对/不可用**，不要用
- **当前版本已修复**: `{#...}` 绑定表达式（`{` 开头）不会被误判为节点路径

## 绑定表达式格式参考

```python
# 简单绑定 — 直接引用另一个属性值
"{#Info/warning.value}"

# 带转换的绑定（Info 上已有的绑定示例）
"#A = {#Info/sys.ignState}\n#MOD(CLAMP(0,1,ABS(A-(1)))+1,2)\nA = {#Info/charge.state}"
```

## 常见错误处理

| 错误信息 | 原因 | 解决 |
|----------|------|------|
| `调用线程无法访问此对象，因为另一个线程拥有该对象` | 在非 UI 线程调用了线程敏感方法（如 CreateBinding） | ✅ 新版已修：所有反射调用统一调度到 UI 线程执行，不再报此错 |
| code 为 null 或空 | `{#...}` 被当成节点路径解析 | ✅ 新版已修：绑定表达式（`{` 开头）不再被误判为节点路径，保留 code 原字符串 |
| `找不到与参数匹配的方法` | ref 格式错误（@10 而非 @obj10） | 检查 ref 组装代码，用完整 `@obj10` |

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
