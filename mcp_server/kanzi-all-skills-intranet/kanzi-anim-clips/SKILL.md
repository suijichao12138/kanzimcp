---
name: kanzi-anim-clips
description: Kanzi 关键帧与动画数据：关键帧在 Animation Data 内部（非 Timeline）、动画组 AnimationClip 字段。
---

## ⭐ 关键帧（在 Animation Data 内部，非 Timeline！2026-08-08 模型纠偏）

> ⚠️ 老隋纠正：**关键帧在 Animation Data 内部**，Animation Data = 单一关键帧动画（定义 keyframes + target property）。
> **Animation Clip = 组合多个 Animation Data**（"一个组合可以包含很多 animation"）。
> Timeline Entry / Timeline Sequence 是**另一套**（操纵动画的：重复/缩放/targeting/blending），**不是关键帧本体，不要碰**（老隋："我现在只要 animationclip 和 animation，不要其他的"）。

### 实测证据：现有动画组确实引用多个 Animation（Clip 组合的本质）
| 动画组 | 引用动画数 |
|---|---|
| 01circle_scale | 3（SCALE_X/Y/Z）|
| modern_sett_navi scale | 2 |
| 其余多数 | 1 |
引用存于 `AnimationDataChildReferences`。✅ Kanzi 能力存在（现有组能引多个），缺的是 bridge 写通道。

> ⚠️ 曾误入歧途（2026-08-08 上午）：往 Timeline Sequences 库建 TimelineSequence/TimelineEntry 并当成"关键帧"，是**认知错误**。Timeline Entry 不是关键帧本体，是操纵动画的容器。已废弃该方向。

### ✅ 重大突破：动画组引用动画（AnimationDataChildReferences）—— 用 ReparentProjectItem 实现（2026-08-08）

> **之前卡住的核心难点已解决**：让 Animation Clip 引用 Animation。**正确方法是 `ReparentProjectItem` + 两个完整路径字符串参数**（不是 @obj 引用、不是 `set_Item("AnimationDataChildReferences",...)`）。老隋在 Studio GUI 实测确认：`01circle_innerRadius` 已成功引用到 `adas.num`。

```python
# 拿命令执行器
@studio.get_Commands() → GeneratedCommandInvoker (@obj2)

# ReparentProjectItem(动画完整路径, 动画组完整路径) → 让动画组引用动画 ✅
kz_invoke target=@obj2 method=ReparentProjectItem \
  args=["Animation Data/adas.num", "Animation Clips/01circle_innerRadius"]
→ ✅ 调用成功（无返回值）
```

**用法铁律（贯穿整个踩坑）**：
1. 两个参数**都必须是完整路径字符串**（`Animation Data/xxx`、`Animation Clips/xxx`），**不带开头 `/`，也用不得 @obj 引用**。
2. 用 @obj 引用调用会报「Adding child animations is not supported」——但**路径字符串调用返回成功**且真正建立引用。
3. 返回「✅ 调用成功」即代表真的建立了**引用**关系（不是层级移动）——不要用 `get_Children` 验证（动画组的引用不在 children 里，get_Children 查空是正常的）。**正确验证方式：
   ```
   # 读动画组引用的动画列表（关键验证方法！不是 get_ 方法，是 get_Item 索引器）
   clip.get_Item("AnimationDataChildReferences")  # → 返回引用的动画列表，每项含 ref_id + name
   # 例: 01circle_innerRadius → [InnerRadius_1(原有), adas.num(Reparent新加)]
   # 注: get_AnimationDataChildReferences（get_ 前缀）在 wrapper 上找不到，用 get_Item 才对
   ```
4. ⚠️ 但注意：用 get_Parent 查动画项仍是原库（这里 adas.num 的 parent 仍是 Animation Data）——Reparent 建立的是**引用**，动画项物理位置不变。

**之前失败的老路（勿再试）**：
- ❌ `clip.set_Item("AnimationDataChildReferences", <任何形式>)` 失败——`@anim:`/`@obj`/路径都不行，报 "cannot be converted to studio internal property value"。这是引用集合属性，bridge 纯反射没法直接构造属性值封装。
- ❌ `ReparentProjectItem` 用 @obj 引用当参数 → 报「Adding child animations is not supported」。

> **老总结修正**：创建（Animation/AnimationClip/AnimationChildClip/**TimelineSequence/TimelineEntry**）✅ 全通；子片段引用动画项 ✅；关键帧创建+时间字段配置 ✅；**动画组引用动画（AnimationDataChildReferences）✅ 现可用——用 ReparentProjectItem 完整路径。**
