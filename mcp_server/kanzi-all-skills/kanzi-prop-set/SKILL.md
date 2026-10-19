---
name: kanzi-prop-set
description: Kanzi 属性增删改查：set_Item/get_Item/AddProperty/RemoveProperty、批量操作、查询、中文Unicode值设置、常见错误处理。含图片/九宫格设置（Image2D.Image、NinePatchImage2D.Image*）。
---

## 核心原则

### 对齐枚举速查（Node.HorizontalAlignment / Node.VerticalAlignment）
> 对齐是**枚举属性**，设置**必须 `@int:`**（不支持 `@enum:`/裸字符串）。枚举值对照表（老隋提供，2026-08-19）：

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
| `对象引用 '@objXXX' 不存在或已失效` | ref 未缓存或 Studio 重启过（**仅人工**，助手绝不重启） | 重新触发缓存（调一次 get_Name 等方法） |
| `The given value "@objXXX" was not a valid value` | ResourceReference 属性传的 @obj 未缓存 | 先 `get_Name` 触发缓存再 Set |
| `不支持的节点类型或方法` | kz_create_node/kz_delete_node 在新版插件中不可用 | 当前版本可用；如不可用则用 kz_invoke 替代 |


## 图片 / 九宫格设置

> 给 Image2D / 九宫格节点**直接设置图片**（图片路径/图片名），不涉及资源概念。节点创建见 `kanzi-node-create`。

### Image2D 节点设置图片

```python
# Image2D.Image 属性（Image2D 节点自带，无需 AddProperty）
# 方式1：直接给图片路径（Textures 库里的图片）
mcp kz_invoke target=@image_1 method=set_Item args=["Image2D.Image", "Textures/adas/green_sig_num"]
# 方式2：直接给图片名
mcp kz_invoke target=@image_1 method=set_Item args=["Image2D.Image", "green_sig_num"]
```

### 九宫格节点设置 9 块图片

> 九宫格节点创建见 `kanzi-node-create`（类型 NinePatchImage2D）。9 块图属性创建节点时就自带（无需 AddProperty），直接设图片即可。

```python
# 9 块图属性：ImageTopLeft/Top/TopRight/Left/Center/Right/BottomLeft/Bottom/BottomRight
# 方式1：直接给图片路径（Textures 库里的图片）
mcp kz_invoke target=@bg_9slice method=set_Item args=["NinePatchImage2D.ImageTopLeft", "Textures/adas/green_sig_num"]
# 方式2：直接给图片名
mcp kz_invoke target=@bg_9slice method=set_Item args=["NinePatchImage2D.ImageCenter", "center_tex"]
# 其余 7 块同理（Top/TopRight/Left/Right/BottomLeft/Bottom/BottomRight）
```

### 图片来源（Textures 库）

```python
# Textures 库 → 子库 → 图片（拿路径/名字）
mcp kz_invoke target=@project method=get_Children   # 找 "Textures" 行 → 库引用
mcp kz_invoke target=<Textures库> method=get_Children  # 子库 → 子库引用
mcp kz_invoke target=<子库> method=get_Children     # → green_sig_num（get_Path = Textures/adas/green_sig_num）
# 注意：图片引用每次连接 Studio 动态分配，需重新定位，不能硬编码
```

> 创建纹理/图片 → `kanzi-asset-create` skill。
> 设置颜色/字体等资源引用 → `kanzi-resource-set` skill。
