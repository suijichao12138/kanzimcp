---
name: kanzi-resource-create
description: Kanzi 创建 Resource 资源条目（ResourceDictionary + CreateResourceEntry）。在节点/页面创建资源条目（颜色刷/图片等），resourceID 的 @string 前缀坑。不含节点上设置资源引用（那是 kanzi-resource-set）。
---

# 创建 Resource 资源条目（在节点/页面创建资源条目）

### 🌟 创建 Resource 资源条目（ResourceDictionary + CreateResourceEntry，2026-08-07 v6 实测打通）

> **背景**：之前 `CreateResourceDictionary()` 返回空、拿不到对象去调 `CreateResourceEntry` 的根因，已在 **v6** 修复：`WrapResult` 增加 `ResourceDictionary` 特判（类型名含 ResourceDictionary 时 `RegisterObject` 返回对象引用，不再被当成空集合展开）。**v6 之后可用此方法在节点/页面上创建资源条目**（如颜色刷、图片）。

#### 核心流程（两步）

**第1步：在目标节点上创建（或取）ResourceDictionary**
```python
# 写法A：新建 — 节点调用 CreateResourceDictionary()
mcp kz_invoke target=/Screens/Screen/RootPage/Info/text_1 method=CreateResourceDictionary args=[]
# → 返回 ref_id = @objXXX (类型 ResourceDictionaryWrapper)

# 写法B：取已有 — 节点调用 get_ResourceDictionary()
mcp kz_invoke target=@节点 method=get_ResourceDictionary args=[]
```

**第2步：往字典里加资源条目 CreateResourceEntry(resourceID, 资源对象)**
```python
mcp kz_invoke target=@objRD method=CreateResourceEntry args=["@string:FFFFFF", "@obj9"]
```

#### ⚠️🌟 最关键的坑：resourceID 纯数字必须加 `@string:` 前缀！

> **resourceID 是数字字符串（如 `000000`）时，必须写 `@string:000000`**，否则会被插件的参数解析层 `int.TryParse` 误转成整数 `0`，导致 `CreateResourceEntry` 匹配失败报错：*"类型 System.Int32 的对象无法转换为类型 System.String"*。
> `FFFFFF` 这类含字母的不是数字，不转 int，但**统一加 `@string:` 前缀最稳**。

#### 完整实测示例（cluster_hmi，2026-08-07）

```python
# 1. 先拿到要注册的资源对象引用（颜色刷 / 图片）
#    颜色刷：Brushes 库 get_Children → Color Brush_FFFFFF = @obj9, Color Brush_000000 = @obj8
#    图片：   Textures 库 → adas 子库 → get_Children → green_sig_num = @obj384

# 2. text_1 节点：创建 RD 并加颜色刷
mcp kz_invoke target=/Screens/Screen/RootPage/Info/text_1 method=CreateResourceDictionary args=[]   # → @obj2
mcp kz_invoke target=@obj2 method=CreateResourceEntry args=["@string:FFFFFF", "@obj9"]          # ✅ (第二次报 already exists 正常)
mcp kz_invoke target=@obj2 method=CreateResourceEntry args=["@string:000000", "@obj8"]          # ✅

# 3. image_1 节点：创建 RD 并加图片
mcp kz_invoke target=/Screens/Screen/RootPage/Info/image_1 method=CreateResourceDictionary args=[] # → @obj1066
mcp kz_invoke target=@obj1066 method=CreateResourceEntry args=["@string:green_sig_num", "@obj384"] # ✅

# 4. 验证：get_Resources 应列出 KeyValuePair 条目 [resourceID, 资源名]
mcp kz_invoke target=@objRD method=get_Resources args=[]
# → name = [FFFFFF, ... Name = Color Brush_FFFFFF]
# → name = [000000, ... Name = Color Brush_000000]
# → name = [green_sig_num, ...SingleTexturePluginWrapper Name = green_sig_num]
```

#### 要点
- `CreateResourceDictionary()` 返回 `ResourceDictionaryWrapper` ref；**重复创建同 ID 的条目报 "Another entry with the same Resource ID already exists"（正常保护）**。
- 资源 ref 每次连接 Studio 动态分配，需重新定位，不能硬编码。
- **保存用正规路径**：`@studio.get_Commands()` → `GeneratedCommandInvoker` → `SaveProject(@project)`（⚠️ 不要用 `kz_save_project`，那个工具是坏的/残缺的，见 kanzi-save-export skill）。

> 颜色笔刷/纹理/字体等资源创建 → `kanzi-resource-brush` / `kanzi-resource-texture` / `kanzi-resource-font` skill。

