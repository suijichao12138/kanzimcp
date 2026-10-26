---
name: kanzi-alias
description: Kanzi 创建节点别名 Alias：ResourceDictionary.CreateNodeAliasEntry 对象重载，遍历拿节点引用，验证 NodeReferenceBase。
---
## 🚫 命名铁律（创建前必读）

> 创建任何东西（节点/资源/动画/别名/条目）时，**名字禁止特殊字符**：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格。
> **允许中文，推荐英文**（中文名可用，但英文更稳妥，避免跨工具编码问题）。
> 不要以数字开头（部分 API 限制）。
> 错误：`text/header` `bg.1` `a|b` `C:\temp` `new node`；正确：`text_header` `bg_1` `标题文本` `header-text`。

### 🔍 创建前查重（幂等，2026-10-26 加，协议铁律第17条）

> 子会话可能被重派重试，**不假设本次任务全新**。创建别名前先查目标资源字典里是否已有同别名，**已存在则跳过创建**，回报注明「N 个已存在跳过」。

```python
# 取目标节点资源字典，枚举已有别名（NodeReference）：
mcp kz_invoke target=<Screen> method=get_ResourceDictionary
mcp kz_invoke target=<RD ref> method=get_NodeReferences
# → 逐个比对别名，本次要创建的别名已存在 → 跳过创建（记入「已存在跳过」）
```

## 🌟 创建别名 Alias（2026-10-13 实测打通）

> **别名（Alias）**：对节点的稳定引用，用 `#别名` 访问，节点在树里移动也不影响。
> 必须挂在**资源字典（Resource Dictionary）**里。Screen 节点和 prefab 根节点默认带资源字典。
> 用途：绑定表达式 `{#别名/属性}`、引擎 API `lookupNode("#别名")`、Action 的 Target Item。
>
> **底层 API（Studio 插件 API，kanzidocmcp 文档确认）**：
> - `ResourceDictionary.CreateNodeAliasEntry(string resourceID, Node node)` —— **对象重载（推荐，2026-10-14）**
> - `ResourceDictionary.CreateNodeAliasEntry(string resourceID, string relativePath)` —— 字符串重载（❌ 不可靠，建的是虚别名）
> - `ResourceDictionary.DeleteEntry(string resourceID)` —— 删除别名
> - `ResourceDictionary.NodeReferences` —— 枚举所有别名 `[key, 指向]`

```python
# 1. 拿节点的资源字典（Screen 默认有字典）
mcp kz_invoke target=/Screens/Screen method=get_ResourceDictionary
# → ref_id = @obj5567  (ResourceDictionaryWrapper)

# 2. 遍历节点树拿到目标节点的对象引用（Screen → RootPage → Info）
mcp kz_invoke target=/Screens/Screen method=get_Children
# → ref_id = @obj4924 (PageHostPluginWrapper / RootPage)
mcp kz_invoke target=@obj4924 method=get_Children
# → ref_id = @obj8466 (EmptyNode2DPluginWrapper / Info)  ← 目标节点

# 3. ⚠️ 创建别名：必须用【对象重载】，第二个参数传节点对象引用
mcp kz_invoke target=@obj5567 method=CreateNodeAliasEntry args=["@string:Info", "@obj8466"]
# → ✅ 调用成功（无返回值）
# ⚠️ 用字符串重载 CreateNodeAliasEntry("Info", "Screens/Screen/RootPage/Info") 会建出虚别名，
#    没真正引用到节点（2026-10-14 实测：建完 DeleteEntry 报 No entry exists）！

# 4. 验证：枚举别名，确认 Value 是 NodeReferenceBase（真引用）
mcp kz_invoke target=@obj5567 method=get_NodeReferences
# → name = [Info, Screens/Screen/RootPage/Info]  ✅ 路径正确
# → 取 Value: ref_id = @obj8468 / type = NodeReferenceBase / name = Screens/Screen/RootPage/Info

# 5. 删除别名（改错时）
mcp kz_invoke target=@obj5567 method=DeleteEntry args=["@string:Info"]
# → ✅ 结果: True

# 6. 保存工程（kz_save_project 内部走 ExecutePluginCommand 会失败！用 GeneratedCommandInvoker）
mcp kz_invoke target=@studio method=get_Commands
# → ref_id = @obj1153 (GeneratedCommandInvoker)
mcp kz_invoke target=@obj1153 method=SaveProject args=["@project"]
# → ✅ 调用成功
```

**📌 实测要点（2026-10-13，工程 test）：**
- Screen 的资源字典 = `get_ResourceDictionary`（Screen 节点上直接拿）
- ✅ 正确指向显示为 `[Info, Screens/Screen/RootPage/Info]`（无 `@obj:` 前缀、无前导 `/`）
- ❌ 错误指向显示为 `[Info, @obj:/Screens/Screen/RootPage/Info]`（用了对象重载）
- 引擎侧用 `#Info` 访问；`kz_invoke` 的 target 不支持 `#别名` 语法（那是引擎 lookup）
- **kz_save_project 工具不可用**（ExecutePluginCommand 反射不到），保存一律走 GeneratedCommandInvoker.SaveProject(@project)
