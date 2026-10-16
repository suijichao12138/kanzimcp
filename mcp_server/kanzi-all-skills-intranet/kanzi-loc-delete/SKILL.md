---
name: kanzi-loc-delete
description: Kanzi 本地化删表+建表（低层技能）+ 删除事故警示。删行/改字段的完整链路：读全表→内存改→删旧表→建新表→写回。
---

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
