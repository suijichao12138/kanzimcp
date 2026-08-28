# v8_localization — Localization 读写能力（增删改查）

基于 `v7_list_param` 完整复制的新版本（**v7_list_param 未动**）。共享文件(JsonUtils/KzMainWindow*/KzMCPChatPluginFactory/csproj/sln)与 V7 完全一致，仅 Localization 部分有改动。

## 新增能力：编辑 Localization Table（读写闭环，增量式）

新增 MCP 工具 `kz_localization`，可增/删/改/查。

**关键设计（针对网络传输优化）：** 只传要改动的**增量**数据，插件内部"读全表 → 合并 → 写回"。跨网络只传几条，不是整个 991 行表。

## 写入机制（直接 ImportTranslations 整表写回）

`set/delete` → 插件读当前全表（`ExportTranslations`）→ 合并增删改 → **直接 `ImportTranslations` 整表写回**。

## ⚠️ 核心修复：修改已有 key 时【不要 new】新行（2026-08-08 老隋指出）

**关键：`ImportTranslations` 只认表里原有的 `LocalizationTableRow` 对象实例。**
- 之前"修改"是：去掉同 key 旧行 → `new` 一个新行加进去 → 写回。**新行即使同 key 也不被识别为对已有行的更新，导致修改不生效。**
- **正确做法（当前实现）：** 修改已有 key 时，在 `current` 里找到同 resourceName 的**原有行实例**，**直接改它的 DefaultText / Translations**（反射调 setter），不 new。只有真正**新增**（表里没有该 key）才 `new` 一行。

```
set 已有 key  → current 里找同 resourceName 的原行 → ModifyExistingRow(原行, rd)（改 DefaultText/Translations）→ ImportTranslations
set 无此 key  → BuildLocalizationTableRow new 新行 → current.Add → ImportTranslations
delete        → current 过滤掉 deleteKeys（保留原行对象）→ ImportTranslations
```

## 新增工具：kz_localization（增删改查四操作）

通用参数：
- `target`：LocalizationTable 对象引用或路径（如 `/Localization/LocalizationTable`、`@project`、`@objN`）
- `action`：`set`(增/改) | `delete`(删) | `get`(查单条) | `list`(查全部)

### action 和参数规则

| action | 含义 | 传参规则 |
|--------|------|----------|
| `set` | 增 / 改（表里有=覆盖改[改原行]，没有=新增[new]） | `rows`：**完整行数组** |
| `delete` | 删 | `keys`：resourceName 数组，**只传 key** |
| `get` | 查单条 | `key`：单个 resourceName，**只传 key** |
| `list` | 查全部 | 无（读整表返回） |

## 调用示例

**① 改/增（网络只传 1 条，插件内部合并写回）**
```json
{
  "target": "/Localization/LocalizationTable",
  "action": "set",
  "rows": [
    { "resourceName": "1196", "defaultText": "测试", "translations": { "en": "New", "zh-CHS": "测试" } }
  ]
}
```

**② 删（只传 key）**
```json
{ "target": "/Localization/LocalizationTable", "action": "delete", "keys": ["1196", "2001"] }
```

**③ 查单条（只传 key）**
```json
{ "target": "/Localization/LocalizationTable", "action": "get", "key": "1196" }
```

**④ 查全部**
```json
{ "target": "/Localization/LocalizationTable", "action": "list" }
```

## rows 每行结构（set 用，完整行）
```json
{
  "resourceName": "1196",        // 资源名/键（Key，唯一标识）必填
  "defaultText": "默认文本",
  "translations": { "en": "...", "zh-CHS": "..." }   // 兼容字段名 locales
}
```

## 改动文件（相对 v7_list_param）

| 文件 | 改动 |
|------|------|
| `KzMCPReflectionBridge.cs` | 新增 `LocalizationEdit(target, action, rows, keys, key)` 及辅助方法（读全表 ExportTranslations、构造 LocalizationTableRow、**ModifyExistingRow 修改原行不 new**、ImportRows 整表写回、增删改合并逻辑） |
| `KzMCPServerClient.cs` | 工具注册 `kz_localization` + tools/call 分派 case |
| `README_v8_localization.md` | 本说明 |

（注：`JsonUtils.cs` 曾加过 `GetBool` 但无副作用；csproj 已回退到与 V7 完全一致——之前 v5 方案A 加的 AbstractLocalizationPlugin 引用、MCPLocalizationImporter.cs 均已撤销。）

## 实现要点（遵守全反射铁律）

- **不缓存** MethodInfo/类型，每次调用运行时反射
- **行类型来源（关键修复）**：运行时 `LocalizationTableRow` 是**接口**（接口 `GetConstructors` 恒空，所以不能靠 `LoadTypeByFullName` 拿到的接口 Type 去 `GetConstructors`）。改为从现有行实例的 `GetType()`（`ExportTranslations` 拿到的真实实现类）解析行类型，再用它来 `GetConstructors` 造新行 —— 这样才能拿到接口实现类上真正存在的构造器
- 构造新行（仅新增用）：**优先 3 参构造器** `(string, string, IDictionary<string,string>)`（= 老隋 CsvImporter.cs 写法），**兜底无参构造器 + 反射填充**；搜索时兼容 **Public+NonPublic** 构造器
- **修改已有 key：不 new，`ModifyExistingRow` 直接用原行对象改 DefaultText / Translations（setter 反射）**
- 整表写回：`ImportRows` → `ImportTranslations(IEnumerable<LocalizationTableRow>)`，参数类型不匹配自动 Array/List 适配，异常保留真实 InnerException
- 读全表用 `ExportTranslations` → resourceName / translations（get_Key / get_Value）
- **线程策略：与 V7 一致，未强切 UI 线程**（回退了我调试时加的 RunOnUiThread）

## 构建 & 部署

NAS：`/mnt/nas/kanzi/kanzi_mcp/v8_localization/`。Windows 用 VS 打开 `KzMCPChatPlugin.sln` 编译（Reference PluginInterface → `..\v1_mcp_server\PluginInterface.dll`），产物 dll 替换 Kanzi 插件目录旧版。

> ⚠️ 本目录所有文件遵循 SOUL.md 文件安全规则：仅 Kanzi（我）可修改，其他 agent 只读。
