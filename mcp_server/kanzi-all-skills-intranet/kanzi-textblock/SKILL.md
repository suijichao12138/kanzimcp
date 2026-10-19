---
name: kanzi-textblock
description: Kanzi TextBlock2D 文本排版配置：创建文本节点、文本内容 TextConcept.Text、字号 FontStyleConcept.Size、对齐/换行/字距、自定义属性。字体/颜色设置见 kanzi-resource-set。
---

## TextBlock2D 文本排版配置

### 1. 创建文本节点
```python
# 创建 TextBlock2D 节点（节点骨架，不含任何资源设置）
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_create_node","arguments":{"parent":"/Screens/Screen/RootPage/Info/warning","type":"TextBlock2D","name":"text"}}})
```

### 2. 文本内容（TextConcept.Text）
```python
# 直接值：用 @string: 前缀（裸文本会失败）
mcp kz_invoke target=@节点 method=set_Item args=["TextConcept.Text","@string:123"]
# 或绑定形式：KzResourceID:123（存资源名）
mcp kz_invoke target=@节点 method=set_Item args=["TextConcept.Text","KzResourceID:123"]
```

### 3. 字号（FontStyleConcept.Size）
```python
mcp kz_invoke target=@节点 method=AddProperty args=["FontStyleConcept.Size"]
mcp kz_invoke target=@节点 method=set_Item args=["FontStyleConcept.Size", 36]
```

### 4. 对齐 / 换行（非资源排版属性）
| UI 属性 | 绑定/属性名 | 说明 |
|---------|------------|------|
| Text Horizontal Alignment | `TextConcept.TextHorizontalAlignment` | 文本水平对齐 |
| Text Vertical Alignment | `TextConcept.TextVerticalAlignment` | 文本垂直对齐 |
| Word Wrap | `TextBlockConcept.WordWrap` | 是否自动换行 |
| Character Spacing | `FontStyleConcept.CharacterSpacing` | 字距 |

```python
mcp kz_invoke target=@节点 method=set_Item args=["TextConcept.TextHorizontalAlignment","@enum:CENTER"]
mcp kz_invoke target=@节点 method=set_Item args=["TextBlockConcept.WordWrap", true]
```

### 5. 自定义属性
```python
mcp kz_invoke target=@节点 method=AddProperty args=["warning.value"]
```

## ⚠️ 文本颜色规则（重要）

> **Text Block 2D 文本颜色 → `Node2D.ForegroundBrush`**（颜色刷，需先 AddProperty）。
> **`Font Color` 只能给 Text Block 3D，不能设置 Text Block 2D 颜色**。
> 颜色/字体等的设置 → `kanzi-resource-set` skill。
