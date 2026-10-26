---
name: kanzi-localization
description: Kanzi 本地化全流程：读取（定位表/ExportTranslations 读全表/kz_localized_resources 读字体引用）、CRUD（首选 v13 kz_loc_entry_* 增改删/增删语言列）、删表+建表（低层重建）。含正确构造函数与删除事故警示。
---

## 🚫 命名铁律（创建前必读）

> 创建任何东西（节点/动画/别名/条目）时，**名字禁止特殊字符**：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格。
> **允许中文，推荐英文**（中文名可用，但英文更稳妥，避免跨工具编码问题）。
> 不要以数字开头（部分 API 限制）。
> 错误：`text/header` `bg.1` `a|b` `C:\temp` `new node`；正确：`text_header` `bg_1` `标题文本` `header-text`。

# Kanzi 本地化全流程

## 🚨 删除事故警示（2026-08-08 血泪教训，务必先读）

> **`Delete()` 删的是整张 LocalizationTable 项，不是单行！** 我在排查删除方法时对表对象调用 `Delete` 返回 `True`，**结果整张表（991 行）被删**——路径 `/Localization/Localization Table` 直接无法解析，`Localization` 库 children 变空。
>
> **教训：**
> 1. **绝不能对自己不明确语义的方法随便调用**，尤其删除类。调任何方法前先确认它作用在什么对象、删什么。
> 2. `Delete()` 在项目项上 = 删除整个项，危险。v13 删单行用 `kz_loc_entry_delete`（底层 Remove(key,true)），**不能用项目项的 Delete 删单行**。
> 3. 探测删除方法名时，先在**备份/测试工程**上做，别在真实数据上试。
> 4. 出事第一时间停写操作、检查 Undo/版本控制恢复，并如实报告。

## 一、定位 Localization Table（底层）

```python
# 1) @project.get_Children() 里有名为 "Localization" 的库（不是 get_LocalizationLibrary）
mcp kz_invoke target=@project method=get_Children

# 2) Localization 库 (LocaleLibraryPluginWrapper) 的 children 里有 Localization Table
mcp kz_invoke target=/Localization method=get_Children
#   → ref_id=@objXXX, type=LocalizationTablePluginWrapper, name="Localization Table"

# 完整路径定位表
LT="/Localization/Localization Table"
```

> ⚠️ `@project` 上**没有** `get_LocalizationLibrary`（不存在）；Localization 库是 children 里的普通库。

## 二、读取（ExportTranslations 读全表 + kz_localized_resources 读字体引用）

### ⭐ 核心读取通道：ExportTranslations()（2026-08-08 实测打通）

**最关键的教训：`Localization Table.get_Children()` 返回空（len=0）是误导——它不代表没数据！**
**正确的枚举方式是 `ExportTranslations()`**（反编译 ExcelPlugin 里的 MemberRef 引用发现的）。

```python
# 1) 枚举所有行 —— 返回 LocalizationTableRow 列表（海量，实测 cluster_hmi = 991 行）
t = kz_invoke target=/Localization/Localization Table method=ExportTranslations args=[]
#   → 每行一个: ref_id=@objNNN, type=LocalizationTableRow

# 2) 每行读 key（资源名）
kz_invoke target=@行Ref method=get_ResourceName args=[]
#   → ✅ 结果: 1196   （key，如 "1196"/"131"/"2091"_1"）

# 3) 每行读翻译 —— 返回多个 KeyValuePair<string,string>（一个语言一个）
kz_invoke target=@行Ref method=get_Translations args=[]
#   → 每个: ref_id=@objNNN, type=KeyValuePair`2, name=[en, xxx]

# 4) 每个 KeyValuePair 读语言码 + 翻译文本
kz_invoke target=@KVPRef method=get_Key args=[]     # → ✅ 结果: en / zh-CHS
kz_invoke target=@KVPRef method=get_Value args=[]   # → ✅ 结果: 翻译文本
# 也可 ToString() → [en, Stop vehicle immediately and move away.]
```

### 完整读取链路（实测代码）
```python
# 枚举行
t=call("Localization/Localization Table","ExportTranslations",[])
row_refs=list(set(re.findall(r'ref_id = (@obj\d+)\n▪ type = LocalizationTableRow', t)))
# 每行
for row in row_refs:
    key=call(row,"get_ResourceName",[])
    trans=call(row,"get_Translations",[])
    kvps=re.findall(r'ref_id = (@obj\d+)\n▪ type = KeyValuePair', trans)
    for k in kvps:
        lang=call(k,"get_Key",[]); val=call(k,"get_Value",[])
```

### 实测数据（cluster_hmi）
- **总行数：991 行**（数据量很大，get_Children 空是假象）
- **语言：`en` + `zh-CHS`** 两种
- 示例：
  | key | en | zh-CHS |
  |---|---|---|
  | 1196 | Complex environment, drive safely | 环境复杂，请注意安全 |
  | 131 | Door release motor fault | 车门释放电机故障 |
  | 2091 | (空) | 请立即控制车辆 |
  | 2278 | (空) | 请小心驾驶 |
- 注意：部分 key 的 en 为空、只有 zh-CHS 有值（数据本身如此）

### ⭐ 读取资源/字体引用（v13 `kz_localized_resources`，get_Entries 通道 2026-08-18 打通）

> **ExportTranslations 只拿得到纯文本行（get_Translations 是 string 字典），读不到字体/资源引用。**
> 要读**字体（FontFamily）等资源引用**，走 `kz_localized_resources` → 内部对象 `ResourceLocalizationItems.LocalizationTable`
> 上的 **`get_Entries()`**（接口 `ResourceDictionaryInterface` 的显式实现，普通反射/ExportTranslations 看不到）。
> 这是 V8~V12 一直做不到的，v13 打通。

### 调用
```json
{"name":"kz_localized_resources","arguments":{"target":"/Localization/Localization Table"}}
```

### 返回结构（实测 227 行全表条目）
每个条目 `ResourceDictionaryEntry`（`Rightware.Kanzi.Tool.Logic.Project.ResourceDictionaryItems.ResourceDictionaryEntry`）：

| 字段 | 含义 |
|---|---|
| `key` | resourceName（如 `SourceHanSansSCfontFamily` / `里程`） |
| `isText` | **True=文本条目**；False=资源条目（字体等） |
| `isAlias` / `isUrl` | 别名 / URL 标记 |
| `resourceRef` | ProjectItemReference（资源引用对象 @obj） |
| `targetRef` / `targetType` / `targetName` | **Target 目标**（字体=FontFamily，targetName=字体名） |

### 字体（FontFamily）读取实测
```json
// kz_localized_resources 返回里 key 含 fontFamily 的条目：
{
  "key": "SourceHanSansSCfontFamily",
  "isText": false,               // ← 非文本，所以 get_Translations 读不出！
  "resourceRef": "@obj13",      // ProjectItemReference
  "targetRef": "@obj14",
  "targetType": "FontFamily",
  "targetFullType": "Rightware.Kanzi.Tool.Logic.Project.ResourceFileItems.FontFamily",
  "targetName": "SourceHanSansSC_new"   // ← 字体名
}
// SourceHanSansSCfontFamily_medium 同样 → targetName=SourceHanSansSC_new
```

### 与 ExportTranslations 的区别
| 通道 | 能拿什么 | 不能拿什么 |
|---|---|---|
| `ExportTranslations()` → LocalizationTableRow | 每行 key + **纯文本** translations(string字典) | **字体/资源引用**（isText=False 的行读不到） |
| `get_Entries()` → ResourceDictionaryEntry | 每行 key + **ResourceReference→Target(FontFamily)** + isText/isAlias/isUrl | 直接的翻译文本字典（文本值要走另一个入口） |

### 技术要点（v13 插件实现）
- 底层：内部对象 `ResourceLocalizationItems.LocalizationTable` 实现 `ResourceDictionaryInterface`（有 `get_Entries` 等）
- `get_Entries()` → `IEnumerable<ResourceDictionaryEntry>`（所有条目：文本 + 字体 + 资源）
- `ResourceDictionaryEntry.get_ResourceReference()` → `ProjectItemReference` → `get_Target()` → **FontFamily**
- 方法为**显式接口实现**（普通 `GetMethod` 看不到），须用 `GetInterfaceMap` 精确调（v13 `TryCallInterfaceGetter`）
- **安全**：预算保护 + 去重（Seen），绝无递归，不会卡死

## 三、CRUD（首选 v13 `kz_loc_entry_*`）

## 🥇 首选：v13 MCP 工具 `kz_loc_entry_*`（完整 CRUD，2026-08-18 add/set 打通 + 回归）

v13 插件把本地化 CRUD 封装成专用 MCP 工具 `kz_loc_entry_*`，直接对外暴露完整增删改查，**日常操作优先用它**。按 key(resourceName) 单个增/改/删，**不删表、不重建**，字体/资源引用天然保留。

### 定位
```python
TBL="/Localization/Localization Table"   # v13 工具 target 都指向它
```

### 工具一览（v13，均可一次多行/多key；底层正确构造 + SetOrCreate，void 返回即成功）
| 工具 | 参数 | 功能 | 状态 |
|---|---|---|---|
| `kz_loc_entry_list` | `target` | 列出全表所有条目（key/type/文本/引用，注册 @obj） | ✅ |
| `kz_loc_entry_get` | `target, key` | 读单条（found/key/isText/引用） | ✅ |
| `kz_loc_entry_add` | `target, rows[]` | **新增**条目（rows 支持多行） | ✅（2026-08-18） |
| `kz_loc_entry_set` | `target, rows[]` | **修改**条目（defaultText/type/引用） | ✅（2026-08-18） |
| `kz_loc_entry_delete` | `target, keys[]` | **删除**指定条目（Remove(key,true) **整表级联**：主表+所有 locale 同步清） | ✅ |
| `kz_loc_entry_dump` | `target` | 诊断：列 entry 内部对象全部接口方法 | 诊断用 |
| `kz_loc_entry_add_language` | `target, lang` | **新增语言列**（CreateLocaleCommandRecord.CreateProjectItem，等价 GUI 新建语言） | ✅（2026-08-19） |
| `kz_loc_entry_delete_language` | `target, lang` | **删除语言列**（get_Locales 找匹配 Language → 项目项 Delete()，等价 GUI Delete ProjectItem） | ✅（2026-08-19） |
| `kz_localized_resources` | `target` | 读字体/资源引用（get_Entries） | ✅（2026-08-18） |

> rows 元素结构：`{"resourceName":KEY, "type":"text|font|style|node", "defaultText":"...", "targetRef":"@objN或路径", "translations":{"en":"..","zh-CHS":".."}}`
> ⚠️ v13 的 `kz_loc_entry_*` 取代了 v8 的 `kz_localization`（get/list/set/rebuild/delete），旧工具已删除。

> ⚠️ **地址规则**：若环境已配置好相关 MCP（如 nlp_worker config.yaml 的 `mcp_servers` 或部署机已建网关），**必须使用已配置的 MCP 地址**；`<kz_mcp_http机IP>` 仅为通用占位符（未配置时的示例写法）。

### CRUD 实测示例
```bash
# 查
HTTP POST http://<kz_mcp_http机IP>:9001/mcp（X-Kanzi-User: suijichao）→ tools/call {"name":"kz_loc_entry_list","arguments":{"target":"/Localization/Localization Table"}}
HTTP POST http://<kz_mcp_http机IP>:9001/mcp（X-Kanzi-User: suijichao）→ tools/call {"name":"kz_loc_entry_get","arguments":{"target":"/Localization/Localization Table","key":"ECO"}}

# 增（add，带 defaultText + 各语言 translations，多行）
HTTP POST http://<kz_mcp_http机IP>:9001/mcp（X-Kanzi-User: suijichao）→ tools/call {"name":"kz_loc_entry_add","arguments":{"target":"/Localization/Localization Table","rows":[{"resourceName":"zz_newkey","type":"text","defaultText":"默认文本","translations":{"en":"hello","zh-CHS":"你好"}}]}}
# → added=True；add 内部用 new ResourceDictionaryEntry(key, new ProjectItemReference(text,TEXT)) + SetOrCreate

# 改（set，改 defaultText + translations，多行）
HTTP POST http://<kz_mcp_http机IP>:9001/mcp（X-Kanzi-User: suijichao）→ tools/call {"name":"kz_loc_entry_set","arguments":{"target":"/Localization/Localization Table","rows":[{"resourceName":"zz_newkey","type":"text","defaultText":"改后的默认文本","translations":{"en":"MODIFIED","zh-CHS":"已改"}}]}}
# → updated=True；type 保持 text

# 删（delete，多 key）
HTTP POST http://<kz_mcp_http机IP>:9001/mcp（X-Kanzi-User: suijichao）→ tools/call {"name":"kz_loc_entry_delete","arguments":{"target":"/Localization/Localization Table","keys":["zz_newkey"]}}

# 增语言列（add language）
HTTP POST http://<kz_mcp_http机IP>:9001/mcp（X-Kanzi-User: suijichao）→ tools/call {"name":"kz_loc_entry_add_language","arguments":{"target":"/Localization/Localization Table","lang":"de"}}
# → success=True；languageCount / translations 出现新语言列

# 删语言列（delete language）
HTTP POST http://<kz_mcp_http机IP>:9001/mcp（X-Kanzi-User: suijichao）→ tools/call {"name":"kz_loc_entry_delete_language","arguments":{"target":"/Localization/Localization Table","lang":"de"}}
# → success=True, found=True；该语言列从 get_Locales 消失；找不到 lang 返回 found=False 且不删任何内容
```

### 🅵 字体/资源引用条目（type≠text，2026-08-19 打通：新增+修改）

除了纯文本条目（`type:"text"`），还能新增/修改**字体（FontFamily）等资源引用条目**，`type` 用 `font`/`style`/`node`（对应 ContentType FONT/STYLE/NODE），`isText=False`。

**⚠️ 关键：`targetRef` 必须传目标资源的裸对象引用（`@obj`），不能用路径（`/path`）！** 用路径会 `构造 ResourceDictionaryEntry 失败`。

**拿目标字体的裸对象 ref（两选一）：**
1. 读一个已有字体条目 → `kz_loc_entry_get` → 返回里的 `targetRef`（如 `@obj24` = FontFamily 裸对象）
2. 用 `kz_get_raw_ref` 从字体 wrapper 取裸对象：`kz_get_raw_ref {target:"@对象", method:"get_WrappedItem", args:[]}` → `✅ 裸对象: @obj37`
  - 先 `kz_invoke {target:"/Font Families", method:"get_Children"}` 列字体 wrapper（name=字体名，ref=@obj）

**新增字体条目：**
```json
{"name":"kz_loc_entry_add","arguments":{"target":"/Localization/Localization Table","rows":[{"resourceName":"__FONT1","type":"font","targetRef":"@obj24","defaultText":"测试"}]}}
// → added=True；targetRef 是 FontFamily 裸对象（@obj，非 path！）
```
读回验证：`isText=false`、`resourceRef_ContentType=ABSOLUTE`、`targetName=<字体>`（如 SourceHanSansSC_new）、`contentType=font`

**修改字体条目（改 target 到另一字体）：**
```json
{"name":"kz_loc_entry_set","arguments":{"target":"/Localization/Localization Table","rows":[{"resourceName":"__FONT1","type":"font","targetRef":"@obj37","defaultText":"测试-MEDIUM"}]}}
// → updated=True；target 换成 @obj37（另一 FontFamily 裸对象）
```
读回确认：`targetName` 变新字体（如 SourceHanSansSC_new → SourceHanSansSC-Medium_new）、`isText` 仍为 false、类型保持 font。

**实测（2026-08-19 真实表）：**
- 新增 `__TEST_FONT_REF` type=font targetRef=@obj24 → added=True，isText=false，target=SourceHanSansSC_new
- set 改 targetRef=@obj37（SourceHanSansSC-Medium_new 裸对象，via kz_get_raw_ref）→ updated=True，target=SourceHanSansSC-Medium_new，isText/type 保持
- 完成后 `kz_loc_entry_delete` 清理测试条目
- ⚠️ `type:"font"` + `targetRef:"/Font Families/..."`（路径）会失败；必须 `@obj` 裸对象引用

**✅ 保留的真实条目（新增后不删，2026-08-19）：**
新增了一个永久字体引用条目并保留在表里：
```json
{"name":"kz_loc_entry_add","arguments":{"target":"/Localization/Localization Table","rows":[{"resourceName":"ARFontfontFamily","type":"font","targetRef":"@obj40","defaultText":"AR字体"}]}}
// → added=True；@obj40 = ARFont Family 字体裸对象（via kz_get_raw_ref get_WrappedItem）
```
读回：`key=ARFontfontFamily`、`isText=false`、`targetName=ARFont Family`、`ContentType=ABSOLUTE` **已保留在表，未删**。
命名约定参照现有字体条目（`<字体名>fontFamily`），供 HMI 字体引用用。

### 🌐 增加语言列（2026-08-19 打通）：首选 `kz_loc_entry_add_language`（CreateLocaleCommandRecord）

#### ✅ 首选：`kz_loc_entry_add_language`（真正新建 Locale，等价 GUI 菜单"新建语言"）

**`kz_loc_entry_add_language` 给本地化表新增一个语言列**，走 `CreateLocaleCommandRecord.CreateProjectItem`（命令记录直调，和 `kz_modify_animation` 同款模式）。它真正创建一个 Locale（语言）对象。**2026-08-19 已实测打通。**

```json
{"name":"kz_loc_entry_add_language","arguments":{
  "target": "/Localization/Localization Table",
  "lang": "de"
}}
```

**实测（真实表，2026-08-19）：**
- 调用 `kz_loc_entry_add_language {target:"/Localization/Localization Table", lang:"zz_test"}` → `success=True`
- 读表语言数：**`languageCount` = 14 → 15**（新增 1 列）
- 读任意 key 的 translations 出现新语言 `zz_test`（值为空，新语言未填翻译）
- 返回 `recordRef`（CreateLocaleCommandRecord 对象引用，可继续 kz_invoke）

**语言码规则：** 语言名称不可重复、必须用缩写（如 `en`/`zh-CHS`/`ar`/`de`）。

**实现（KzMCPReflectionBridge.AddLanguage，全反射）：**
1. `ResolveObject(target)` → wrapper → `GetWrappedItemRaw()` 拿内部 LocalizationTable
2. `LoadTypeByFullName("Rightware.Kanzi.Tool.Logic.Project.ResourceLocalizationItems.CreateLocaleCommandRecord")`
3. 按 2 参构造 `new CreateLocaleCommandRecord(内部表, lang)`
4. `CreateProjectItem(lang)` 真正新建语言列
全程 UI 线程（Dispatcher）+ 全反射（不引用具体类型）。

**背景（2026-08-19 反编译 + kz_type_probe 运行时确认）：**
- `GeneratedCommandInvoker`（@studio.get_Commands() 的 @obj）**无 CreateLocale 命令**；PluginInterface.dll **无 Locale 类型**（不能像建表那样 @type: 直接建）。
- 真正机制 = `CreateLocaleCommandRecord`：构造函数 `(LocalizationTable parent, String name)` + `CreateProjectItem(String name)`。
- `kz_type_probe` 可只读验证任意类型能否加载/构造签名（不含新建，安全）。
- ⚠️ 反编译 IL 显示 CreateProjectItem 是空 stub（混淆），但运行时可反射可调（实测 true）。

### 🗑️ 删除语言列（2026-08-19 打通）：`kz_loc_entry_delete_language`（项目项 Delete）

**`kz_loc_entry_delete_language` 删除本地化表的一个语言列**，等价 GUI 菜单"删除" → `Delete ProjectItem ".../Localization Table/<lang>"`。

```json
{"name":"kz_loc_entry_delete_language","arguments":{
  "target": "/Localization/Localization Table",
  "lang": "zz_del_probe"
}}
// → success=True, found=True, foundName=zz_del_probe, message=已删除语言: zz_del_probe
// 找不到 lang → success=False, found=False, message=表中不存在语言...（不删任何内容）
```

**实测（真实表，2026-08-19）：**
- 先 `kz_loc_entry_add_language {lang:"zz_del_probe"}` 建临时语言（get_Locales itemCount 17）
- `kz_loc_entry_delete_language {lang:"zz_del_probe"}` → `success=True`，get_Locales 中该语言消失，itemCount 回到 16 ✅

**实现（KzMCPReflectionBridge.DeleteLanguage，全反射）：**
1. `ResolveObject(target)` → wrapper → `GetWrappedItemRaw()` 拿内部 LocalizationTable
2. 枚举 `GetLocalesList`（get_Locales 接口）→ 按 `LocaleName`/`Name` 精确匹配 lang（忽略大小写）
3. 找不到 → 返回 found=false，**不删任何内容**（安全）
4. 找到 → 对该 Locale 项目项调 `Delete()`（`FindMethod(...,"Delete",Type.EmptyTypes)`，标准项目项删除 = GUI Delete ProjectItem）
5. `success=true`；Delete() 返回 null 或 true 视为成功（void/bool 归还判断）
全程 UI 线程（Dispatcher）+ 全反射。

**注意：**
- 语言码大小写不敏感匹配（en / EN 都匹配）；只删**完全匹配**的那一个语言列，不会误删其他列。
- 与新增对称：新增用 `CreateLocaleCommandRecord.CreateProjectItem`，删除用 Locale 项目项 `Delete()`（**无 DeleteLocaleCommandRecord，实测不存在**）。
- 删除真实语言列前先确认 lang 正确（可用 `kz_loc_iface get_Locales` 列当前所有语言）。

### ⭐ v13 不删表重建（安全合规）
v13 的 `kz_loc_entry_*` **按 key 单个增/改/删**，底层 `SetOrCreate`/`Remove`，**不删整表、不重建**，字体/资源引用天然保留，无需手动备份。

> ⚠️ 但要改的是**真实表**，确认好 target、key、rows 再提交。删单条用 `kz_loc_entry_delete`（绝不用项目项的 `Delete()` 删单行）。

## 四、删表 + 建表（低层重建，高风险）

> 日常增删改查用 `kz_loc_entry_*`（按 key 单个操作，不删表）。**删表/建表**是底层重建技能（删整表重建、实现删行/改字段/重命名），仅在你需要重建整表时用，**高风险、操作真实表，务必先备份/在测试工程验证**。

### 删表：`kz_invoke target=表对象 method=Delete`（危险）
```python
# 先定位表对象（ExportTranslations list 或 get_Children 拿 ref），再调用 Delete
@obj4521.Delete()   # 例：对 LocalizationTablePluginWrapper 调 Delete 返回 True
# → 整张表项被删：路径 /Localization/xxx 无法解析，Localization 库 children 变空
```
> **Delete() = 删整个项目项，不是删行！** 只能在确认数据有备份/可恢复时用。

### 建表：`@project.CreateProjectItem`（关键：参数顺序）
```python
# 参数顺序 = [@type:完整类型名, @string:表名, @obj:Localization库]（type→名字→库！）
# ❌ 我之前写成 [type, 库, 名字] 一直识别不了；正确见下：
@project.CreateProjectItem(args=[
  "@type:Rightware.Kanzi.Studio.PluginInterface.LocalizationTable",
  "@string:新表名",
  "@obj:XXX"   # get_LocaleLibrary() 拿到的 Localization 库
])
# → 返回新表 LocalizationTablePluginWrapper，出现在库 children
```
> **参数顺序是最大坑**：`[type, name, lib]` 才对（跟 SingleTexture 等资源同模式）。
> `@type:` 用**接口全名** `Rightware.Kanzi.Studio.PluginInterface.LocalizationTable`（能 Type.GetType 解析）。

### 完整链路：读全表 → 内存改 → 删旧表 → 建新表 → 写回（实现删行/改字段）
因为 `ImportTranslations` 写的是**全新构造的行**（3 参 new 随便改 resourceName/defaultText），所以：
| 想实现 | 做法 | 结果 |
|---|---|---|
| 删除行 | 内存里去掉该行 → 重建只写保留行 | ✅ 实测（REC_1 丢了） |
| 改 defaultText | 新行带新默认文本 → 重建写上 | ✅ 实测（"第二行"→"第二行改过的DT"） |
| 改 resourceName | 新行用新 key → 重建写上 | ✅ 同理会 |
| 加/改翻译 | translations 全新构造 | ✅ 实测 |
> ⚠️ 跨线程报"无法访问对象"是**表面现象**（V7 线程策略），实际仍写入成功，重试/继续即可（读回已验证）。
> ⚠️ 删除/重建是**高风险**操作（会删整表）——确认好备份再操作；日常单条增删改用 `kz_loc_entry_*`。
