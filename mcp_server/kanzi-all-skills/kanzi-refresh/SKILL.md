---
name: kanzi-refresh
description: Kanzi 刷新工程树 + 刷新 Preview。创建任何对象后必须 SelectProjectItems 刷工程树；截图前必须 RestartPreview 刷 Preview。用 kz_invoke 反射调 Commands（GeneratedCommandInvoker），不加专用工具。
---

# Kanzi 刷新工程树 / 刷新 Preview

> **规则**：任何创建完成后必须刷新工程树；任何截图前必须刷新 Preview。否则 Studio 里看不到新内容 / 截到旧画面。
> **原理**：插件无专用刷新工具，但 `@studio.get_Commands()` 返回的 GeneratedCommandInvoker 有这两个方法（2026-10-21 阿里云实机验证通过）。

## 唯一前置：拿 Commands 对象

每次连接编号会变，先动态取（不写死 @obj）：

```python
kz_invoke target=@studio method=get_Commands   # → @objN（GeneratedCommandInvoker）
```

## ① 刷新工程树（创建后必调）

**触发**：任何创建操作完成后 —— 新建节点、模板（Prefab）、属性、状态机（StateManager/StateGroup/State/StateObject）、多国语表、纹理、动画、笔刷、资源条目、别名等。

```python
# 传路径（最简单，推荐）
kz_invoke target=@objN method=SelectProjectItems args=["/Screens/Screen/RootPage/新建节点名"]
# 或传 @obj 引用（刚创建返回的 ref 也行）
kz_invoke target=@objN method=SelectProjectItems args=["@obj:xxx"]
```

- 作用：选中该工程项 → 工程树滚动定位 + 刷新显示，新内容立即可见。
- 批量创建后选最后一个/代表节点即可。

## ② 刷新 Preview（截图前必调）

**触发**：每次截图之前。

```python
kz_invoke target=@objN method=RestartPreview   # 重启 Preview 进程
```

- 刷新后略等 Preview 重启完成再截图（sleep 1~2s 或调 kz_health 确认）。

## 完整示例

```python
# 1. 拿 Commands
kz_invoke target=@studio method=get_Commands    # → @objN
# 2. 创建完 → 刷工程树
kz_invoke target=@objN method=SelectProjectItems args=["/Screens/Screen/RootPage/Info/warning"]
# 3. 截图前 → 刷 Preview
kz_invoke target=@objN method=RestartPreview
```

## 相关

- 其余 Commands 方法（SaveProject/ExportBinary/StartPreview 等）见 `kanzi-save-export`。
- 截图流程见 `kanzi-screenshot`。
