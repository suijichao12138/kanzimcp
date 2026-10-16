---
name: kanzi-prefab
description: Kanzi 引用模板（Node2DPrefabPlaceholder）：把节点创建为占位符类型并设 Node2DPrefabPlaceholderTemplate 指向模板。
---
## 🚫 命名铁律（创建前必读）

> 创建任何东西（节点/资源/动画/别名/条目）时，**名字禁止特殊字符**：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格。
> **允许中文，推荐英文**（中文名可用，但英文更稳妥，避免跨工具编码问题）。
> 不要以数字开头（部分 API 限制）。
> 错误：`text/header` `bg.1` `a|b` `C:\temp` `new node`；正确：`text_header` `bg_1` `标题文本` `header-text`。

## 引用模板（Prefab Placeholder，2026-08-07 实测打通）

> ⚠️ **关键坑**：Kanzi 里"节点引用模板/预制体"**不是**给节点设 `Node.Prefab` 属性（不支持），而是把节点创建为 **`Node2DPrefabPlaceholder`** 类型。这类节点天然带 `Node2DPrefabPlaceholderTemplate` 属性（ResourceReference，指向 Node2DPrefabTemplate），设置成目标模板即可。工程现有实例：`gear_mini_default` / `gear_driving` 都引用 gear 模板。

```python
# 1. 定位模板（Prefabs 库 @obj121 = Prefabs）
mcp kz_invoke target=@obj121 method=get_Children
# → 找目标 Node2DPrefabTemplate, 如: @obj342 POP / @obj331 TextPrefab_pop / @obj325 ImagePrefab / @obj329 gear / @obj324 TextPrefab_text
# 模板根节点类型看 get_RootNode2D: TextPrefab_* 的 root 是 TextBlock2D(文本), ImagePrefab 的 root 是 Image2D(图片)

# 2. 创建 Node2DPrefabPlaceholder 类型节点（在 Info 或任意节点下）
mcp kz_create_node parent=/Screens/Screen/RootPage/Info type=Node2DPrefabPlaceholder name=warning_pop
# → ✅ 节点已创建: @obj5279 (类型=Node2DPrefabPlaceholderPluginWrapper)

# 3. 设 Node2DPrefabPlaceholderTemplate = 模板引用（ResourceReference！用 set_Item, 不用 Set）
mcp kz_invoke target=@obj5279 method=set_Item args=["Node2DPrefabPlaceholderTemplate","@obj342"]
# → ✅ 读回 get_Item = "POP" 即可确认成功
```

**📌 同一方法可引用任意模板（2026-08-07 实测，Info 下）：**
- `warning_pop` → **POP**（Node2DPrefabPlaceholder）✅
- `test_text` → **TextPrefab_text**（模板 root=TextBlock2D 文本）✅
- `test_image` → **ImagePrefab**（模板 root=Image2D 图片）✅
- 已有参考：`gear_mini_default` → gear 、`gear_driving` → gear_driving

> ⚠️ 若用 EmptyNode2D 建节点再 AddProperty("Node2DPrefabPlaceholderTemplate") 会失败（"ProjectItem of type..."），因为该属性不属于普通 EmptyNode2D。**必须用 Node2DPrefabPlaceholder 类型创建。**
> ⚠️ `kz_delete_node` 按路径能删除冲突/错误的占位节点（如误建的 EmptyNode2D warning_pop）。
