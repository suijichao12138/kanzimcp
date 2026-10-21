---
name: kanzi-studio-mcp
description: Kanzi Studio MCP 总入口。接入方式（http 端点 + X-Kanzi-User / relay ws 直连）、用脚本调 MCP 的完整流程与坑、31 个工具的确切参数 schema、v4 参数标识符（@type/@int/@string/@enum/@obj/@node/@null/@vector/@transformation2d/@color/@list 等）、target 取值、返回格式。操作 Kanzi Studio 前先读本 skill，再读具体操作的 skill（ui/binding/state-manager/animation/localization/resource-create/trigger/screenshot/save-export）。
---

# kanzi-studio-mcp 使用手册（MCP 本身）

> 操作 Kanzi Studio 的总入口。**任何 Kanzi 操作前先读本 skill**，再读对应具体 skill。

## 〇、我有两种接入方式（都实测可用）

### 方式 A：relay ws 直连（我当前用的，最方便）

工作区脚本 `kanzi-mcp-client.mjs` 走这条：

```bash
# 读工程名（验证连接）
node /home/suijichao/.openclaw/workspace-kanzimcp/kanzi-mcp-client.mjs '{"name":"kz_invoke","arguments":{"target":"@project","method":"get_Name","args":[]}}'
# → ✅ 结果: cluster_hmi
```

- 地址：`ws://123.57.85.81:58080/suijichao`（**端口 58080；路径段 = 通道名**）
- **第一条消息必须带 `role`**：`{"role":"client","name":"suijichao"}` —— 否则中继回 `未知角色` / `Server not connected`
- 之后走 JSON-RPC：`initialize` → `tools/call`
- 相关脚本：`kanzi-mcp-client.mjs`（通用调用）、`kanzi-mcp-list-tools.mjs`（列工具）、`kanzi-shot-save.mjs`（截图落盘）
- ⚠️ ws 直连是 **client 槽**：同通道里 server（Kanzi 插件）是对方。多 client 并存已支持（2026-09-14 实测）。

### 🔌 脚本单连接铁律（批量/多调用脚本必读！2026-10-19 老隋要求）

**一个脚本只建一次连接，所有调用复用同一连接提交。**

> ⚠️ **崩溃根因（2026-10-19 实测）**：AI 写的批量脚本每次调用都 `Popen` 新进程 → 每次新建 WS 连接 → 循环里每步连接都换 → @obj ref 缓存失效、`BeginBatchModification` 事务跨连接错乱 → **Kanzi Studio 崩溃**。

正确结构（伪代码，单连接复用）：

```python
import json, websockets, asyncio

async def main():
    # 1. 只建一次连接（整个脚本复用这一个）
    async with websockets.connect("ws://123.57.85.81:58080/suijichao") as ws:
        await ws.send(json.dumps({"role":"client","name":"suijichao"}))
        # 2. Begin 批量
        await call(ws, "kz_invoke", {"target":"@project","method":"BeginBatchModification","args":["批量创建"]})
        # 3. 循环内复用同一连接发 N 次调用（禁止每次重新连接）
        for name in names:
            await call(ws, "kz_invoke", {"target":"@project","method":"CreateProjectItem","args":["@type:State", name, parent_ref]})
        # 4. Commit
        await call(ws, "kz_invoke", {"target":"@project","method":"CommitBatchModification"})

async def call(ws, tool, args):
    req = {"jsonrpc":"2.0","id":"req-1","method":"tools/call","params":{"name":tool,"arguments":args}}
    await ws.send(json.dumps(req, ensure_ascii=False))
    resp = json.loads(await ws.recv())
    return resp
```

**规则**：
1. **一个脚本 = 一个连接**。整个脚本生命周期只 `connect` 一次，循环/多步调用全部复用同一个 `ws`。
2. **禁止**：每次调用都 `Popen` 新进程 / 重新 connect / 重新初始化（每次新连接 = 每次 @obj 缓存重排 + batch 状态跨连接）。
3. **@obj 引用在同连接内连续有效**：本连接里第一次调用返回的 `@objN`，后续调用直接当 target/args 用。
4. batch（Begin→调用→Commit）**必须在同一连接内完成**，不能 Begin 在连接 A、Commit 在连接 B。
5. HTTP MCP（方式 B）是**无状态 HTTP**，每次 POST 独立 —— 批量脚本请用方式 A（ws 单连接）或把 batch 三件套放进同一个 Python 进程内连续 POST。

### 方式 B：HTTP MCP（脚本/其他工具接入用）

```
POST http://<kz_mcp_http机IP>:9001/mcp
Header: Content-Type: application/json
Header: X-Kanzi-User: <用户名>       ← 必需
```

- 阿里云实测：`http://123.57.85.81:9001/kanzistudio_mcp`（2026-09-14 实测可用）
- **三端点并存**（copilot 就是这么配的）：
  - `/kanzistudio_mcp` → 操作 Kanzi Studio（**标准端点**；`/mcp` 是等价别名，实测两者结果一致）
  - `/kanzi_api_mcp` → 官方 API 代理
  - `/kanzi_doc_mcp` → 官方文档代理
- 白名单 `users.json`：`suijichao / wangtianyu / wangdong / zhenghaitao / lvhuiyuan / test`

## 一、用脚本直接调 HTTP MCP（2026-09-14 实测打通）

**① 必需两件套**

| 项 | 位置 | 说明 |
|----|------|------|
| **用户名** | HTTP header `X-Kanzi-User: <用户名>` | 必带；缺=403；须在 `users.json` 白名单；不同用户名 = 不同 relay 通道 |
| **请求 id** | JSON-RPC 体里的 `id` | 必带；**同一时刻唯一即可**（数字/字符串都行）；回包按此 id 配对 |

**② 最小可用脚本（Python）**

```python
import json, urllib.request

req = urllib.request.Request(
    "http://123.57.85.81:9001/mcp",
    data=json.dumps({
        "jsonrpc": "2.0",
        "id": "my-request-1",          # 唯一 id（字符串/数字均可）
        "method": "tools/call",
        "params": {"name": "kz_invoke",
                   "arguments": {"target": "@project", "method": "get_Name", "args": []}}
    }).encode(),
    headers={"Content-Type": "application/json",
             "X-Kanzi-User": "suijichao"},
    method="POST")
print(urllib.request.urlopen(req, timeout=60).read().decode())
```

**③ 注意事项（实测踩过的坑）**

- **不强制 `initialize`**：脚本直发 `tools/call` 也能用（http 层不强制）。
- **并发**：每个请求**开自己的 HTTP 连接**。实测 5 并发 5/5 成功、各回各的 id、不串。
- **超时**：给足 timeout（服务端默认 mcp_timeout 300s）。
- **回包 id 必须原样透传**：插件旧版把字符串 id 按整数解析 → 回包 id 变 `-1` → 上游按 id 配对全对不上 → 请求被误判「丢失」（实测症状：6.3s 后报 `MCP 请求丢失(插件空闲未收到)`）。
  **两层修复（2026-09-14）**：方案A 插件 `JsonUtils.GetRaw` 原样透传 id；方案B http 侧收到 `-1` 时 FIFO 兜底配对。
- **`isError:true` ≠ 请求丢失**：前者是 Kanzi **真执行后**的业务错误（如方法名不存在），说明链路已通。
- **白名单热更新**：改 `users.json` 保存即生效，**不需要重启** kz_mcp_http.py。
- **同用户名多客户端**：copilot 与脚本可各自独立连接并存（relay 多 client 并存 + 按 id 定向回传），不再互踢。

## 二、工具清单（31 个，与插件 tools/list 实际注册一致）

工具名都以 `kz_` 开头。以工具名为准（不按编号）。常用：

### 🔧 工程/基础
- `kz_health`：探活，返回 `{ok, busy, active_request_id, 工程名}`（**并行、不排队**）
- `kz_list_projects`：列出已打开工程（含 ActiveProject/Primary 标记）
- `kz_select_project`：切换 `@project` 作用目标（**不改 ActiveProject**）
- `kz_invoke`：通用反射调用（最核心，`target` + `method` + `args`）
- `kz_ref_properties` / `kz_ref_methods` / `kz_list_refs`：探引用能干什么
- `kz_type_probe`：只读探测类型构造/方法签名

### 📦 节点/属性/保存
- `kz_create_node`（parent + type + name）
- `kz_set_property` / `kz_get_property` / `kz_delete_node` / `kz_get_node_tree`
- `kz_save_project`

### 🌐 多国语表 Localization
- `kz_loc_entry_list` / `kz_loc_entry_get` / `kz_loc_entry_add` / `kz_loc_entry_set` / `kz_loc_entry_delete`
- `kz_loc_entry_add_language` / `kz_loc_entry_delete_language`
- `kz_loc_row_get`（读单行 DefaultText + Translations）
- `kz_localized_resources`（读字体等资源通道）
- `kz_loc_entry_dump` / `kz_loc_iface`（诊断）

### 🖼 截图/窗口
- `kz_enum_all_windows`（列所有顶层窗口，拿 pid/hwnd）→ **截图第一步**
- `kz_screenshot_preview`（**一键截图，传 `pid` + `maxSide`**；无 Preview 则截 Studio 主窗）
- `kz_enum_windows` / `kz_print_window` / `kz_capture_screen`

### 🎬 动画
- `kz_modify_animation`（action: add/modify/remove + keyframes）

## 三、v4 参数标识符（kz_invoke 的 args / target 里最常用，完整总表）

### 基础类型

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@string:值` | 强制字符串（避免被转 int） | `@string:123` → `"123"` |
| `@int:` / `@long:` | 强制整数 | `@int:255` |
| `@float:` / `@double:` / `@decimal:` | 强制浮点 | `@float:36` |
| `@bool:true` | 强制布尔 | `@bool:true` |
| `@byte:` / `@char:` | 字节 / 字符 | `@byte:200` |
| `@null` | 可空参数置 null | `CreateIntProperty(...,"@null")` |
| `@enum:名字` | 精准枚举转换 | `@enum:WHOLE_PROPERTY` |
| `@type:名字` | .NET Type 对象 | `@type:string` |
| `@dict:k=v,k=v` | 字典（CreateCustomEnumProperty） | `@dict:off=0,on=1` |

### 引用 / 对象

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@objN` / `@obj:N` | 对象缓存引用（**先调一次如 get_Name 触发缓存**；Studio 重启（**仅人工**）失效） | `@obj238` |
| `@node:/path` | 节点路径（target/args 均可） | `@node:/Screens/.../text` |
| `@project` / `@studio` / `@projectItem` | 内置对象，自动注入 | `@project` |
| `@proj:<工程名>[/路径]` | 指定工程对象/路径（v12） | `@proj:hmi-alarm/Prefabs/warning` |
| `@anim:名称` | Kanzi 内部资源引用（动画子片段引用） | `@anim:InnerRadius_1` |
| `@list:类型名@obj1,@obj2` | 集合 List<T>（**集合属性必须用**，如 FontFiles） | `@list:Rightware...FontFile@obj10,@obj11` |

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
> - 用于 `Node2D.RenderTransformation` 等**只接受 Transformation2D 类型值**的属性（Kanzi 2D 节点定位就是用这个）。
> - ⚠️ **不要用 `@vector:` 或裸字符串设 RenderTransformation**：会存错类型（2 分量 Vector / string）导致读回 null，污染属性。必须用 `@transformation2d:`（详见 `kanzi-transform` skill）。
> - 示例：位置 X:0, Y:115（无缩放无旋转）→ `@transformation2d:1,1,0,0,115`

### 颜色（v6 新加）

| 标识符 | 作用 | 示例 |
|--------|------|------|
| `@color:AARRGGBB` | System.Windows.Media.Color（WPF Color 对象） | `@color:#FF9BA014` |

> **`@color:` 说明**：
> - 解析成 `System.Windows.Media.Color`（WPF Color 对象），**不是字符串**——用于 `ColorBrush.Color` 等只接受 Color 值的属性。
> - 格式：8 位 `AARRGGBB` 或 6 位 `RRGGBB`（A 默认 255），`#` 前缀可有可无。
> - ⚠️ 平台舍入：中间色值读回可能差 1（如 B=0x14→读回 0x13），边界色(00/FF)精确，非解析问题。

> **规则**：有标识 → 按标识解析；无标识 → 自动猜测兜底。

### target 特殊取值
- `/Screens/Screen/RootPage/...`：节点路径，**不带工程名前缀**
- `@node:/...`：显式节点引用

## 四、返回格式

`kz_invoke` 返回通常含 `ref_id`（如 `@obj5`），后续把它当 target 或 args 的 `@obj:` 引用；
简单值直接返回（数字/字符串/bool）。

先用 `kz_ref_properties` / `kz_ref_methods` 探一个 `ref_id` 能干什么，再动手。

## 五、⚠️ 坑

- **批量操作必须成对**：`BeginBatchModification` / `CommitBatchModification`，否则 Studio 卡死（API 全返回空）。
- **集合属性（List<T>）赋值必须 `@list:` 前缀**，直接给单个 `@obj` 报 "cannot be converted"。
- **ResourceReference 型属性**（FontFamily / StateManager）：用 `Set` 方法（不是 `set_Item`），传 `@obj`。
- **`@type:` 不适用于 Node**（UI 节点用 `kz_create_node`）；`@type:` 只用于能继承 ProjectItem 的类型。
- **反射调用在 UI 线程执行**，重量操作会让 Studio 界面短暂卡住，属正常。
- **不污染现有工程**：新建一律用新名字，不改动现有资源/节点/材质。
