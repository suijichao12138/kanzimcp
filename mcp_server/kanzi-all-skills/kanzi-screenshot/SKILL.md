---
name: kanzi-screenshot
description: Kanzi Preview/Studio 截图。流程：kz_enum_all_windows 定位 Studio 主窗 PID → kz_screenshot_preview 一键截图（有 Preview 截 Preview，没有截 Studio 主窗）。不截主屏幕。
---

# Kanzi Preview/Studio 截图

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



## 完整流程（两步）

```python
# 1. 定位 Studio 主窗 PID（title 含 "Kanzi Studio" 的 HwndWrapper[KanziStudio]，注意字段可能多行）
kz_enum_all_windows {}

# 2. 一键截图，pid 填上面找到的 Studio 主窗 PID
kz_screenshot_preview {"pid": <Studio主窗pid>, "maxSide": 1600}
```

## 返回

PNG base64，含 `target` 字段：
- `preview` = 截到 Preview
- `studio` = 截到 Studio 主窗

## 规则
- 有 Preview（title 含 preview）→ 截 Preview
- 没有 → 截 Studio 主窗
- 不截主屏幕、不截浏览器

## 可视化
base64 解码成 png 发用户确认。
