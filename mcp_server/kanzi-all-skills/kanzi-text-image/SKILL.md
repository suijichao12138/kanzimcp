---
name: kanzi-text-image
description: Kanzi 文本/图片/前景色/背景色设置 + KzResourceID 资源引用。TextConcept.Text、Node2D.ForegroundBrush/BackgroundBrush、Image2D.Image，含 Resource 资源条目创建。资源创建见 kanzi-resource-create。
---

---
name: kanzi-text-image
description: Kanzi 文本/图片/前景色/背景色设置 + KzResourceID 资源引用。TextConcept.Text、Node2D.ForegroundBrush/BackgroundBrush、Image2D.Image，含 Resource 资源条目创建。
---

## 文本 / 图片 / 前景色 / 背景色 设置 + ResourceID 引用原理（2026-08-07 实测打通）

老隋要求梳理文本、图片、文字前景色、文字背景色四类属性的设置，重点是 **resourceID（资源引用）** 的用法。全部在 Info 下用 4 个测试节点实测：`text`/`text_1`（TextBlock2D）与 `image`/`image_1`（Image2D）。

### 🌟 最重要的规则（老隋强调，务必记住）

> **无论你看到/想用的是 `resource:xxx`、`KzResourceID:xxx` 还是 `resourceID:xxx`，实际设置时一律写成 `KzResourceID:xxx`。**
> 使用 resource（资源引用）的形式，设置的字符串就是 **`KzResourceID:xxx`**。
> （⚠️ 不要写 `resourceID:xxx`——少 `Kz` 前缀会失败！这个坑实测踩了很久。）

### 4 节点标准示例（全部读回验证通过）

| 节点 | 类型 | 文本 | 前景色 | 背景色 | 图片 |
|------|------|------|--------|--------|------|
| **text** | TextBlock2D | `123` | `Color Brush_FFFFFF` | `Color Brush_000000` | - |
| **text_1** | TextBlock2D | `KzResourceID:123` | `KzResourceID:FFFFFF` | `KzResourceID:000000` | - |
| **image** | Image2D | - | - | - | `green_sig_num`(路径/@obj) |
| **image_1** | Image2D | - | - | - | `KzResourceID:green_sig_num` |

上面区分了两种写法：`text`/`image` 用**直接值**，`text_1`/`image_1` 用 **`KzResourceID:` resource 形式**。两者效果相同，resource 形式更通用。

### 属性名（TextBlock2D / Image2D，GetAddableProperties 确认）

- **文本内容**：`TextConcept.Text`（string）
- **文字前景色**：`Node2D.ForegroundBrush`（ResourceReference）⚠️ 需先 AddProperty
- **文字背景色**：`Node2D.BackgroundBrush`（ResourceReference）⚠️ 需先 AddProperty（不是 `Background`/`BackgroundColor`/`BackdropBrush`，那些都不存在）
- **图片**：`Image2D.Image`（ResourceReference，仅 Image2D 节点）

### 设置语法（set_Item 实测）

```python
# ================= 文本 TextConcept.Text（string）=================
# 直接值：用 @string: 前缀（裸文本会失败）
mcp kz_invoke target=@节点 method=set_Item args=["TextConcept.Text","@string:123"]   # → 显示 "123"
# resource 形式：
mcp kz_invoke target=@节点 method=set_Item args=["TextConcept.Text","KzResourceID:123"]  # → 存 "KzResourceID:123"

# ================= 前景色/背景色（ResourceReference，需先 AddProperty）=================
# 添加属性
mcp kz_invoke target=@节点 method=AddProperty args=["Node2D.ForegroundBrush"]
mcp kz_invoke target=@节点 method=AddProperty args=["Node2D.BackgroundBrush"]
# 设置（两种等价写法）：
# 写法A：直接用 @obj 刷资源对象引用（@obj5736/@obj5735 这个引用怎么获取见下方说明）
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.ForegroundBrush","@obj5736"]   # Color Brush_FFFFFF
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.BackgroundBrush","@obj5735"]   # Color Brush_000000
#    ▶ 获取颜色刷引用：Brushes 库 get_Children → Color Brush_FFFFFF = @obj5736
#      （完整流程见下方「### 资源定位（在工程里找 brush 和图片）」章节）
# 写法B：resource 形式（KzResourceID:）
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.ForegroundBrush","KzResourceID:FFFFFF"]
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.BackgroundBrush","KzResourceID:000000"]

# ================= 图片 Image2D.Image（ResourceReference，仅 Image2D 节点）=================
# 写法A：@obj 图片资源对象引用（最稳；@obj5831 这个引用怎么获取见下方说明）
mcp kz_invoke target=@节点 method=set_Item args=["Image2D.Image","@obj5831"]   # green_sig_num
#    ▶ 获取图片引用：Textures 库 → 子库 adas → get_Children → green_sig_num = @obj5831
#      （完整流程见下方「### 资源定位（在工程里找 brush 和图片）」章节）
# 写法B：resource 形式（KzResourceID:资源名）
mcp kz_invoke target=@节点 method=set_Item args=["Image2D.Image","KzResourceID:green_sig_num"]
# 写法C：完整路径字符串
mcp kz_invoke target=@节点 method=set_Item args=["Image2D.Image","Textures/adas/green_sig_num"]
```

### ResourceReference 属性（ForegroundBrush/BackgroundBrush/Image）设值规则

| 写法 | Foreground/Bg Brush | Image |
|------|:---:|:---:|
| **`KzResourceID:资源名`** | ✅ | ✅ |
| **`@obj资源对象引用`** | ✅ | ✅（最稳） |
| **完整路径** `Textures/adas/xxx` | ❌ | ✅ |
| `resourceID:xxx`（无Kz） | ❌ | ❌ |
| `@brush:`/`@image:`/`@texture:` | ❌ | ❌ |
| 相对路径 `adas/xxx` | ❌ | ❌（Null） |

> ⚠️ **读回 Null 可能是时序延迟**：设完立即读回可能显示 `< Null >`，延迟约 1 秒再读就稳定为资源名。别被瞬时 Null 误导判定失败。

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

> 颜色笔刷/纹理/字体等资源创建 → `kanzi-resource-create` skill。

