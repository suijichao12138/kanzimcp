---
name: kanzi-loc-crud
description: Kanzi 本地化 CRUD（首选 v13 kz_loc_entry_*）：新增/更新 text 条目、字体资源引用条目、增删语言列。含正确构造函数。
---

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
