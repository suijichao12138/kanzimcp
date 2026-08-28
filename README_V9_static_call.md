# V9 — 静态调用扩展（Static Call）

> 基于 v8_localization 建立的新版本。**v8 一行未动**，V9 在 v8 基础上**纯新增**三块静态调用能力。
> 用途：让 MCP 反射桥能调用 **CLR 静态方法**，从而拿到 Preview 进程句柄 / PID，为"Preview 截图探活"铺路。

## 与 v8 的差异（纯新增，0 删除）

| 文件 | 改动 |
|------|------|
| `KzMCPReflectionBridge.cs` | ① `InvokeCore` 开头加 `@static:` target 拦截分支；② 新增 `InvokeStatic` / `ResolveStaticType` / `ListStaticMethods` 三个方法 |

- diff 验证：v8 vs V9，**删除行 = 0**，改动集中在 `InvokeCore` 入口 + 三个新方法。
- 花括号平衡：与 v8 同差（差 3，为原文件字符串里的 `{`，非本次引入）。

## 新增能力

### 1. `@static:` target — 调任意 CLR 类型的静态方法

```
kz_invoke target="@static:System.Diagnostics.Process" method="GetProcesses"
kz_invoke target="@static:System.Diagnostics.Process" method="GetProcessById" args=["@int:1234"]
kz_invoke target="@static:System.Diagnostics.Process" method="ListStaticMethods"   # 返回该类型全部静态方法清单
```

- `@static:完整.类型名` → 反射解析 Type（自动补 System / System.Core / mscorlib / PresentationCore 程序集）
- 静态方法以 `BindingFlags.Static` 绑定并调用（`mi.Invoke(null, args)`）
- 参数仍走 v8 的 `ResolveArgs`（`@int:`/`@string:`/`@obj:` 等标识照常生效）
- 走 UI 线程（offUi=false），符合 Kanzi WPF 约束
- 特例：`method="ListStaticMethods"` 时，不要求目标类型真有此静态方法，而是返回该目标类型的全部静态方法清单（便于探索）

### 2. 发现某类型有哪些静态方法（无需知道方法名）

```
kz_invoke target="@static:System.Diagnostics.Process" method="ListStaticMethods"
```

返回 `{ type, staticMethods: ["Name(param) -> return", ...] }`，先看清单再调。

### 3. [V9] 截图工具 `kz_capture_screen`

```
kz_capture_screen  # 默认截整屏，缩放到最大边800，返回 PNG base64
kz_capture_screen  args={ x, y, width, height, maxSide }
```

- 底层：`System.Drawing.Graphics.CopyFromScreen` 抓屏 → Bitmap → 缩放 → PNG → base64 回传（不走文件共享）
- `maxSide`：缩放最大边，默认 800（控制 base64 体积，传输快）；`<=0` 保持原始尺寸
- 用于 Preview/Studio 截图验证
- ⚠️ CopyFromScreen 抓的是当前桌面（Studio 那台 Windows），若 Preview 离屏渲染则桌面看不到其画面

## 设计要点（符合全反射铁律）

- **不缓存**任何 `MethodInfo` / `PropertyInfo`，全部运行时 `GetType()` + `GetMethods()` 动态查找
- **不直接引用**任何具体 CLR 类型（`System.Diagnostics.Process` 等只以字符串形式出现）
- 静态调用为**纯只读**操作（枚举进程等），无副作用，安全
- 所有调用统一走 `InvokeCore` 入口 + UI 线程策略，与既有调用一致

## 待验证（需 Windows 编译 + 部署到 Studio）

### ⚠️ 2026-08-10 实测发现 + 修复
已部署版 `@static:` 前缀机制已生效，但类型解析有限：
- ✅ 能解析 mscorlib 核心类型（System.Environment / System.IO.File / System.String）
- ❌ **解析不了分布在独立程序集的类型**（System.Diagnostics.Process / System.Drawing.Bitmap / System.Windows.Forms.Form）

原因：`Type.GetType` 只在特定程序集/已加载位置查找，这些独立程序集类型命中不到。

**V9 已修复**：`InvokeStatic` 现在优先复用 v8 现成的 `ResolveTypeByName`（内置类型映射 + Kanzi 映射 + Type.GetType + **AppDomain 已加载程序集遍历**），
解析不到再走 `ResolveStaticType` 兜底。AppDomain 遍历是 v8 已验证的可靠方式。

> 需重新编译部署本版才能验证 Process 能否解析。

1. Windows 上用 VS 编译 V9 工程（`KzMCPChatPlugin.sln`）
2. 部署到 Studio 插件目录，重启插件
3. 通过 MCP 客户端发 `kz_invoke target="@static:System.Diagnostics.Process" method="GetProcesses"`
4. 确认能拿到进程列表 / Preview 进程 PID

## 版本脉络

- v7_list_param（WebSocket relay 架构）← 基线
- **v8_localization**（v8 + Localization 读写，NAS `kanzi_mcp/v8_localization/`）
- **V9_static_call**（本次，v8 + 静态调用，NAS `kanzi_mcp/v9_static_call/`）
