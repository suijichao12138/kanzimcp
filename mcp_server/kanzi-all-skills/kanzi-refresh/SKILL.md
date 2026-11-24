---
name: kanzi-refresh
description: Kanzi 刷新工程树 + 刷新 Preview + 刷新属性面板/节点树/资源缓存等各区域。创建任何对象后必须 SelectProjectItems 刷工程树；截图前必须 RestartPreview 刷 Preview；属性面板/节点树/缓存用 @static:KanziCommands 命令中心（RefreshPropertyEditor/UpdateProjectExplorer/CleanCachedFiles）。用 kz_invoke 反射调，不加专用工具。
---

# Kanzi 刷新工程树 / 刷新 Preview

> **规则**：任何创建完成后必须刷新工程树；任何截图前必须刷新 Preview。否则 Studio 里看不到新内容 / 截到旧画面。
> **原理**：插件无专用刷新工具，但 `@studio.get_Commands()` 返回的 GeneratedCommandInvoker 有这两个方法（2026-10-21 实机验证通过）。

## 唯一前置：拿 Commands 对象

每次连接编号会变，先动态取（不写死 @obj）：

```python
kz_invoke target=@studio method=get_Commands   # → @objN（GeneratedCommandInvoker）
```

## ① 刷新工程树（创建后必调）

**触发**：任何创建操作完成后 —— 新建节点、模板（Prefab）、属性、状态机（StateManager/StateGroup/State/StateObject）、多国语表、纹理、动画、笔刷、资源条目、别名等。

```python
# 传路径（最简单，推荐）
kz_invoke target=@objN method=SelectProjectItems args=["/Screens/Screen/RootPage/新建节点名"]
# 或传 @obj 引用（刚创建返回的 ref 也行）
kz_invoke target=@objN method=SelectProjectItems args=["@obj:xxx"]
```

**重载签名（2026-11-09 实机探测确认）**：`SelectProjectItems` 真实重载只有两个，都收 **ProjectItem 对象/集合**（没有 string 路径重载，但反射桥会把字符串路径自动解析成节点对象）：

| 重载 | 参数 | 何时用 |
|------|------|--------|
| `SelectProjectItems(ProjectItem itemToSelect)` | **单个 ProjectItem**（字符串路径或 `@obj:X` 引用均可，桥自动解析） | 选中**单个**工程项 —— 最常用 |
| `SelectProjectItems(IEnumerable<ProjectItem> itemsToSelect)` | **ProjectItem 集合**（多个 ref 用 `@list:` 前缀包数组） | 批量选中**多个**工程项 |

- **字符串路径直接传即可**（`["/Screens/Screen/RootPage/新建节点名"]`），桥自动解析成 ProjectItem —— 2026-11-09 实机验证 ✅ 调用成功。
- 单个引用传 `["@obj:X"]` 同样成功 ✅。
- 批量多选：`args=["@list:类型名@obj1,@obj2"]` —— `@list:` 的**类型名必须是完整类型名**（元素类型，不是占位符）：
  - 例：选中 2 个节点 → `args=["@list:Rightware.Kanzi.Tool.Logic.Project.Plugin.EmptyNode2DPluginWrapper@obj1,@obj2"]`（元素类型用 EmptyNode2DPluginWrapper 时；不同节点类型用各自的 PluginWrapper 类型名）。
  - 记不清元素类型名时，先 `kz_ref_methods` 看 `SelectProjectItems` 的签名（元素类型 = `IEnumerable<...>` 泛型参数），或直接枚举 ref 的 type 字段拿完整类型名。
- 作用：选中该工程项 → 工程树滚动定位 + 刷新显示，新内容立即可见。
- 批量创建后选最后一个/代表节点即可。

## ② 刷新 Preview（截图前必调）

**触发**：每次截图之前。

```python
kz_invoke target=@objN method=RestartPreview   # 重启 Preview 进程
```

- 刷新后略等 Preview 重启完成再截图（sleep 1~2s 或调 kz_health 确认）。
- 实测（2026-11-24）：`RestartPreview` 单次耗时较长（同步阻塞到重启完成），返回后 `kz_health` 立即正常。
- 注意：Kanzi 3.9 的 Preview 是**嵌在 Studio 主窗内的停靠视图**，`kz_enum_all_windows` 里**不会**出现独立的 `KanziPreview` 窗口；此时 `kz_screenshot_preview(pid=<Studio pid>)` 会截 Studio 主窗（`target = studio`），属正常行为。
- `RestartPreview` 有两种等价写法：`Commands.RestartPreview`，或 `get_RestartPreview` 取句柄后 `Execute args=["@null"]`。

## ③ 刷新其他面板区域（KanziCommands 命令中心，2026-11-24 实测打通）

**适用**：属性面板（属性库）、节点树（工程树）、资源缓存等「右键刷新」对应的区域。
**原理**：Studio 内部 static 类 `Rightware.Kanzi.Tool.Logic.Project.KanziCommands` 是**全命令注册中心**（451 个命令），每个 `get_XXX()` 返回可执行的 `CommandHandle`（实机是 `RoutedCommandCommandHandleAdapter`）。用 `@static:` 反射通道直接拿命令并 Execute，等价 GUI 菜单/右键动作。**无需改插件代码。**

### 调用步骤（三步）

```python
# 1. 拿命令句柄（每次连接编号会变，动态取）
kz_invoke target=@static:Rightware.Kanzi.Tool.Logic.Project.KanziCommands \
          method=get_RefreshPropertyEditor args=[]   # → ref_id = @objN

# 2.（可选）检查命令可用性
kz_invoke target=@objN method=CanExecute args=["@null"]   # → ✅ 结果: True / False

# 3. 执行命令（等价点击刷新）
kz_invoke target=@objN method=Execute args=["@null"]      # → ✅ 调用成功（无返回值）
```

> ⚠️ `@static:` 是反射桥 V9 静态调用通道（与 `@static:System.Diagnostics.Process` 同机制），target 直接写全限定类型名。

> ⚠️ **`CanExecute` 必须带参数 `["@null"]`**（WPF `ICommand.CanExecute(object)` 签名）。
> 写成 `method=CanExecute args=[]` 会报：`❌ 在 RoutedCommandCommandHandleAdapter 上找不到与参数 () 匹配的 'CanExecute'`（2026-11-24 实测）。
> `Execute` 同理必须带 `["@null"]`。命令句柄类型为 `Rightware.Kanzi.Tool.Presentation.Application.Commands.RoutedCommandCommandHandleAdapter`。

### 实测可用命令表（2026-11-24 实机 CanExecute=True + Execute 成功）

| 命令 getter | 对应面板区域 | 用途 |
|---|---|---|
| `get_RefreshPropertyEditor` | **属性面板（属性库）** | 刷新属性编辑器显示 |
| `get_UpdateProjectExplorer` | **节点树（工程树）** | 刷新工程树节点 |
| `get_CleanCachedFiles` | 资源缓存 | 清理资源文件缓存（磁盘改图后让 Studio 重载） |
| `get_ShowDataSources` | 数据源窗口 | 打开/聚焦数据源面板 |
| `get_ShowProjectExplorer` | 节点树窗口 | 打开/聚焦工程树 |
| `get_ShowPropertyEditor` | 属性面板窗口 | 打开/聚焦属性面板 |
| `get_ShowProjectProperties` | 工程属性 | 显示工程级属性 |
| `get_ShowSelectedItemsInProjectExplorer` | 工程树定位 | 选中项在工程树中定位显示 |
| `get_ShowLog` | 日志窗口 | 显示 Studio 日志 |
| `get_FilterProjectExplorer` | 工程树过滤 | 过滤工程树显示 |
| `get_OpenDictionariesWindow` | 资源字典窗口 | 打开资源字典查看器 |
| `get_RestartPreview` | Preview | 重启预览（同 RestartPreview 命令） |

### 条件命令表（存在，但当前 CanExecute=False，条件满足才可执行）

| 命令 getter | 面板区域 | False 原因 |
|---|---|---|
| `get_UpdateProjectDataSources` | 数据源 | 当前无待更新的数据源 |
| `get_UpdateSolutionDataSources` | 数据源 | 同上 |
| `get_UpdateDataSourceContents` | 数据源 | 需选中具体数据源 |
| `get_UpdateProjectEnginePlugins` | 引擎插件 | 无待更新插件 |
| `get_UpdateSolutionEnginePlugins` | 引擎插件 | 同上 |
| `get_UpdateEnginePluginMetadata` | 插件元数据 | 同上 |
| `get_UpdateSelectionToPreview` | Preview 同步 | 需有选择项 |
| `get_OpenResourceGridEditor` | 资源网格 | 需选中资源字典 |
| `get_OpenLocalizationTable` | 多国语表 | 需选中表 |

### 场景组合（创建后完整刷新链）

```python
# 创建节点/属性后：定位 + 刷节点树 + 刷属性面板
kz_invoke target=@studio method=get_Commands        # → @objN（GeneratedCommandInvoker）
kz_invoke target=@objN method=SelectProjectItems args=["/Screens/Screen/RootPage/新建节点名"]  # 定位
kz_invoke target=@static:Rightware.Kanzi.Tool.Logic.Project.KanziCommands method=get_UpdateProjectExplorer args=[]  # → @objX
kz_invoke target=@objX method=Execute args=["@null"]  # 刷节点树
kz_invoke target=@static:Rightware.Kanzi.Tool.Logic.Project.KanziCommands method=get_RefreshPropertyEditor args=[]  # → @objY
kz_invoke target=@objY method=Execute args=["@null"]  # 刷属性面板
```

> 💡 命令名可从返回值 `name = XXXCommand` 确认（如 `RefreshPropertyEditorCommand`）。
> 实测结论：下表 12 个命令在空载状态下 `CanExecute` 全部返回 True，`Execute` 全部返回「✅ 调用成功（无返回值）」（含 `get_RestartPreview`）。
> 副作用提示：`Show*` 系列会真的打开/聚焦对应窗口（如 `ShowDataSources` 会弹出 Data Sources 窗口），测试时可用来确认调用生效。

## ④ 各 skill 创建资源 → 对应刷新方法（2026-11-24 实测映射）

**原则**：Kanzi Studio 的 Project Explorer（节点树 + Library 资源库是**同一个窗口的两个视图**），所以 `UpdateProjectExplorer` 同时覆盖节点树和资源库。属性/自定义属性类用 `RefreshPropertyEditor`；磁盘资源用 `CleanCachedFiles`。

### 通用刷新动作（任何创建后）

```python
# 1. SelectProjectItems 定位（保证新对象出现在树里）
# 2. UpdateProjectExplorer 刷节点树/资源库
# 3. RefreshPropertyEditor 刷属性面板
```

### 各 skill 映射表（创建的资源 → 刷新方法）

| Skill | 创建的资源 | 刷新方法 | 说明 |
|---|---|---|---|
| **kanzi-node-create** | EmptyNode2D / TextBlock2D / 插件节点 / 九宫格 | `UpdateProjectExplorer` + `SelectProjectItems` | 节点落在节点树；SelectProjectItems 定位到新建节点 |
| **kanzi-layout** | StackLayout2D 布局节点 | `UpdateProjectExplorer` | 同节点树 |
| **kanzi-textblock** | TextBlock2D 文本节点 | `UpdateProjectExplorer` | 同节点树 |
| **kanzi-prefab** | Node2DPrefabPlaceholder 模板引用 | `UpdateProjectExplorer` | 模板占位符在节点树 |
| **kanzi-proptype** | 自定义属性类型（DynamicProperty） | `RefreshPropertyEditor` | 属性类型变化→属性面板刷新（AddDynamicPropertyType 后建议 + `UpdateProjectExplorer`） |
| **kanzi-animation** | Animation / AnimationClip / AnimationChildClip | `UpdateProjectExplorer` + `RefreshPropertyEditor` | 动画资源在资源库；关键帧/播放器属性→属性面板 |
| **kanzi-asset-create** | Color Brush / Texture / FontFamily | `UpdateProjectExplorer` + `CleanCachedFiles` | 素材在资源库；磁盘纹理改后需 CleanCachedFiles 重载 |
| **kanzi-material-brush** | Material / MaterialType / MaterialBrush | `UpdateProjectExplorer` + `RefreshPropertyEditor` | 材质三层都在资源库 |
| **kanzi-resource-create** | Resource 资源条目（ResourceDictionary） | `UpdateProjectExplorer` + `OpenDictionariesWindow` | 资源条目在资源字典；OpenDictionariesWindow 打开字典查看 |
| **kanzi-resource-set** | 节点上设置资源引用 | `RefreshPropertyEditor` | 改的是节点属性 |
| **kanzi-state-manager** | StateManager / StateGroup / State / StateObject | `UpdateProjectExplorer` + `RefreshPropertyEditor` | 状态机是节点组件；State 属性→属性面板 |
| **kanzi-trigger** | TriggerNodeComponent / TriggerActionItem | `UpdateProjectExplorer` + `RefreshPropertyEditor` | 触发器是节点组件 |
| **kanzi-binding** | 数据绑定（CreateBinding） | `RefreshPropertyEditor` | 绑定是属性级，属性面板刷新即可 |
| **kanzi-localization** | 多国语表条目/语言 | `UpdateProjectExplorer` + `OpenLocalizationTable` | 多国语表在资源库；OpenLocalizationTable 需选中表（CanExecute 条件满足才可） |
| **kanzi-shader** | Shader / MaterialType 着色器 | `UpdateProjectExplorer` + `RefreshPropertyEditor` | 着色器是资源库条目；uniform 属性→属性面板 |
| **kanzi-alias** | 节点别名（CreateNodeAliasEntry） | `UpdateProjectExplorer` | 别名关联节点树 |
| **kanzi-transform** | 节点 RenderTransformation 变换 | `RefreshPropertyEditor` | 改的是节点属性 |
| **kanzi-data-source** | 数据源（大文件预处理） | `UpdateProjectDataSources`（条件满足时） | 数据源窗口；CanExecute=False 时说明无变更 |

### 创建命令可用性实测（2026-11-24）

> 这些是 KanziCommands 的创建命令，CanExecute=True 表示当前可用（False 需选中父项/上下文）：

| 创建命令 | CanExecute | 说明 |
|---|---|---|
| `CreateNode2DPrefabTemplateCommand` | ✅ True | 2D 模板 |
| `CreateNode3DPrefabTemplateCommand` | ✅ True | 3D 模板 |
| `CreateAnimationCommand` | ✅ True | 动画 |
| `CreateAnimationClipCommand` | ✅ True | 动画片段 |
| `CreateSingleTextureCommand` | ✅ True | 纹理 |
| `CreateFontFamilyCommand` | ✅ True | 字体 |
| `CreateMaterialCommand` | ✅ True | 材质 |
| `CreateMaterialTypeCommand` | ✅ True | 材质类型 |
| `CreateStateManagerCommand` | ✅ True | 状态机 |
| `CreateLocalizationTableCommand` | ✅ True | 多国语表 |
| `CreateThemeGroupCommand` | ✅ True | 主题组 |
| `CreateEmptyNode2DCommand` 等 | ❌ False | 需选中父节点（创建节点走 skill 的 kz_create_node） |

> 💡 创建命令本身 CanExecute 情况不影响刷新；刷新只需上述通用三步。

## 完整示例（创建后完整刷新链）

```python
# 1. 拿 Commands（GeneratedCommandInvoker）
kz_invoke target=@studio method=get_Commands    # → @objN

# 2. 创建完 → 定位到新节点（工程树滚动定位 + 高亮）
kz_invoke target=@objN method=SelectProjectItems args=["/Screens/Screen/RootPage/Info/warning"]

# 3. 刷节点树/资源库（专用刷新命令）
kz_invoke target=@static:Rightware.Kanzi.Tool.Logic.Project.KanziCommands method=get_UpdateProjectExplorer args=[]  # → @objX
kz_invoke target=@objX method=Execute args=["@null"]

# 4. 刷属性面板（属性/自定义属性变化时）
kz_invoke target=@static:Rightware.Kanzi.Tool.Logic.Project.KanziCommands method=get_RefreshPropertyEditor args=[]  # → @objY
kz_invoke target=@objY method=Execute args=["@null"]

# 5. 截图前 → 刷 Preview
kz_invoke target=@objN method=RestartPreview
```

> 💡 `SelectProjectItems`（定位）与 `UpdateProjectExplorer`（刷新）区别：前者选中并滚动到目标项（副作用会刷新显示）；后者是工程树的专用刷新命令。**创建后两者都建议执行**（先定位再刷新）。

## 相关

- 其余 Commands 方法（SaveProject/ExportBinary/StartPreview 等）见 `kanzi-save-export`。
- 截图流程见 `kanzi-screenshot`。
