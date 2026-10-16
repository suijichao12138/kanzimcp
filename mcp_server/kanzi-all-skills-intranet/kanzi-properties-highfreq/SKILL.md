---
name: kanzi-properties-highfreq
description: Kanzi 高频属性速查（常驻 system prompt）。布局/文本/可见性/纹理/范围等最常用 39 个属性的 UI 面板名 + 绑定写法 + 说明。查属性优先看这里，冷门属性用 search_property 或读全量版。
---

# Kanzi 高频属性速查（常驻）

> 老隋圈定的高频属性。**绑定写法列已实测 ✅**。用法：查属性 → 在本表按 UI 名搜 → 拿绑定写法。
> 冷门/没在这里的属性 → 用 skill MCP 的 `search_property` 查全量库，或读 `kanzi-properties-all` 对应分组。

## 布局与尺寸

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Layout Width` | `{@../Node.Width}` ✅ | The width of the node when used in a layout. Overr |
| `Layout Height` | `{@../Node.Height}` ✅ | The height of the node when used in a layout. Over |
| `Actual Layout Width` | `{@../Node.ActualWidth}` ✅ | The calculated width of the node when used in a la |
| `Actual Layout Height` | `{@../Node.ActualHeight}` ✅ | The calculated height of the node when used in a l |
| `Horizontal Margin` | `{@../Node.HorizontalMargin}` ✅ | Sets the horizontal space between this node and ot |
| `Vertical Margin` | `{@../Node.VerticalMargin}` ✅ | Sets the vertical space between this node and othe |
| `Horizontal Alignment` | `{@../Node.HorizontalAlignment}` ✅ | The alignment in horizontal direction the node sho |
| `Vertical Alignment` | `{@../Node.VerticalAlignment}` ✅ | The alignment in vertical direction the node shoul |

## 文本与字体

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Text` | `{@../TextBlock2D.Text}` ✅ | Sets the text content that the text node renders.  |
| `Word Wrap` | `{@../TextBlock2D.WordWrap}` ✅ | Sets whether to break long lines into multiple lin |
| `Text Horizontal Alignment` | `{@../TextConcept.TextHorizontalAlignment}` ✅ | Sets the horizontal alignment of the text. |
| `Text Vertical Alignment` | `{@../TextConcept.TextVerticalAlignment}` ✅ | Sets the vertical alignment of the text. |
| `Font Family` | `{@../TextBlock2D.FontFamily}` ✅ | The font family used to render the text. |
| `Font Size` | `{@../TextBlock2D.FontSize}` ✅ | Sets the size of the font in pixels. |
| `Font Color` | `{@../TextConcept.FontColor}` ✅ | Sets the color of the text in a 3D text node. |

## 外观：颜色/图片/可见性

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Foreground Brush` | `{@../Node.ForegroundBrush}` ✅ | The foreground brush to paint the foreground of 2D |
| `Background Brush` | `{@../Node.BackgroundBrush}` ✅ | The background brush to paint the background of 2D |
| `Opacity` | `{@../Node.Opacity}` ✅ | Opacity of the node. |
| `Visible` | `{@../Node.Visible}` ✅ | When disabled, Kanzi does not render the node. |
| `Texture` | `{@../Texture}` ✅ | Sets the texture of the material. |

## Nine Patch 九宫格图片

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Top Image` | `{@../NinePatchImage.TopImage}` ✅ | The image to use in the middle of the top row. |
| `Bottom Image` | `{@../NinePatchImage.BottomImage}` ✅ | The image to use in middle of the bottom row. |
| `Left Image` | `{@../NinePatchImage.LeftImage}` ✅ | The image to use in the center-left. |
| `Right Image` | `{@../NinePatchImage.RightImage}` ✅ | The image to use in the center-right. |
| `Center Image` | `{@../NinePatchImage.CenterImage}` ✅ | The image to use in the center. |
| `Top-Left Image` | `{@../NinePatchImage.TopLeftImage}` ✅ | The image to use in the top-left corner. |
| `Top-Right Image` | `{@../NinePatchImage.TopRightImage}` ✅ | The image to use in the top-right corner. |
| `Bottom-Left Image` | `{@../NinePatchImage.BottomLeftImage}` ✅ | Image to use in the bottom-left corner. |
| `Bottom-Right Image` | `{@../NinePatchImage.BottomRightImage}` ✅ | The image to use in the bottom-right corner. |

## 范围值

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Maximum Value` | `{@../Range.Maximum}` ✅ | The maximum value that the range allows. |
| `Minimum Value` | `{@../Range.Minimum}` ✅ | The minimum value that the range allows. |
| `Enabled` | `{@../Node.Enabled}` ✅ | Whether to apply this effect. |

## 变换

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Render Transformation` | `{@../Node.RenderTransformation}` ✅ | The 2D transformation to be applied after layoutin |
| `Render Transformation Origin` | `{@../Node.RenderTransformationOrigin}` ✅ | Sets the render transform origin in relative coord |

## 概念（不是属性，是节点/管理器）

| 名称 | 说明 |
|------|------|
| `State Manager` | 状态机组件（StateManager），见 kanzi-state-manager skill |
| `Stack Layout` | 堆栈布局（StackLayout2D），见 kanzi-layout skill |
| `Text Block` | 文本节点（TextBlock2D），见 kanzi-text skill |

> 完整分组（含绑定写法）见 `kanzi-properties-all` 合并全量版。