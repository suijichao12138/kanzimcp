# V13：读取本地化资源（字体等 NodeResource）

> 基于 **V12_multiproject** 派生，V12 一行未动（存档于 `../v12_multiproject`）。
> V13 解决 V8~V12 一直读不到的多国语表「字体引用」问题。

## 解决的问题

多国语表（Localization Table）里，普通文本行的各语言列用 `LocalizationTableRow.get_Translations` 能读到。
但**字体行**（如 `SourceHanSansSCfontFamily`）的各语言列内容 = **`ResourceReference`（引用 FontFamily 资源）**，
走的是**资源通道**，不在 `get_Translations`（纯文本字典）里 → 所以用 `kz_invoke get_Translations` 读到**空**。

## 反编译钉死的链路（LogicProject.dll，2026-08-18，非脑补）

插件反射对象是 `LocalizationTablePluginWrapper`，它**不暴露** `get_Resources`/`get_LocalizationTableRecords`
（只暴露 LocalizationTable 接口 3 方法：ExportTranslations/ImportTranslations/get_PropertyTypes）→
不改插件原本拿不到字体。

反编译 `LogicProject.dll` 找到完整资源通道：

- `KanziLocalizationTable.get_LocalizationTableRecords()` → `KanziTranslationList`
- `KanziTranslationList.GetLocalizedResourceList()` → **`IEnumerable<NodeResource>`**（字体/FontFamily 在这）
- `KanziTranslationList.GetTranslation(NodeResource, NodeResource)` → `KanziLocale`
- `ProjectItemReference`（`ResourceDictionaryEntry.get_ResourceReference` 返回）：
  - `get_IsResourceReference`（判断是否资源引用）
  - `get_IsText`（判断是否文本）
  - `get_Target`（目标对象 → FontFamily）
- `ResourceDictionaryEntry`（命令历史里的类型）：`get_ResourceReference` / `set_ResourceReference`

**关键**：字体不在 `get_Texts`/`get_Translations`（文本通道），而在 `GetLocalizedResourceList`（本地化资源通道）。

## 新增唯一入口

```
kz_localized_resources { "target": "/Localization/Localization Table" }
  → {
      count,
      resources: [
        { ref_id: @objXXX, type, fullType, name, path, resourceID,
          isResourceReference?, isText?, targetRef?, targetName?, targetPath? },
        ...
      ]
    }
  → 每个 ref_id 可用于继续 kz_invoke（如取 FontFamily 属性）
```

## 双路径兜底（路径1 + 路径2，一起测试）

两条路径都在 `GetLocalizedResources()` 里实现：**路径1 失败自动走路径2；都失败才报错**（不再静默返回空）。

### 路径1：穿透 wrapper（主路径）
```
wrapper.get_WrappedItem() → KanziLocalizationTable
  → get_LocalizationTableRecords() → KanziTranslationList
  → GetLocalizedResourceList() → IEnumerable<NodeResource>
```

### 路径2：LogicProject 反射 / 对象池兜底
- **不需 csproj 引用 LogicProject.dll**（Studio 进程已加载它），保持全反射不直接引用具体类型。
- 扫描对象池（`@obj` 引用缓存）：任意已注册对象若带 `GetLocalizedResourceList`（或其内部对象有）就直接读取。
- 这样即使 wrapper 的 `get_WrappedItem` 没暴露，只要用户已引用表记录集合对象也能读到。

## 新增 / 改动清单

### KzMCPReflectionBridge.cs（纯新增，不改动现有方法）
- `public GetLocalizedResources(string target)`：双路径入口。
- `TryGetLocalizedResourcesFromObject(object)`：核心链路 `get_LocalizationTableRecords` → `GetLocalizedResourceList`。
- `TryGetLocalizedResourcesFromLogicProject()`：路径2，扫描对象池兜底。
- `BuildLocalizedResourcesResult` / `BuildResourceInfo` / `TryGetStringProp` / `TryGetBoolProp`：结果格式化 + 辅助。

### KzMCPServerClient.cs（纯新增）
- 注册新工具 `kz_localized_resources`（含 schema）。
- dispatch 新增 `case "kz_localized_resources":`。

## 待实测验证点（Windows Kanzi Studio 编译 + 连真实 Studio）
1. 路径1：`GetWrappedItemRaw(表wrapper)` 能否拿到 `KanziLocalizationTable`。
2. `get_LocalizationTableRecords()` 在内部对象上能否调用。
3. `GetLocalizedResourceList()` 是否真返回 `IEnumerable<NodeResource>`（字体）。
4. 读到的 resource 对象上 `get_Name`/`get_Path` 是否可读 FontFamily 名（如 SourceHanSansSC_new）。
5. `get_Target`（ProjectItemReference 的）能否拿到 FontFamily 具体对象。
6. 路径2：对象池扫描能否兜底（若路径1失败）。

## 版本继承

V8 → V9 → V10_modify_animation → V11_transformation2d → V12_multiproject → **V13_get_resource**

## 2026-08-18 更新：新增 get_Entries 探测（取字体/资源条目）

**背景**：之前 kz_localized_resources 沿 `get_LocalizationTableRecords`/`GetLocalizedResourceList`/`get_Resources` 探测全部失败
（这些方法在 LocalizationTable wrapper 及其内部对象上不存在/到不了）。

**本次新增**（KzMCPReflectionBridge.cs）：
- `ProbeRecursive` 新增 a4 块：通过**接口映射**精确调 `get_Entries`（`ResourceDictionaryInterface` 显式接口实现，
  普通反射看不到，用 `GetInterfaceMap` 按名匹配）。预算保护（Budget--），失败静默不崩。
- 新增 `BuildEntriesResult` / `BuildEntryInfo`：枚举 `ResourceDictionaryEntry`，提取
  `Key`(resourceName) / `IsText` / `IsAlias` / `IsURL` / `ResourceReference`（→ ProjectItemReference → Target = FontFamily）。

**预期链路**：wrapper → 穿透内部对象 `ResourceLocalizationItems.LocalizationTable` → 接口映射调 `get_Entries()`
→ `IEnumerable<ResourceDictionaryEntry>` → 每行的 `get_ResourceReference()` 即字体引用。

**注意**：`ResourceLocalizationItems.LocalizationTable` 实现的接口含 `NodeReferenceContainer` 及 3 个未解析接口
（疑为 ResourceDictionaryItem/ResourceDictionaryInterface）。`get_Entries` 探测若命中即成功；不命中则静默返回错误。

## V13+：新增语言列（kz_loc_entry_add_language，2026-08-19）

### 背景
老隋要"新增一个语言"的能力（加语言列）。确认 v13 `kz_loc_entry_add/set` 的 translations 只对**已存在 Locale** 写值
（匹配 LocaleName），新语言码 → NO-LOCALE，加不了新列。所以需要创建新 Locale。

### 反编译 + 运行时探测确认（非脑补）
- **没有 GUI 命令**：`GeneratedCommandInvoker`（@studio.get_Commands()）方法列表**无 CreateLocale**。
- **无 PluginInterface.Locale**：PluginInterface.dll 只有 LocalizationTable / LocaleLibrary。
- **真正机制**：`CreateLocaleCommandRecord`（构造函数 `(LocalizationTable parent, String name)`，方法 `CreateProjectItem(String name)`）。
  - `kz_type_probe` 运行时验证：类型加载于 LogicProject.dll，构造/方法签名确认。
  - ⚠️ 反编译 IL 显示 CreateProjectItem 是空 stub(混淆)；但运行时可反射拿到签名并调用（待实测真建）。
- 参考已验证先例：`kz_modify_animation` = `new ModifyAnimationCommandRecord(参数).Execute()` 反射直调命令记录。

### 新工具 kz_loc_entry_add_language
```
kz_loc_entry_add_language { "target": "/Localization/Localization Table", "lang": "de" }
→ { success, lang, recordRef, message }
```
实现（AddLanguage，KzMCPReflectionBridge.cs + dispatch case）：
1. ResolveObject(target) → wrapper → GetWrappedItemRaw() → 内部 LocalizationTable
2. LoadTypeByFullName → CreateLocaleCommandRecord
3. 按 2 参匹配构造: new CreateLocaleCommandRecord(internalTable, lang)
4. FindMethodByParamCount → CreateProjectItem(String) → invoke(lang)
全程走 UI 线程（AddLanguageCore via Dispatcher），全反射不引用具体类型。
