---
name: kanzi-localization
description: Kanzi Studio 多国语资源表（Localization Table）的完整增删改查。定位 Localization 库 / Localization Table（LocalizationTablePluginWrapper）。**首选 v13 MCP 工具 `kz_loc_entry_*`（add/set/delete/get/list，完整 CRUD）+ `kz_loc_entry_add_language`（新增语言列）+ `kz_loc_entry_delete_language`（删除语言列，2026-08-19 实测打通：get_Locales 找匹配 Language 的 Locale → 项目项 Delete()，等价 GUI Delete ProjectItem）**。底层原理：读取用 ExportTranslations → LocalizationTableRow → get_ResourceName / get_Translations → KeyValuePair<语言,翻译> 的 get_Key / get_Value（实测 991 行 en/zh-CHS）。注意 get_Children 返回空是误导，正确枚举方式是 ExportTranslations。**创建/更新带值条目（2026-08-18 v13 打通）：必须用正确构造函数 `new ResourceDictionaryEntry(key, new ProjectItemReference(text, ContentType.TEXT))` + SetOrCreate，不能用 Activator 裸 new。**读取字体/资源引用（2026-08-18 v13 打通）：`LocalizationTable` 上还有 `ResourceDictionaryInterface` 的接口方法 `get_Entries()`（显式接口实现，普通反射/ExportTranslations 看不到），返回 `IEnumerable<ResourceDictionaryEntry>`——每行含 Key(资源名)/IsText/IsAlias/IsURL/ResourceReference→Target(FontFamily)。字体行 isText=False（所以 get_Translations 纯文本读不出）。**新增/修改字体引用条目（2026-08-19 打通）：kz_loc_entry_add/set 用 type=font/style/node + targetRef=@obj裸对象（不能用路径），isText=False、ContentType=ABSOLUTE，可新增并改 target 到另一字体。**
---

# Kanzi 多国语资源表（Localization Table）

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


## 概念
Kanzi 的**多国语资源表（Localization Table）**集中存放工程里所有要翻译的文本，每行一个翻译条目（key + 每个语言一条翻译）。GUI 在 Localization 编辑器里管理。

## 接入方式（本机中继桥）

通过中继 WebSocket 连接 Kanzi Studio 插件。客户端 `kanzi-mcp-client.mjs`（workspace 根目录）。

- **中继**：`ws://123.57.85.81:58080`，channel = `openclaw-main`
- **调用**：`node kanzi-mcp-client.mjs '<tools/call 参数 JSON>'`
- **参数格式**：`{"name":"kz_invoke","arguments":{"target":"<ref或路径>","method":"<方法>","args":[...]}}`
- 返回 `ref_id = @objN` 自动进对象缓存，`@objN` 可作后续 target（重启 Studio 后编号失效，须重新枚举）
- 示例中的 `mcp kz_invoke target=X method=Y args=[...]` 等价于 `node kanzi-mcp-client.mjs '{"name":"kz_invoke","arguments":{"target":"X","method":"Y","args":[...]}}'`
- **本地化 CRUD**：v13 工具 `kz_loc_entry_*`（add/set/delete/get/list，完整 CRUD，日常优先）+ `kz_loc_entry_add_language`/`kz_loc_entry_delete_language`（语言列增删），底层仍走 `kz_invoke` 反射。读字体/资源引用用 `kz_localized_resources`。
- 底层用 `kz_invoke`（反射），本地化专用工具 `kz_loc_entry_*`（v13，完整 CRUD，日常优先）。

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

### CRUD 实测示例
```bash
# 查
node kanzi-mcp-client.mjs '{"name":"kz_loc_entry_list","arguments":{"target":"/Localization/Localization Table"}}'
node kanzi-mcp-client.mjs '{"name":"kz_loc_entry_get","arguments":{"target":"/Localization/Localization Table","key":"ECO"}}'

# 增（add，带 defaultText + 各语言 translations，多行）
node kanzi-mcp-client.mjs '{"name":"kz_loc_entry_add","arguments":{"target":"/Localization/Localization Table","rows":[{"resourceName":"zz_newkey","type":"text","defaultText":"默认文本","translations":{"en":"hello","zh-CHS":"你好"}}]}}'
# → added=True；add 内部用 new ResourceDictionaryEntry(key, new ProjectItemReference(text,TEXT)) + SetOrCreate

# 改（set，改 defaultText + translations，多行）
node kanzi-mcp-client.mjs '{"name":"kz_loc_entry_set","arguments":{"target":"/Localization/Localization Table","rows":[{"resourceName":"zz_newkey","type":"text","defaultText":"改后的默认文本","translations":{"en":"MODIFIED","zh-CHS":"已改"}}]}}'
# → updated=True；type 保持 text

# 删（delete，多 key）
node kanzi-mcp-client.mjs '{"name":"kz_loc_entry_delete","arguments":{"target":"/Localization/Localization Table","keys":["zz_newkey"]}}'

# 增语言列（add language）
node kanzi-mcp-client.mjs '{"name":"kz_loc_entry_add_language","arguments":{"target":"/Localization/Localization Table","lang":"de"}}'
# → success=True；languageCount / translations 出现新语言列

# 删语言列（delete language）
node kanzi-mcp-client.mjs '{"name":"kz_loc_entry_delete_language","arguments":{"target":"/Localization/Localization Table","lang":"de"}}'
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

**✅ 保留的真实条目（老隋要求新增后不删，2026-08-19）：**
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

**语言码规则（老隋要求）：** 语言名称不可重复、必须用缩写（如 `en`/`zh-CHS`/`ar`/`de`）。

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

## 定位 Localization Table（底层）

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

## ⭐ 核心读取通道：ExportTranslations()（2026-08-08 实测打通）

**最关键的教训：`Localization Table.get_Children()` 返回空（len=0）是误导——它不代表没数据！**
**正确的枚举方式是 `ExportTranslations()`**（反编译老隋 ExcelPlugin 里的 MemberRef 引用发现的）。

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

## ⭐ 读取资源/字体引用（v13 `kz_localized_resources`，get_Entries 通道 2026-08-18 打通）

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

## 数据结构（反编译 PluginInterface.dll 铁证）

```
LocalizationTable（接口）→ 仅 3 方法：ExportTranslations / ImportTranslations / get_PropertyTypes
  └─ LocalizationTableRow（行）——【具体类 + 只读属性】
       ├─ get_ResourceName() → key（无 setter！）
       ├─ get_DefaultText() → defaultText（无 setter！）
       ├─ get_Translations() → IDictionary<string,string> 语言→翻译（无 setter！）
       ├─ .ctor() 无参
       ├─ .ctor(string ResourceName, string DefaultText, IDictionary<string,string> Translations) ← 3参构造（可直接 new）
       └─ ResourceNameEquals() → 按 key 查找
```

- **读取翻译的正路 = `LocalizationTableRow.get_Translations()`**（反编译 ExcelPlugin 引用到的）
- `ExportTranslations` 是 **Tool.Logic 运行时 wrapper** 的方法（不在 PluginInterface 接口里，接口只有 Fill/ImportTranslations——所以靠反编译接口看不到 ExportTranslations）
- ⚠️ **反编译确认（2026-08-08 实测）：`LocalizationTableRow` 是具体类，只有 getter、没有 setter（只读）**，有 3 参构造 `(string, string, IDictionary<string,string>)` → 能直接 `new` 新行
- ✅ 强类型导航：`KanziStudio.get_ActiveProject()` → `Project.get_LocaleLibrary()`；`Project.GetProjectItem(path)` 返回 ProjectItem 可 `as LocalizationTable`。窗口插件模式见 kanzi-save-export skill（PluginWindowFactory）。

## 🚨 删除事故警示（2026-08-08 血泪教训，务必先读）

> **`Delete()` 删的是整张 LocalizationTable 项，不是单行！** 我在排查删除方法时对表对象调用 `Delete` 返回 `True`，**结果整张表（991 行）被删**——路径 `/Localization/Localization Table` 直接无法解析，`Localization` 库 children 变空。
>
> **教训：**
> 1. **绝不能对自己不明确语义的方法随便调用**，尤其删除类。调任何方法前先确认它作用在什么对象、删什么。
> 2. `Delete()` 在项目项上 = 删除整个项，危险。v13 删单行用 `kz_loc_entry_delete`（底层 Remove(key,true)），**不能用项目项的 Delete 删单行**。
> 3. 探测删除方法名时，先在**备份/测试工程**上做，别在真实数据上试。
> 4. 出事第一时间停写操作、检查 Undo/版本控制恢复，并如实报告。

## ✅ 删表 + 建表（低层技能，2026-08-08 实测打通）

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

## 参考：老隋的 ExcelPlugin 导入导出插件

老隋之前写的**本地化导入/导出插件**（C#，用 NPOI 读写 excel/csv），可参考实现本地化读写逻辑：
- **DLL 组件**：`AbstractLocalizationPlugin.dll`（抽象基类）、`ExcelPlugin.dll`/`CsvPlugin.dll`（实现）、NPOI.dll 系列
- **AbstractLocalizationPlugin**（`<Namespace>.AbstractLocalizationPlugin`）：
  - `AbstractLocalizationExporter`（extends PluginCommand，菜单命令）：`Export()` / `GetLocales()`（拿语言列表）/ `Initialize()` / `Execute()` / `CanExecute()` / `get_Studio()`/`set_Studio()`
  - `AbstractLocalizationImporter`：`Import()` / 同上
- **CsvExporter / CsvImporter**（实现）：内部用 NPOI（`CreateRow`/`GetRow`/`GetCell`/`GetFormat`/`GetSheetAt`/`GetLine`）读写 excel/csv，用 `LocalizationTableRow.get_Translations()` 取数据
- **引用类型**：LocalizationTable / LocalizationTableRow / Project（`Project.Get()` 拿对象）
- 这些是**菜单命令插件**（GUI 触发），不直接暴露给 MCP；我们通过 `ExportTranslations` 在运行时直接读，等价于插件的导出逻辑

## ✅ 创建/更新 text 条目的正解（2026-08-18 v13 打通）——必须用正确构造函数

**增改 text 本地化条目，必须用正确的构造函数创建 entry，不能用 `Activator` 裸 new（裸 new 的 entry 没有文本值承载，SetOrCreate 建的条目 key 有但内容空 / 或 type 变 node）。**

```csharp
var pir = new ProjectItemReference(textValue, ContentType.TEXT);  // 文本路径 + 内容类型
var entry = new ResourceDictionaryEntry(key, pir);                 // key + ResourceReference
// 主表：SetOrCreate(entry, true)；各语言翻译：对每个 Locale 同样 SetOrCreate
```

**新增辅助方法（KzMCPReflectionBridge.cs，v13）：**
- `ConstructEntryWithRef(entryType, key, pir)` — `new ResourceDictionaryEntry(key, pir)`
- `CreateProjectItemReferenceWithText(text, contentTypeName)` — `new ProjectItemReference(text, ContentType.X)`（text 用）
- `CreateProjectItemReferenceForObj(target, contentTypeName)` — `new ProjectItemReference(target)`（font/style/node 用）
- `ResolveContentTypeEnum(name)` — 解析 TEXT/FONT/STYLE/NODE 枚举值

**关键类型签名（运行时 + 反编译双确认，非脑补）：**
- `ResourceDictionaryEntry` 构造：`()` / **`(String key, ProjectItemReference resourceReference)`** / `(source, newKey)`；属性 `Key/IsText/IsAlias/IsURL/ResourceReference`；**无 DefaultText、无设文本方法**
- `ProjectItemReference` 构造：**`(String targetPath, ProjectItemReferenceContentType type)`** / `(String targetPath)` / `(ProjectItemInterface target)` / `(ProjectItemPath)` / `(source)`；可写 `set_ContentType`/`set_Target`/`set_IsTargetPopulated`；**`RelativePath`、`IsText` 均只读（无 set_RelativePath / set_IsText）→ 文本值只能构造函数带**
- `set_Key` 是显式接口实现的**非公共 setter**：`GetSetMethod(true)`（含 private）才能拿到
- `ResourceDictionaryEntry` **无 DefaultText 属性**，中文文档中普通 text 条目的"文言(defaultText)" = 主条目 `ResourceReference` 的文本值（通过构造函数 `new ProjectItemReference(text, TEXT)` 写入）

**⚠️ 写方法返回 void = 成功**：`SetOrCreate`/`Remove` 返回 **void**(null)。成功判断统一 `ok == null || (ok is bool && bb)`（add/set/delete 三处）。之前 `ok is bool && bb` 把 void 成功误判成 false → "added=False"/"already exists" 都是误报（条目其实建好了）。

**set = 和 add 统一**：不要用 `ApplyRowToExisting`（改内存对象，无 setter 改不了），改为 `BuildEntryFromRow`（新构造带新值）+ `SetOrCreate`（对已有 key=更新）+ translations 写各 Locale。
- 验证（2026-08-18）：set zz_good1 → default=好文本V2、translations{zh-CHS=好文本中文V2, en=Good Text V2} 全生效，isText/contentType 保持 text ✅

**诊断小技巧：**
- entryCaps / resourceRefCaps：运行时 dump entry / ProjectItemReference 的 ctors/props/methods/setters
- ⚠️ 诊断里 `List<String>` 会被 relay 折叠成 `List`1[String]`，要转 `List<object>` 才能展开显示
- "每次全新 key 都报 already exists" → 多是 SetOrCreate 实际成功但判断误报，先怀疑判断而非真失败

## 已实测验证清单
- ✅ 定位 Localization 库 / Localization Table（LocalizationTablePluginWrapper）
- ✅ `ExportTranslations()` 枚举 991 行（cluster_hmi）
- ✅ 读行 key：`get_ResourceName()` → 如 "1196"
- ✅ 读翻译：`get_Translations()` → KeyValuePair 列表，`get_Key`(en/zh-CHS) + `get_Value`(翻译文本)
- ✅ 确认语言集合：en + zh-CHS
- ✅ **创建/更新 text 条目（2026-08-18 v13）：add/set 用 `new ResourceDictionaryEntry(key, new ProjectItemReference(text, TEXT))` 全打通，key/type/defaultText/translations 全生效**
- ✅ **读取资源/字体引用（2026-08-18 v13 打通）：`kz_localized_resources` → `get_Entries()` → ResourceDictionaryEntry → get_ResourceReference() → Target(FontFamily)，字体行 isText=False**
- ✅ 字体条目：`SourceHanSansSCfontFamily` / `_medium` → `FontFamily` targetName=`SourceHanSansSC_new`
- ❌ `get_Children()` 返回空（**误导，勿当无数据**）
- ✅ **v13 `kz_loc_entry_*` 完整 CRUD（2026-08-18 打通回归）：list/get/add/set/delete 全打通；add/set 用正确构造+SetOrCreate，key/type/defaultText/translations 全生效**
- ✅ **新增/修改字体引用条目（2026-08-19 打通）：kz_loc_entry_add/set 用 type=font/style/node + targetRef=@obj裸对象（不能路径），isText=False/ContentType=ABSOLUTE；可新增并 set 改 target 到另一字体**
- ✅ v13 增改删按 key 单个操作，**不删表不重建**（取代 v8 的 rebuild/delete 备份流）
- ✅ **新增语言列首选 `kz_loc_entry_add_language`（2026-08-19 打通）：CreateLocaleCommandRecord.CreateProjectItem，真正新建 Locale，target+lang，实测 languageCount 14→15、translations 出现新语言列（KVP 方式已废弃，不再用）**
- ✅ **删除语言列 `kz_loc_entry_delete_language`（2026-08-19 打通）：get_Locales 找匹配 Language → 项目项 Delete()，等价 GUI Delete ProjectItem；实测建→删 zz_del_probe，itemCount 17→16；找不到 lang 不删任何内容**
- ❌ `kz_loc_entry_rename` 已删除（2026-08-19 老隋要求，暂时不需要）
- ✅ 语言列规则：**语言名称不可重复、需用缩写**（老隋要求）
- ✅ **删除 key 是整表级联（2026-08-19 实测）**：`kz_loc_entry_delete 里程` → 主表 found=False 后，逐行扫 226 行（ExportTranslations）无残留 + get_Entries 全条目无残留 + **14 个 locale 逐个 `GetEntry(里程)` 全部拿不到**。Remove(key, true) 同步清主表与所有 locale 字典，无需额外清理。
- ⚠️ 行只读：改字段 = v13 用 `kz_loc_entry_set`（重建+SetOrCreate 更新，type 保持）；不用底层删表+建表

## 相关主题
- 节点/属性：kanzi-ui skill
- 资源创建：kanzi-resource-create skill
- 导入导出：参考老隋 ExcelPlugin（NPOI）
