---
name: kanzi-studio-mcp
description: Kanzi Studio MCP 本身的使用方法和参数规则。接入方式(内网三端点+X-Kanzi-User)、31 个工具的确切参数 schema、v4 参数标识符(@type/@int/@string/@enum/@obj/@node/@null/@vector/@vector3d/@quaternion/@transformation2d/@color/@dict 等)完整规则、target 取值、返回格式。是操作 Kanzi Studio 的总入口(skill)，其他 skill(binding/state-manager/ui/save-export/animation/localization/resource-create/trigger/screenshot)是在此之上的具体实例。
---

# kanzi-studio-mcp 使用手册（MCP 本身）

## 🚀 多工程切换（2026-08-17 实测打通，v12）

bridge 支持多工程操作。默认 `@project` 指向 ActiveProject，可在多工程间随时切换。

> ⚠️ 多工程需要 **v12 插件** 支持。v10 插件只有 `kz_invoke` 等基础工具，**没有下列 select_project/list_projects 工具**，请先升级插件到 v12 再使用本节。

**① `kz_select_project` 切换 `@project` 作用目标（v12 新增工具，推荐）**
```json
{"name":"kz_select_project","arguments":{"name":"hmi-alarm"}}
// ✅ 已切换到工程: hmi-alarm（之后 @project 相关操作作用于该工程；ActiveProject 不变）

{"name":"kz_select_project","arguments":{"name":""}}
// ✅ 已切回 ActiveProject: cluster_hmi
```

**② `kz_list_projects` 列出所有已打开工程（v12 新增工具）**
```json
{"name":"kz_list_projects","arguments":{}}
// 列出 cluster_hmi [Primary]/[Active]、hmi-alarm、Resources、hmi-charging … 等
```

**③ `@proj:<工程名>[/路径]` 前缀独立引用某工程（不切 @project）**
```json
{"name":"kz_invoke","arguments":{"target":"@proj:hmi-alarm/Prefabs/warning","method":"get_Name","args":[]}}
```

**要点：**
- select 到哪个工程就操作哪个；**与工程是否 Active 无关**——次级工程上读写（建节点/保存）都正常。
- 切到某工程后，`/Screens/...`、`/Prefabs/...` 等路径都指该工程；要回 ActiveProject 再 select 空串。
- 全程 **ActiveProject 不变**（方案 A 承诺），不打扰你在 Studio 正编辑的工程。



> 本 skill 讲 **MCP 工具面**是什么、怎么连、参数规则。它是操作 Kanzi Studio 的总入口；
> 具体场景(绑定/状态机/UI/保存导出)看对应 skill，但**所有 `kz_invoke` 的 target/args 参数都遵循本手册的规则**。

## 一、接入方式（内网）

kanzi-studio-mcp 是内网 `kz_mcp_http.py` 提供的**三端点之一**，走 Streamable HTTP：

| MCP | 端点 | 内容 |
|-----|------|------|
| **kanzi-studio-mcp** | `<base>/kanzistudio_mcp` | 操作 Kanzi Studio（本手册） |
| kanzi-api-mcp | `<base>/kanzi_api_mcp` | 官方 API 代理 |
| kanzi-doc-mcp | `<base>/kanzi_doc_mcp` | 官方文档代理 |

- **base** = `http://<kz_mcp_http机IP>:<端口>`，默认 `http://10.10.118.152:9001`（kz_mcp_http.py 与 relay 同机）
- **认证**：每个请求必须带 HTTP header `X-Kanzi-User: <用户名>`，用户名在 kz_mcp_http.py 的 users.json 白名单
- 其他工具接入时在 `.mcp.json` 注册即可（Claude/Copilot 都这样挂）：

```json
{"mcpServers": {
  "kanzi-studio-mcp": {"type":"http","url":"http://10.10.118.152:9001/kanzistudio_mcp","headers":{"X-Kanzi-User":"suijichao"}}
}}
```

- **注意**：不同用户名=完全隔离通道；同用户名多客户端共享通道会冲突。

## 二、工具清单（31 个，与插件 tools/list 实际注册一致）

工具名都以 `kz_` 开头。下方清单 = 插件(v13) `tools/list` 实际注册的顺序与确切 schema，**不手写编号**（以工具名为准）。`required` 字段（标 * ）必传。

### 🔧 工程/基础

**kz_health** — 检查 Kanzi Studio 插件连接状态和当前工程信息

**kz_list_projects** — V12多工程：列出所有已打开的工程（含 ActiveProject/Primary 标记）

**kz_select_project** — V12多工程：选择指定工程为『当前操作上下文』
```text
参数: `name*`:string（工程名（kz_list_projects 返回的 name）；空/省略=切回 ActiveProject）
```

**kz_invoke** — 通用反射调用：在任意 Kanzi Studio API 对象上调用任意方法
```text
参数: `target*`:string（调用目标。格式: @studio | @project | @projectItem | @obj1/@obj2 | @proj:<工程名>[/路径] | /节点路径）; `method*`:string（方法名）; `args`:array[]（参数列表）
```

**kz_ref_properties** — 列出指定引用的所有可用属性
```text
参数: `target*`:string（对象引用ID，如 @obj1, @project, @studio）
```

**kz_ref_methods** — 列出指定引用的所有可用方法
```text
参数: `target*`:string（对象引用ID）
```

**kz_list_refs** — 列出当前对象引用缓存中的所有引用

### 📦 节点/属性/保存

**kz_create_node** — 创建 UI 节点
```text
参数: `parent*`:string（父节点路径）; `type*`:string（节点类型，如 Button2D, TextBlock2D）; `name*`:string（新节点名称）
```

**kz_set_property** — 设置节点属性值
```text
参数: `node_path*`:string（节点路径）; `property*`:string（属性名）; `value*`:string（属性值）
```

**kz_get_property** — 获取节点属性值
```text
参数: `node_path*`:string（节点路径）; `property*`:string（属性名）
```

**kz_delete_node** — 删除节点
```text
参数: `node_path*`:string（节点路径）
```

**kz_get_node_tree** — 获取工程节点树
```text
参数: `root`:string（根节点路径（可选））
```

**kz_save_project** — 保存当前工程

### 🌐 多国语表 Localization

**kz_localized_resources** — [V13] 读取本地化表里按 locale 使用的资源（字体等 NodeResource）
```text
参数: `target*`:string（本地化表位置，如 /Localization/Localization Table 或 @obj 引用）
```

**kz_loc_entry_list** — 列出本地化表所有条目（含 type/文本/引用）
```text
参数: `target*`:string（LocalizationTable 对象引用或路径（如 /Localization/Localization 或 @objN））
```

**kz_loc_entry_get** — 按 key(resourceName) 查本地化表单条目
```text
参数: `target*`:string（LocalizationTable 对象引用或路径）; `key*`:string（resourceName(Key)，只传这一个 key）
```

**kz_loc_entry_add** — 新增本地化表单条目，支持一次多行，每行需指定 type（text|font|style|node）
```text
参数: `target*`:string（LocalizationTable 对象引用或路径）; `rows*`:array[]（多行数组）
```

**kz_loc_entry_set** — 修改本地化表单条目，支持一次多行
```text
参数: `target*`:string（LocalizationTable 对象引用或路径）; `rows*`:array[]（多行数组）
```

**kz_loc_entry_delete** — 删除本地化表单条目，支持一次多行
```text
参数: `target*`:string（LocalizationTable 对象引用或路径）; `keys*`:array[]（要删除的 resourceName(Key) 数组）
```

**kz_loc_entry_delete_language** — 删除本地化表的一个语言（语言列）
```text
参数: `target*`:string（本地化表路径或 @obj 引用，如 /Localization/Localization Table）; `lang*`:string（要删除的语言码（缩写，如 de / fr / zh-CN））
```

**kz_loc_entry_dump** — 诊断：列出拿到 entry 的内部对象的全部接口方法（含显式接口实现），用于找读翻译/文本的隐藏入口
```text
参数: `target*`:string（LocalizationTable 对象引用或路径）
```

**kz_loc_entry_add_language** — 给本地化表新增一个语言（语言列）
```text
参数: `target*`:string（本地化表路径或 @obj 引用，如 /Localization/Localization Table）; `lang*`:string（新语言码（缩写，如 de / fr / zh-CN））
```

**kz_loc_row_get** — 读本地化表单单行（按 key）
```text
参数: `target*`:string（LocalizationTable 对象引用或路径）; `key*`:string（resourceName/key）
```

**kz_loc_iface** — 通用诊断：在 target 的内部对象上调指定接口 getter 或 0 参接口方法（普通反射看不到的显式接口实现）
```text
参数: `target*`:string（LocalizationTable / Localization 库 / Locale 对象引用或路径）; `method*`:string（接口/类方法名，如 get_Locales / get_Entries / GetEntry / get_ResourceReference）; `key`:string（可选；传给方法的单参数（用于 GetEntry(key) 等））
```

**kz_type_probe** — 只读诊断：按完整类型名探测一个类型是否能加载到 Studio 进程，并列出其构造函数和方法签名（不执行任何逻辑，不污染工程）
```text
参数: `typeName*`:string（完整类型名，如 Rightware.Kanzi.Tool.Logic.Project.ResourceLocalizationItems.CreateLocaleCommandRecord）
```

### 🖼 截图/窗口

**kz_capture_screen** — 截取屏幕区域并返回 PNG 的 base64（用于 Preview/Studio 截图验证）
```text
参数: `x`:integer（左上角x（默认0））; `y`:integer（左上角y（默认0））; `width`:integer（宽（<=0则整屏））; `height`:integer（高（<=0则整屏））; `maxSide`:integer（缩放最大边（默认800，<=0保持原尺寸））
```

**kz_enum_windows** — 用 user32.EnumWindows 枚举指定 PID 进程的所有顶层窗口（HWND、类名、可见性、矩形）
```text
参数: `pid*`:integer（目标进程 PID（如 KanziPreview 的 PID））
```

**kz_enum_all_windows** — 枚举系统中所有顶层窗口（无需 pid），每个带 pid/title/className/visible/坐标

**kz_print_window** — 用 user32.PrintWindow 把指定 HWND 的窗口内容离屏渲染成 PNG(base64)
```text
参数: `hwnd*`:integer（窗口句柄（kz_enum_windows 返回的 hwnd））; `maxSide`:integer（缩放最大边（默认0不缩放））
```

**kz_screenshot_preview** — 一键截图 Preview；获取不到 Preview 窗口则截 Studio 主窗
```text
参数: `pid*`:integer（KanziStudio 进程 PID）; `maxSide`:integer（缩放最大边（默认1200））
```

### 🎬 动画

**kz_modify_animation** — 给 Animation Data 加/改/删关键帧（驱动 Kanzi ModifyAnimationCommand，带撤销）
```text
参数: `animation*`:string（目标 Animation Data 路径或 @obj 引用（AnimationPluginWrapper））; `action*`:string（操作：add(加帧) | modify(改帧) | remove(删帧)）; `keyframes*`:array[]（关键帧数组（[ { time, value, type? } ]））
```

> ⚠️ **多国语表（Localization）用 v13 专用工具组 `kz_loc_entry_*`**，已取代已删除的 v8 旧工具 `kz_localization`（get/list/set/rebuild/delete）。完整玩法见 `kanzi-localization` skill。

## 三、v4 参数标识符（kz_invoke 的 args 里最常用，也适用于 target）

**规则：有标识→按标识解析；无标识→自动猜测类型（兼容老调用）。** 避免歧义就加前缀。

### 基础类型
| 标识 | 示例 | 说明 |
|------|------|------|
| `@int:` | `@int:36` | 有符号 32 位整数 |
| `@long:` | `@long:100` | 64 位整数 |
| `@float:` | `@float:1.5` | 单精度浮点 |
| `@double:` | `@double:3.14` | 双精度浮点 |
| `@decimal:` | `@decimal:99.9` | 高精度十进制 |
| `@bool:` | `@bool:true` | 布尔 |
| `@byte:` | `@byte:200` | 字节 |
| `@char:` | `@char:a` | 单字符 |
| `@string:` | `@string:123` | **强制字符串**（否则数字会被当数值） |

### 特殊值
| 标识 | 示例 | 说明 |
|------|------|------|
| `@null` | `@null` | 可空参数缺省值（如 CreateFloatProperty 缺省 bounds） |
| `@vector:` | `@vector:0,0` | Vector2D |
| `@vector3d:` | `@vector3d:0,0,0` | Vector3D |
| `@quaternion:` | `@quaternion:0,0,0,1` | Vector4D/四元数 |
| `@transformation2d:` | `@transformation2d:1,1,0,0,115` | **Transformation2D（v11 新加）**。格式 `scaleX,scaleY,rotation,tx,ty`（逗号分隔 5 个 double），对应属性原始值 `scaleX; scaleY; rotation; tx; ty`（最后两位=位置X,位置Y）。构造 `Rightware.Kanzi.Studio.PluginInterface.Transformation2D`（构造签名 `(Vector scale, double rotation, Vector translation)`，反编译确认）。用于 `Node2D.RenderTransformation` 等**只接受 Transformation2D 类型值**的属性（2D 节点定位）。⚠️ 别用 `@vector:`/裸字符串设它——会存错类型导致读回 null、污染属性。 |
| `@color:` | `@color:#FF9BA014` | **System.Windows.Media.Color（WPF Color 对象）**，v6 新加。格式 `AARRGGBB`(8位) 或 `RRGGBB`(6位,A=255)，`#` 可有可无，R/G/B 用 16 进制（`#FF9BA014`=A=FF R=9B G=A0 B=14）。用于 `ColorBrush.Color` 等**只接受 Color 值对象**的属性（不接受字符串）。⚠️ 平台舍入：中间色值读回可能差 1（如 0x14→0x13），边界色(00/FF)精确。 |
| `@dict:` | `@dict:off=0,on=1,ss=3` | 逗号分隔 k=v（枚举/选项字典）。真 JSON 对象由 MCP 反序列化成 IDictionary 走字典分支，不靠 @dict: |
| `@list:` | `@list:Rightware.Kanzi.Studio.PluginInterface.FontFile@obj10,@obj11` | **构造 List&lt;T&gt;（v7 新加）**。格式 `@list:类型名@obj1,@obj2`：类型名是第一个 `@` 之前的部分（可为空→`List<object>`），元素以逗号分隔。类型名解析失败/省略时用 `object`。**用于 FontFiles 这类要求 List&lt;T&gt; 参数的集合属性**（如 `fontFamily.Set("FontFiles", List<FontFile>)`）。元素支持 `@objN`/`@string:`/数值/布尔。⚠️ 元素 @obj 引用须已进缓存。 |

### 引用 / 类型
| 标识 | 示例 | 说明 |
|------|------|------|
| `@obj:N` | `@obj:6` | 对象缓存引用（新格式，兼容 `@obj6`）。**target 和 args 都认** |
| `@objN` | `@obj6` | 旧格式，等价 |
| `@type:名` | `@type:string` `@type:StateManager` | .NET Type 对象（泛型方法 `<T>` 用） |
| `@enum:名` | `@enum:WHOLE_PROPERTY` | 精准枚举值 |
| `@node:路径` | `@node:/Screens/.../text` | 节点路径（target 用） |
| `@project` | `@project` | 当前工程对象（args 里会解析成对象） |
| `@studio` | `@studio` | Kanzi Studio 对象（args 里会解析成对象） |

### target 特殊取值
- `@studio` / `@project` / `@projectItem`：内置对象，自动注入，直接可用
- `@objN` / `@obj:N`：缓存引用，**必须先进入缓存才能用**（调一次 `get_Name` 触发缓存），Studio 重启后失效需重取
- 节点路径：如 `/Screens/Screen/RootPage/Info/warning`，**不带 `cluster_hmi/` 前缀**；也可用显式 `@node:/...`

## 四、返回格式

`kz_invoke` 返回（tools/call 的 result）通常为对象引用形式，含：
- `ref_id`（如 `@obj5`）：后续操作把它当 target 或 args 的 `@obj:` 引用
- 若返回简单值，直接是值（数字/字符串/bool）

先用 `kz_ref_properties` / `kz_ref_methods` 探一个 `ref_id` 能干什么，再动手。

## 五、⚠️ 坑

- **批量操作必须成对**：`BeginBatchModification` 和 `CommitBatchModification` 必须成对，否则 Kanzi Studio 卡死（所有 API 返回空）。
- **集合属性（List<T>）赋值必须用 `@list:` 前缀**：如 `Set("FontFiles", "@list:类型名@obj1,@obj2")`。直接用单个 `@obj` 引用会报 "cannot be converted"（Kanzi 端要的是 List<T>，不是单个对象）。
- **ResourceReference 型属性**（FontFamily / StateManager）：用 `Set` 方法（不是 `set_Item`），传 `@obj` 引用。
- **`@type:` 不适用于 Node 类型**（UI 节点），节点用 `kz_create_node`。`@type:` 只用于能继承 ProjectItem 的类型（状态机、属性类型等）。
- 简单类型(int/bool/float/string)用 `set_Item` 直接传；但想强转就加标识符。
- 反射调用统一在 UI 线程执行，重量操作(如大状态机)会让 Studio 界面短暂卡住，属正常。
