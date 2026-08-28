---
name: kanzi-save-export
description: Kanzi Studio 工程保存和 kzb 导出操作。通过 GeneratedCommandInvoker（@studio.get_Commands 获取）执行 SaveProject(Project) 和 ExportBinary(Project) 命令。
---

# Kanzi Studio 保存 & 导出

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



> ⚠️ **不要用 `kz_save_project` 工具保存！** 该工具分派到 `SaveProject()` 内部找 `Save` 方法反射不到（@project 包装类型无公开 Save），落到 `ExecuteCommand("Save")` fallback 又反射不到 `ExecutePluginCommand`，报 "找不到 ExecutePluginCommand"。**正确保存方式如下（通过 GeneratedCommandInvoker）**。

## 概述

Kanzi ProjectPluginWrapper 没有直接暴露 Save/ExportKZB 方法。保存和导出操作通过 `@studio` 的 `Commands` 属性（`GeneratedCommandInvoker` 类型）执行。

## 执行流程

### 第1步：获取命令执行器

通过 `@studio.get_Commands()` 获取 `GeneratedCommandInvoker` 对象。

```python
r = mcp({
    "jsonrpc": "2.0", "id": "1",
    "method": "tools/call",
    "params": {
        "name": "kz_invoke",
        "arguments": {
            "target": "@studio",
            "method": "get_Commands",
            "args": []
        }
    }
})
```

返回示例：
```json
{
  "ref_id": "@obj706",
  "type": "GeneratedCommandInvoker",
  "fullType": "Rightware.Kanzi.Tool.ApplicationCommon.Plugin.GeneratedCommandInvoker"
}
```

**注意**：ref_id 每次连接或不同上下文可能变化，需要动态获取，不要硬编码。

### 第2步：保存工程

使用 `SaveProject(Project)` 方法，参数传 `@project`。

```python
r = mcp({
    "jsonrpc": "2.0", "id": "2",
    "method": "tools/call",
    "params": {
        "name": "kz_invoke",
        "arguments": {
            "target": "@obj:706",      # GeneratedCommandInvoker 的 ref（新格式 @obj: 等价 @obj706）
            "method": "SaveProject",
            "args": ["@project"]       # @project 自动解析为当前工程对象（v4 已修复 args 解析）
        }
    }
})
```

成功返回：`✅ 调用成功（无返回值）`

> ✅ **v4 实测确认**：`@project` 作为 `args` 参数现在能正确解析成工程对象（此前会当字符串导致"找不到与参数(String)匹配"）；`@obj:` 新格式 target 与 `@obj706` 等价可用（v4 已加归一化）。

### 第3步：导出 kzb

使用 `ExportBinary(Project)` 方法。

```python
r = mcp({
    "jsonrpc": "2.0", "id": "3",
    "method": "tools/call",
    "params": {
        "name": "kz_invoke",
        "arguments": {
            "target": "@obj:706",
            "method": "ExportBinary",
            "args": ["@project"]
        }
    }
})
```

成功返回：`✅ 调用成功（无返回值）`

## 完整 Python 示例

```python
# 本机中继桥：通过 ws://123.57.85.81:58080 调用 kz_invoke（客户端 kanzi-mcp-client.mjs）
# 调用：node kanzi-mcp-client.mjs '{"name":"kz_invoke","arguments":{"target":...,"method":...,"args":[...]}}'
# 下面 mcp({...}) 调用 = 对中继桥 kz_invoke 工具的一次调用（tools/call JSON-RPC）。
# 说明：此例保留了手动 tools/call 结构，仅作底层反射调用参考；日常用 kanzi-mcp-client.mjs 只需传 tools/call 参数 JSON。

# 1. 获取命令执行器
r = mcp({
    "jsonrpc": "2.0", "id": "1",
    "method": "tools/call",
    "params": {
        "name": "kz_invoke",
        "arguments": {
            "target": "@studio",
            "method": "get_Commands",
            "args": []
        }
    }
})

lines = r["result"]["content"][0]["text"]
m = re.search(r'@obj(\d+)', lines)
cmd_ref = '@obj' + m.group(1)

# 2. 保存
mcp({
    "jsonrpc": "2.0", "id": "2",
    "method": "tools/call",
    "params": {
        "name": "kz_invoke",
        "arguments": {
            "target": cmd_ref,
            "method": "SaveProject",
            "args": ["@project"]
        }
    }
})

# 3. 导出 kzb
mcp({
    "jsonrpc": "2.0", "id": "3",
    "method": "tools/call",
    "params": {
        "name": "kz_invoke",
        "arguments": {
            "target": cmd_ref,
            "method": "ExportBinary",
            "args": ["@project"]
        }
    }
})

ws.close()
```

## 相关类的关键方法

### GeneratedCommandInvoker 可用方法（部分）

| 方法 | 说明 |
|------|------|
| `SaveProject(Project)` | 保存指定工程 |
| `SaveProject(Project, String, Boolean...)` | 保存到指定路径（含各种选项） |
| `SaveAllProjects()` | 保存所有打开工程 |
| `ExportBinary(Project)` | 导出指定工程的 kzb |
| `ExportBinary(Project, Boolean)` | 导出，第二个参数控制是否覆盖 |
| `ExportBinary(Project, Boolean, Boolean)` | 导出，第三参数控制是否清理 |
| `ExportAllProjectBinaries()` | 导出所有工程的 kzb |
| `ExportBinaryWithApplication(Project)` | 导出含 application 配置的 kzb |
| `CloseProject()` | 关闭当前工程 |
| `CloseSolution()` | 关闭解决方案 |
| `ExitApplication()` | 退出 Kanzi Studio |

## 相关路径

- 工程路径：`@project.get_FileSystemPath()`
- 导出目录：`@project.get_BinaryExportDirectory()`

## v4 参数标识符总表（通用）

所有 Kanzi skill 共用。`target` 与 `args` 参数都支持以下标识符（v4 插件已全部实测通过）。

### 基础类型

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@string:值` | 强制字符串（数字/布尔不再自动转） | `@string:123` → `"123"` |
| `@int:` / `@long:` | 强制整数 | `@int:255` |
| `@float:` / `@double:` / `@decimal:` | 强制浮点 | `@float:36` |
| `@bool:true` | 强制布尔 | `@bool:true` |
| `@byte:` / `@char:` | 字节 / 字符 | `@byte:200` |
| `@null` | 可空参数置 null（无冒号） | `CreateIntProperty(...,"@null")` |

### 引用 / 对象

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@obj:X` | 对象缓存引用（等价 `@objX`，target 与 args 均可用） | `@obj:706` |
| `@node:/path` | 节点路径（target 与 args 均可用） | `@node:/Screens/.../text` |
| `@project` / `@studio` | 工程/Studio 对象（target 与 args 均可用，v4 已修 args 解析） | `args:["@project"]` |
| `@type:名字` | .NET Type 对象（如 `@type:string`） | `CreateProperty<T>` |
| `@enum:名字` | 精准枚举转换（如 `@enum:WHOLE_PROPERTY`） | `@enum:WHOLE_PROPERTY` |
| `@dict:k=v,k=v` | 字典（CreateCustomEnumProperty options） | `@dict:off=0,on=1` |

### 向量

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@vector:x,y` | Vector2 | `@vector:0,0` |
| `@vector3d:x,y,z` | Vector3 | `@vector3d:0,0,0` |
| `@quaternion:x,y,z,w` | Vector4/四元数 | `@quaternion:0,0,0,1` |

> **规则**：有标识 → 必须按标识解析；无标识 → 自动猜测兜底（兼容旧调用）。`@obj:` / `@node:` 在 `target` 位置（走 `ResolveObject`）与 `args` 位置（走 `ResolveSingleArg`）都支持。
