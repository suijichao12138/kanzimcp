---
name: kanzi-loc-read
description: Kanzi 本地化读取：定位表、ExportTranslations 读全表、kz_localized_resources 读字体/资源引用。
---

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
