---
name: kanzi-properties-quickref
description: Kanzi 常用属性速查（给 kanzi-ui / kanzi-binding skill 引用）。每个属性给出 UI 属性面板名称、绑定表达式写法、说明。按节点分组。
---

# Kanzi 常用属性速查

> 用途：给 **kanzi-ui**（设置属性）和 **kanzi-binding**（绑定取值）两个 skill 当字典用。
> 每属性三列：**UI 名**（属性面板里显示的名字，UI 设置用）| **绑定写法**（绑定表达式里的写法，去空格驼峰）| **说明**。
> 绑定写法已验证的标 ✅，规则生成的标 ⚙（用前可在 Studio 绑定编辑器确认）。

## 绑定名规则

| 规则 | 示例 |
|------|------|
| UI 属性名去空格、首字母大写后续小写 | `Actual Layout Width` → `Node.ActualWidth` |
| 路径写在 `{}` 里：`{@路径/属性名}` | `{@../Node.ActualWidth}` |
| 相对路径：`./`自己 `../`父级 `#别名` | `{@./Node.Opacity}` / `{@#Main/Node.Width}` |
| 取属性字段用点号（变换/颜色） | `{@../Node.RenderTransformation}.translationX` |

## Activity

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Activity Status` | `{@../Activity.ActivityStatus}` ✅ | Sets the possible states of the Activity when its Activity Host activates or deactivates that Activity. |

## Blit Render Pass

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Texture 0` | `{@../RenderPass.Texture0}` ✅ | Sets the first texture you want the Blit render pass to blit. |
| `Texture 1` | `{@../RenderPass.Texture1}` ✅ | Sets the second texture you want the Blit render pass to blit. |
| `Texture 2` | `{@../RenderPass.Texture2}` ✅ | Sets the third texture you want the Blit render pass to blit. |
| `Texture 3` | `{@../RenderPass.Texture3}` ✅ | Sets the fourth texture you want the Blit render pass to blit. |

## Blur Effect 2D

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Blur Quality` | `{@../BlurEffect2D.BlurQuality}` ✅ | Sets the visual quality of the blur. Lower quality uses less computing and memory resources. |
| `Blur Radius` | `{@../BlurEffect2D.BlurRadius}` ✅ | Blur radius for the material. |
| `Masked Blur` | `{@../BlurEffect2D.MaskedBlur}` ✅ | Sets whether to blur only the pixels whose alpha channel value is not zero. When you enable this property, the blur does not spread to fully transparent pixels … |

## Brush

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Background Brush` | `{@../Node.BackgroundBrush}` ✅ | The background brush to paint the background of 2D nodes. |
| `Brush Color` | `{@../Brush.BrushColor}` ✅ | Color for brush. Set alpha to 0 to disable brush. |
| `Brush Horizontal Tiling` | `{@../Brush.BrushHorizontalTiling}` ✅ | Horizontal Tiling for the brush. Affects the scale of texture coordinates. |
| `Brush Modulate Color` | `{@../Brush.BrushModulateColor}` ✅ | Modulation color for brush. Effects brush rendering that needs color modulation. |
| `Brush Texture` | `{@../Brush.BrushTexture}` ✅ | Texture for brush. |
| `Brush Vertical Tiling` | `{@../Brush.BrushVerticalTiling}` ✅ | Vertical Tiling for the brush. Affects the scale of texture coordinates. |
| `Composition Brush` | `{@../Node.CompositionBrush}` ✅ | The brush to use to compose 2D nodes to screen. |
| `Foreground Brush` | `{@../Node.ForegroundBrush}` ✅ | The foreground brush to paint the foreground of 2D nodes. |

## Button

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Auto Press Interval` | `{@../Button.AutoPressInterval}` ✅ | Sets the time in milliseconds after which a button that the user keeps pressed down sends the Button: Click message. While the user holds the button down, the b… |
| `Down On Hover` | `{@../Button.DownOnHover}` ✅ | Whether holding a finger on the device screen and moving it over the button transitions the button to the down state. |
| `Hold Interval` | `{@../Button.HoldInterval}` ✅ | Sets the amount of time in milliseconds that the user must hold the button pressed down for Kanzi to recognize it as a long-press gesture. To disable the long-p… |
| `Is Down` | `{@../Button.IsDown}` ✅ | Indicates whether the button is pressed and in the down state. |

## Code Behind

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Code Behind Concept` | `{@../CodeBehind.CodeBehindConcept}` ✅ | （官方无描述） |
| `Code Behind Source` | `{@../CodeBehind.CodeBehindSource}` ✅ | Sets the metaclass name of the code behind class for this node. |

## Command

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Command` | `{@../Control.Command}` ✅ | The command executed by a UI control |

## Data Context

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Data Context` | `{@../Node.DataContext}` ✅ | Source of data for this node and its descendants |

## Data-Driven Exclusive Activity Host

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Active Activity Index` | `{@../DataDrivenExclusiveActivityHost.ActiveActivityIndex}` ✅ | The index of the active Activity in the Data-Driven Exclusive Activity Host. After instantiating all Activity from a Data Source, this property refers to the on… |
| `Activity Source` | `{@../ActivityHost.ActivitySource}` ✅ | The data object that provides the data for this Activity node. |
| `Activity Template` | `{@../DataDrivenExclusiveActivityHost.ActivityTemplate}` ✅ | If set, the Data-Driven Exclusive Activity Host uses this prefab for Activity nodes that it creates. |

## Description

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Description` | `{@../Node.Description}` ✅ | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export th… |

## Dock Layout

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Side` | `{@../DockLayout2D.Side}` ✅ | The docking side of an item in the dock layout. |

## Effect

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Effect` | `{@../Node.Effect}` ✅ | Reports the runtime effect instance that this node uses. Kanzi sets the value of this property internally when the value of the Effect Prefab property in this n… |
| `Effect Prefab` | `{@../Node.EffectPrefab}` ✅ | The 2D Effect to use for this node. |

## Focus Scope

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Cyclic Focus Navigation` | `{@../FocusScope.CyclicFocusNavigation}` ✅ | Sets whether the focus chain navigation within the focus scope is cyclic. When you enable this property: * When the user navigates in the forward direction and … |
| `Focus Scope Type` | `{@../FocusScope.FocusScopeType}` ✅ | Sets the type of the focus scope node: * Group groups focusable nodes. * Fence keeps the focus chain navigation inside the scope and does not allow the focus ch… |

## Grid Layout

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Column` | `{@../GridLayout2D.Column}` ✅ | The column into which grid layout places the item. |
| `Column Span` | `{@../GridLayout2D.ColumnSpan}` ✅ | Defines the number of columns an item in a grid layout occupies. |
| `Row` | `{@../GridLayout2D.Row}` ✅ | The row into which grid layout places the item. |
| `Row Span` | `{@../GridLayout2D.RowSpan}` ✅ | Defines the number of rows an item in a grid layout occupies. |

## Grid List Box

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Calculated Offset` | `{@../TrajectoryLayout2D.CalculatedOffset}` ✅ | Reports the current relative offset of an item in the Grid List Box in proportional range [0, 1]. |

## Image

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Image` | `{@../Image2D.Image}` ✅ | The image to display. |

## Input

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Effectively Enabled` | `{@../Node.EffectivelyEnabled}` ✅ | Indicates whether this node and its ancestor nodes are enabled. Use this property in state managers and bindings to observe whether a node is effectively enable… |
| `Enabled` | `{@../Node.Enabled}` ✅ | Whether to apply this effect. |
| `Hit Testable` | `{@../Node.HitTestable}` ✅ | When enabled, the node can be hit tested. Enabling Hit Testable for a 2D node enables hit testing only for that node. Enabling Hit Testable for a 3D node enable… |

## Layout.Item

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Horizontal Alignment` | `{@../Node.HorizontalAlignment}` ✅ | The alignment in horizontal direction the node should use when it resides under a layout. |
| `Layout Height` | `{@../Node.Height}` ✅ | The height of the node when used in a layout. Overrides the default bounds of the item. |
| `Layout Width` | `{@../Node.Width}` ✅ | The width of the node when used in a layout. Overrides the default bounds of the item. |
| `Vertical Alignment` | `{@../Node.VerticalAlignment}` ✅ | The alignment in vertical direction the node should use when it resides under a layout. |
| `Actual Layout Height` | `{@../Node.ActualHeight}` ✅ | The calculated height of the node when used in a layout. |
| `Actual Layout Width` | `{@../Node.ActualWidth}` ✅ | The calculated width of the node when used in a layout. |
| `Horizontal Margin` | `{@../Node.HorizontalMargin}` ✅ | Sets the horizontal space between this node and other nodes that are adjacent to this node in a layout. To access the Horizontal Margin property fields in a bin… |
| `Vertical Margin` | `{@../Node.VerticalMargin}` ✅ | Sets the vertical space between this node and other nodes that are adjacent to this node in a layout. To access the Vertical Margin property fields in a binding… |

## List Box

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Selected Item Index` | `{@../ListBox.SelectedItemIndex}` ✅ | Sets the index of the item that is currently selected in the List Box node. A List Box node updates this property when the user scrolls that List Box node. To s… |

## List Box Item Container

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Item Index` | `{@../ListBoxItemContainer.ItemIndex}` ✅ | Reports the index of the item in the List Box Item Container. |
| `Selected` | `{@../ListBoxItemContainer.Selected}` ✅ | Indicates whether the List Box item held by this List Box Item Container is selected. The List Box sets the value of this property. |

## Mask Effect 2D

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Invert Mask` | `{@../MaskEffect2D.InvertMask}` ✅ | Whether to invert the mask so that transparent areas become opaque and opaque areas become transparent. |
| `Mask Channel` | `{@../MaskEffect2D.MaskChannel}` ✅ | Sets the texture channel to use as the input for the mask: * Alpha uses the alpha channel from the texture. This is the default. * Red uses the red color channe… |
| `Mask Height` | `{@../MaskEffect2D.MaskHeight}` ✅ | Sets the height of the mask to use in a layout. This value overrides the height of the texture that you use as the mask. |
| `Mask Horizontal Alignment` | `{@../MaskEffect2D.MaskHorizontalAlignment}` ✅ | Sets the horizontal alignment of the mask effect: * Left aligns the left edge of the mask with the left edge of the node. This is the default. * Right aligns th… |
| `Mask Offset` | `{@../MaskEffect2D.MaskOffset}` ✅ | Sets the mask offset along the X and Y axes in pixels. Kanzi applies the mask offset after stretch, alignment, and scale. |
| `Mask Scale` | `{@../MaskEffect2D.MaskScale}` ✅ | Sets the factor by which to scale the mask. Kanzi applies the scale after stretch and alignment. |
| `Mask Strength` | `{@../MaskEffect2D.MaskStrength}` ✅ | Sets the strength of the mask effect in the range from 0 to 1: * 0 disables the mask effect. * 1 applies the mask at full strength. This is the default. * Any v… |
| `Mask Stretch` | `{@../MaskEffect2D.MaskStretch}` ✅ | Sets the stretch mode of the mask effect: * None disables stretching. This is the default. * Fill stretches the mask to fill the node. * Uniform stretches the m… |
| `Mask Texture` | `{@../MaskTexture}` ✅ | Sets the texture that masks another texture or color. |
| `Mask Vertical Alignment` | `{@../MaskEffect2D.MaskVerticalAlignment}` ✅ | Sets the vertical alignment of the mask effect: * Bottom aligns the bottom edge of the mask with the bottom edge of the node. * Top aligns the top edge of the m… |
| `Mask Width` | `{@../MaskEffect2D.MaskWidth}` ✅ | Sets the width of the mask to use in a layout. This value overrides the width of the texture that you use as the mask. |
| `Use Screen Space` | `{@../MaskEffect2D.UseScreenSpace}` ✅ | Whether to layout the mask relative to the screen instead of the node. |

## Material

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Alpha Cutoff` | `{@../AlphaCutoff}` ✅ | Sets the cutoff threshold for alpha cutting. If the alpha value is less than the value of this property, Kanzi discards the fragment. The default value is 0.5. |
| `Ambient Color` | `{@../AmbientColor}` ✅ | Sets the color of the material when lights are not present. Use the Intensity (I) property field to adjust the exposure of the color. |
| `Base Color Factor` | `{@../BaseColorFactor}` ✅ | Sets the base color for the material. |
| `Base Color Texture` | `{@../BaseColorTexture}` ✅ | Sets the texture that contains the base color for the material. Use the Base Color Factor property to filter the value from this texture. |
| `Blend Intensity` | `{@../BlendIntensity}` ✅ | Controls the intensity of materials that are blended on top of an existing color. Attached property enables overriding of the blend intensity of the used materi… |
| `Blend Mode` | `{@../BlendMode}` ✅ | Sets how to combine the color and alpha values of pixels in one layer or image with those in the underlying layer or image. |
| `BRDF Lookup Table` | `{@../BRDFLookupTable}` ✅ | Gets the Bidirectional Reflectance Distribution Function (BRDF) lookup table for the material. The BRDF table is a texture that contains precomputed information… |
| `Clear Coat Normal Scale` | `{@../ClearCoatNormalScale}` ✅ | Sets the clear coat normal scale for the material. Use the scale to set the intensity of the Clear Coat Normal Texture. |
| `Clear Coat Normal Texture` | `{@../ClearCoatNormalTexture}` ✅ | Sets the texture that contains a clear coat normal map for the material. Use the Clear Coat Normal Scale property to scale the texture value. |
| `Clear Coat Roughness Factor` | `{@../ClearCoatRoughnessFactor}` ✅ | Sets the roughness of the outer clear coat layer for the material: 0 represents a smooth, glossy surface, and 1 represents a rough, diffuse surface. |
| `Clear Coat Roughness Texture` | `{@../ClearCoatRoughnessTexture}` ✅ | Sets the texture that contains a clear coat roughness map for the material. Kanzi reads the roughness from the Green channel of the texture. Use the Clear Coat … |
| `Clear Coat Strength Factor` | `{@../ClearCoatStrengthFactor}` ✅ | Sets the clear coat strength for the material: 0 represents a material with no clear coat, and 1 represents a full strength clear coat. |
| `Clear Coat Strength Texture` | `{@../ClearCoatStrengthTexture}` ✅ | Sets the texture that contains a clear coat strength map for the material. Kanzi reads the strength from the Red channel of the texture. Use the Clear Coat Stre… |
| `Cubemap Color` | `{@../CubemapColor}` ✅ | （官方无描述） |
| `Detail Base Color Factor` | `{@../DetailBaseColorFactor}` ✅ | Sets the detail base color for the material. The detail base color is alpha blended with the standard base color. |
| `Detail Base Color Texture` | `{@../DetailBaseColorTexture}` ✅ | Sets the detail texture that contains the base color for the material. Use the Detail Base Color Factor property to filter the value from this texture. The deta… |
| `Detail Clear Coat Normal Scale` | `{@../DetailClearCoatNormalScale}` ✅ | Sets the detail clear coat normal scale for the material. Use the scale to set the intensity of the Detail Clear Coat Normal Texture. |
| `Detail Clear Coat Normal Texture` | `{@../DetailClearCoatNormalTexture}` ✅ | Sets the detail texture that contains a clear coat normal map for the material. Use the Detail Clear Coat Normal Scale property to scale the texture value. |
| `Detail Clear Coat Roughness Texture` | `{@../DetailClearCoatRoughnessTexture}` ✅ | Sets the detail texture that contains a clear coat roughness map for the material. Use the Clear Coat Roughness Factor and Clear Coat Roughness Texture properti… |
| `Detail Clear Coat Strength Texture` | `{@../DetailClearCoatStrengthTexture}` ✅ | Sets the detail texture that contains a clear coat strength map for the material. Kanzi reads the strength from the Red channel of the texture. Use the Clear Co… |
| `Detail Diffuse Color Factor` | `{@../DetailDiffuseColorFactor}` ✅ | Sets the detail diffuse color for the material. Kanzi alpha blends the detail diffuse color with the standard diffuse color. |
| `Detail Diffuse Color Texture` | `{@../DetailDiffuseColorTexture}` ✅ | Sets the detail texture that contains the diffuse color for the material. Use the Detail Diffuse Color Factor property to filter the value from this texture. Ka… |
| `Detail Emissive Factor` | `{@../DetailEmissiveFactor}` ✅ | Sets the color of the light that is emitted from a detail texture for the material. Use the Intensity (I) property field to adjust the brightness of the light. … |
| `Detail Emissive Texture` | `{@../DetailEmissiveTexture}` ✅ | Sets the detail texture that contains the light emitted from the material. Use the Detail Emissive Factor property to scale the value from this texture. Use the… |
| `Detail Glossiness Texture` | `{@../DetailGlossinessTexture}` ✅ | Sets the detail texture that contains a glossiness map for the material. Kanzi reads the glossiness from the Alpha channel of this texture. Use the Glossiness F… |
| `Detail Metallic Texture` | `{@../DetailMetallicTexture}` ✅ | Sets the detail texture that contains a metallic map for the material. Kanzi reads the metalness from the Blue channel of this texture. Use the Metallic Factor … |
| `Detail Normal Scale` | `{@../DetailNormalScale}` ✅ | Sets the detail normal scale for the material. Use the scale to set the intensity of the Detail Normal Texture. |
| `Detail Normal Texture` | `{@../DetailNormalTexture}` ✅ | Sets the detail texture that contains a normal map for the material. Use the Detail Normal Scale property to scale the texture value. |
| `Detail Occlusion Strength` | `{@../DetailOcclusionStrength}` ✅ | Sets the detail occlusion strength for the material. Use the strength to set the intensity of the Detail Occlusion Texture. |
| `Detail Occlusion Texture` | `{@../DetailOcclusionTexture}` ✅ | Sets the detail texture that contains an occlusion map for the material. Kanzi reads the occlusion from the Red channel of this texture. Use the Detail Occlusio… |
| `Detail Roughness Texture` | `{@../DetailRoughnessTexture}` ✅ | Sets the detail texture that contains a roughness map for the material. Kanzi reads the roughness from the Green channel of the texture. Use the Roughness Facto… |
| `Detail Specular Color Factor` | `{@../DetailSpecularColorFactor}` ✅ | Sets the detail specular color for the material. Kanzi alpha blends the detail specular color with the standard specular color. |
| `Detail Specular Color Texture` | `{@../DetailSpecularColorTexture}` ✅ | Sets the detail texture that contains the specular color for the material. Use the Detail Specular Color Factor property to filter the value from this texture. … |
| `Detail Texture Offset` | `{@../DetailTextureOffset}` ✅ | Sets the detail texture offset for the material. Kanzi adds this value to the UVs to produce a second set of detail UVs to use for all detail texture properties… |
| `Detail Texture Tiling` | `{@../DetailTextureTiling}` ✅ | Sets the detail texture tiling factor for the material. Kanzi multiplies this value by the UVs to produce a second set of detail UVs to use for all detail textu… |
| `Diffuse Color` | `{@../DiffuseColor}` ✅ | Sets the color of the material when it is lit by a light. |
| `Diffuse Color Factor` | `{@../DiffuseColorFactor}` ✅ | Sets the diffuse color for the material. |
| `Diffuse Color Texture` | `{@../DiffuseColorTexture}` ✅ | Sets the texture that contains the diffuse color for the material. Use the Diffuse Color Factor property to filter the value from this texture. |
| `Emissive Color` | `{@../EmissiveColor}` ✅ | Sets the color of the light that is emitted from the material surface. |
| `Emissive Factor` | `{@../EmissiveFactor}` ✅ | Sets the color of the light that is emitted from the material. Use the Intensity (I) property field to adjust the brightness of the light. This color affects th… |
| `Emissive Texture` | `{@../EmissiveTexture}` ✅ | Sets the texture that contains the light emitted from the material. Use the Emissive Factor property to scale the value from this texture. |
| `Environment Ambient Factor` | `{@../EnvironmentAmbientFactor}` ✅ | Sets the strength of the cubemap texture to use for ambient environment light. Use the Environment Ambient Texture property to set the cubemap texture. The ambi… |
| `Environment Ambient Texture` | `{@../EnvironmentAmbientTexture}` ✅ | Sets the cubemap to use for the ambient environment light for the material. This cubemap affects the diffuse lighting during image based lighting. Use the Envir… |
| `Environment Reflection Factor` | `{@../EnvironmentReflectionFactor}` ✅ | Sets the strength of the cubemap texture to use for specular environment light. Use the Environment Reflection Texture property to set the cubemap texture. The … |
| `Environment Reflection Texture` | `{@../EnvironmentReflectionTexture}` ✅ | Sets the cubemap to use for the specular environment light for the material. This cubemap affects reflective lighting during image based lighting. Use the Envir… |
| `Exposure` | `{@../Exposure}` ✅ | Sets the exposure compensation for the material. The exposure compensation emulates camera exposure by controlling the total amount of light rendered. Use a neg… |
| `Global Ambient Color` | `{@../GlobalAmbientColor}` ✅ | Sets the color that is multiplied automatically with the Ambient property of the materials in the scene. Use the Intensity (I) property field to adjust the expo… |
| `Glossiness Factor` | `{@../GlossinessFactor}` ✅ | Sets the glossiness of the material: 0 represents a rough, diffuse surface, and 1 represents a smooth, glossy surface. |
| `Glossiness Texture` | `{@../GlossinessTexture}` ✅ | Sets the texture that contains a glossiness map for the material. Kanzi reads the glossiness from the Alpha channel of this texture. Use the Glossiness Factor p… |
| `Glyph Texture` | `{@../GlyphTexture}` ✅ | （官方无描述） |
| `Mask Texture` | `{@../MaskTexture}` ✅ | Sets the texture that masks another texture or color. |
| `Mask Texture Offset` | `{@../MaskTextureOffset}` ✅ | Sets an offset for mask in materials. |
| `Mask Texture Tiling` | `{@../MaskTextureTiling}` ✅ | Determines the number of times a mask is presented in a material |
| `Metallic Factor` | `{@../MetallicFactor}` ✅ | Sets the metalness of the material: 0 represents a non-metallic or dielectric object, and 1 represents a metallic object. |
| `Metallic Texture` | `{@../MetallicTexture}` ✅ | Sets the texture that contains a metallic map for the material. Kanzi reads the metalness from the Blue channel of this texture. Use the Metallic Factor propert… |
| `Normal Scale` | `{@../NormalScale}` ✅ | Sets the normal scale for the material. Use the scale to set the intensity of the Normal Texture. |
| `Normal Texture` | `{@../NormalTexture}` ✅ | Sets the texture that contains a normal map for the material. Use the Normal Scale property to scale the texture value. |
| `Occlusion Strength` | `{@../OcclusionStrength}` ✅ | Sets the occlusion strength for the material. Use the strength to set the intensity of the Occlusion Texture. |
| `Occlusion Texture` | `{@../OcclusionTexture}` ✅ | Sets the texture that contains an occlusion map for the material. Use the Occlusion Strength property to scale the occlusion from the texture. |
| `Offset` | `{@../Offset}` ✅ | （官方无描述） |
| `Roughness Factor` | `{@../RoughnessFactor}` ✅ | Sets the roughness of the material: 0 represents a smooth, glossy surface, and 1 represents a rough, diffuse surface. |
| `Roughness Texture` | `{@../RoughnessTexture}` ✅ | Sets the texture that contains a roughness map for the material. Kanzi reads the roughness from the Green channel of the texture. Use the Roughness Factor prope… |
| `Smoothing` | `{@../Smoothing}` ✅ | （官方无描述） |
| `Specular Anti-Aliasing Strength` | `{@../SpecularAnti-AliasingStrength}` ✅ | Sets the strength of the specular anti-aliasing effect. Higher value results in blurrier specular highlights. For no specular anti-aliasing, set the value to 0.… |
| `Specular Anti-Aliasing Threshold` | `{@../SpecularAnti-AliasingThreshold}` ✅ | Sets the upper limit for the amount of specular anti-aliasing effect to apply. The default value is 0.18. |
| `Specular Color` | `{@../SpecularColor}` ✅ | Sets the color of the specular reflection. |
| `Specular Color Factor` | `{@../SpecularColorFactor}` ✅ | Sets the specular color for the material. |
| `Specular Color Texture` | `{@../SpecularColorTexture}` ✅ | Sets the texture that contains the specular color for the material. Use the Specular Color Factor property to filter the value from this texture. |
| `Specular Exponent` | `{@../SpecularExponent}` ✅ | Sets the size of the specular highlight. |
| `Texture` | `{@../Texture}` ✅ | Sets the texture of the material. |
| `Texture Offset` | `{@../TextureOffset}` ✅ | Sets an offset for texture in materials. |
| `Texture Tiling` | `{@../TextureTiling}` ✅ | Determines the number of times a texture is presented in a material. |
| `Texture2` | `{@../Texture2}` ✅ | （官方无描述） |
| `TextureCube` | `{@../TextureCube}` ✅ | （官方无描述） |
| `Tone Map Linear Scale` | `{@../ToneMapLinearScale}` ✅ | Sets the scale for the linear tonemap option for the material. When linear tonemapping is used, Kanzi divides all output color by the value of this property. |

## Nine Patch Image

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Bottom Image` | `{@../NinePatchImage.BottomImage}` ✅ | The image to use in middle of the bottom row. |
| `Bottom-Left Image` | `{@../NinePatchImage.BottomLeftImage}` ✅ | Image to use in the bottom-left corner. |
| `Bottom-Right Image` | `{@../NinePatchImage.BottomRightImage}` ✅ | The image to use in the bottom-right corner. |
| `Center Image` | `{@../NinePatchImage.CenterImage}` ✅ | The image to use in the center. |
| `Left Image` | `{@../NinePatchImage.LeftImage}` ✅ | The image to use in the center-left. |
| `Right Image` | `{@../NinePatchImage.RightImage}` ✅ | The image to use in the center-right. |
| `Top Image` | `{@../NinePatchImage.TopImage}` ✅ | The image to use in the middle of the top row. |
| `Top-Left Image` | `{@../NinePatchImage.TopLeftImage}` ✅ | The image to use in the top-left corner. |
| `Top-Right Image` | `{@../NinePatchImage.TopRightImage}` ✅ | The image to use in the top-right corner. |

## Node

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Clip Children` | `{@../Node.ClipChildren}` ✅ | Sets whether to clip the child nodes of this node. Kanzi clips the child nodes whose bounding box is completely outside of the bounding box of their parent node… |
| `Content Stretch` | `{@../Node.ContentStretch}` ✅ | Sets how the content that belongs to this node is stretched (as opposed to manipulating the actual node size). |
| `Hover` | `{@../Node.Hover}` ✅ | Indicates whether a node is the foremost hit testable node under the cursor. |
| `Node.Path` | `{@../Node.Path}` ✅ | Full path to the node. |
| `Opacity` | `{@../Node.Opacity}` ✅ | Opacity of the node. |
| `Visible` | `{@../Node.Visible}` ✅ | When disabled, Kanzi does not render the node. |
| `Visible Amount in Parent` | `{@../Node.VisibleAmountInParent}` ✅ | Sets the amount the node is inside its parent. Use the value of this property in shaders to implement fades. Calculated by the parent node. |

## Node 2D

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Aspect Ratio` | `{@../Node2D.AspectRatio}` ✅ | Determines the proportion of width and height. You cannot set both the Aspect Ratio and both, Width and Height. |
| `Force Composition` | `{@../Node2D.ForceComposition}` ✅ | Force rendering to composing target even if not otherwise necessary. |
| `Foreground Hint` | `{@../Node2D.ForegroundHint}` ✅ | Give a hint of the type of the foreground of 2D nodes: * None renders the background brush after rendering the node. * Translucent renders the background brush … |
| `Snap to Pixel` | `{@../Node2D.SnapToPixel}` ✅ | Snap the translation of the node and its size into pixel boundary. |

## Node Effect 2D

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Enabled` | `{@../Node.Enabled}` ✅ | Whether to apply this effect. |

## Outline Effect 2D

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Content Gradient` | `{@../OutlineEffect2D.ContentGradient}` ✅ | Sets the gradient along which the content fades out: * Start sets the minimum intensity at which the content starts to fade out. * Softness sets the difference … |
| `Content Mask` | `{@../OutlineEffect2D.ContentMask}` ✅ | Sets the color that masks color components relevant to the outline calculation. The comparison value is the result of a dot product between the mask and the con… |
| `Content Threshold` | `{@../OutlineEffect2D.ContentThreshold}` ✅ | Sets the threshold at which the value Kanzi calculates using the content mask is considered valid. When the value calculated from masking the content exceeds th… |
| `Invert Content Mask` | `{@../OutlineEffect2D.InvertContentMask}` ✅ | Whether to invert the value that Kanzi calculates using content masking. |
| `Outline Color` | `{@../OutlineEffect2D.OutlineColor}` ✅ | Sets the color of the outline. |
| `Outline Inner Softness` | `{@../OutlineEffect2D.OutlineInnerSoftness}` ✅ | Sets the softness of the outline relative to its width inside the content area. For a sharp outline, set to 0. For a fade-in that takes the complete outline wid… |
| `Outline Inner Width` | `{@../OutlineEffect2D.OutlineInnerWidth}` ✅ | Sets the width of the outline in pixels inside the content area. By default, this property uses the value of the Outline Width property. |
| `Outline Method` | `{@../OutlineEffect2D.OutlineMethod}` ✅ | Sets the method for outline calculation: * Box uses box search which potentially consumes less memory but is slower. * Two-pass uses two-pass search which poten… |
| `Outline Softness` | `{@../OutlineEffect2D.OutlineSoftness}` ✅ | Sets the softness of the outline. For a sharp outline, set to 0. For a fade-in that takes the complete outline width to reach maximum value, set to 1. The defau… |
| `Outline Texture` | `{@../OutlineEffect2D.OutlineTexture}` ✅ | Sets the texture to apply to the outline. Kanzi applies to the outline only the top row of pixels from this texture. Set Outline Color to the color with which y… |
| `Outline Texture Offset` | `{@../OutlineEffect2D.OutlineTextureOffset}` ✅ | Sets the relative starting offset for sampling the outline texture. The default value is 0.0. |
| `Outline Texture Tiling` | `{@../OutlineEffect2D.OutlineTextureTiling}` ✅ | Sets the number of times the texture wraps around within the outline area. To repeat a texture, set its Wrap Mode to Repeat. The default value is 1.0 |
| `Outline Width` | `{@../OutlineEffect2D.OutlineWidth}` ✅ | Sets the width of the outline in pixels outside the content area. The default value is 4 pixels. |

## Page

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Transition Phase` | `{@../Page.TransitionPhase}` ✅ | The phase of the transition. For example, use for pixel-based effects. |

## Parallel Activity Host

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Bring Activated Activity To Front` | `{@../ParallelActivityHost.BringActivatedActivityToFront}` ✅ | Sets whether to show the activated Activity in front within its Parallel Activity Host. This property affects the z-order of the activated Activity within the s… |

## Range

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Is Value Changing` | `{@../Range.IsValueChanging}` ✅ | Whether the value is currently changing. |
| `Maximum Value` | `{@../Range.Maximum}` ✅ | The maximum value that the range allows. |
| `Minimum Value` | `{@../Range.Minimum}` ✅ | The minimum value that the range allows. |
| `Normalized Value` | `{@../Range.NormalizedValue}` ✅ | The current value normalized to range [0, 1]. |
| `Step Value` | `{@../Range.Step}` ✅ | The minimum amount that the value of the range can change at a time. |
| `Value` | `{@../Range.Value}` ✅ | The current value. To update this property with a binding, use a to-source or two-way binding. |

## Render Target

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Cache Valid` | `{@../Node.CacheValid}` ✅ | Indicates whether the node is cached. To disable the cache for one frame, disable this property. |
| `Caching Mode` | `{@../Node.CachingMode}` ✅ | Sets the caching mode of this node: * Disabled sets Kanzi to render the node and its descendants normally, without caching. This is the default. * Enabled sets … |
| `Disable Render Target Clear Color` | `{@../Node.DisableRenderTargetClearColor}` ✅ | Do not clear render target buffers before rendering into it even if necessary. |
| `Multisample Level` | `{@../RenderTarget.MultisampleLevel}` ✅ | Sets the amount of multisample anti-aliasing to apply to the temporary composition targets to which Kanzi renders this node. |
| `Off-Screen Rendering` | `{@../Node.OffScreenRendering}` ✅ | When set and the node has an explicitly set render target, do not render the resulting framebuffer to screen. |
| `Pixel Format` | `{@../RenderTarget.PixelFormat}` ✅ | The pixel format of the node if rendering to a texture. |
| `Render Self` | `{@../Node.RenderSelf}` ✅ | Whether the node renders itself. Does not affect the rendering of child nodes. |
| `Render Target` | `{@../Node.RenderTarget}` ✅ | Forces the node to be rendered into a given render target texture. When set to “No Target”, regular conditions whether node is rendered to a texture, such as op… |
| `Render Target Minimum Height` | `{@../Node.RenderTargetMinimumHeight}` ✅ | Sets the minimum height of implicitly generated render targets. |
| `Render Target Minimum Width` | `{@../Node.RenderTargetMinimumWidth}` ✅ | Sets the minimum width of implicitly generated render targets. |
| `Render Target Reallocation Limit` | `{@../Node.RenderTargetReallocationLimit}` ✅ | The change in size that triggers reallocation of a render target. |

## Resources

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Custom Asset Thumbnail` | `{@../Resources.CustomAssetThumbnail}` ✅ | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `Disable KZB Export` | `{@../Resources.DisableKZBExport}` ✅ | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Export in Asset Package` | `{@../Resources.ExportInAssetPackage}` ✅ | When enabled, this item is exported into asset package if this project is saved as one. |

## State Manager

_（该分组为节点/资源类型，无直接属性，见对应节点章节）_

## Style

_（该分组为节点/资源类型，无直接属性，见对应节点章节）_

## Shadow Effect 2D

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Override Shadow Offset` | `{@../ShadowEffect2D.OverrideShadowOffset}` ✅ | Sets the offset of the shadow from the object along the x and y axes in pixels. When you set this property, the Shadow Angle and Shadow Distance properties have… |
| `Shadow Angle` | `{@../ShadowEffect2D.ShadowAngle}` ✅ | Sets the direction of the shadow as an angle relative to the positive x axis. The default is 45 degrees. When you set the Override Shadow Offset property, this … |
| `Shadow Blur Radius` | `{@../ShadowEffect2D.ShadowBlurRadius}` ✅ | Sets the softness of the shadow by defining the distance in pixels the shadow blur extends outward from an edge. For a shadow with sharp edges, set to 0. The de… |
| `Shadow Color` | `{@../ShadowEffect2D.ShadowColor}` ✅ | Sets the color and alpha of the shadow. |
| `Shadow Distance` | `{@../ShadowEffect2D.ShadowDistance}` ✅ | Sets how far to move the shadow from the object in the direction set by the Shadow Angle property. The default is 10 pixels. When you set the Override Shadow Of… |
| `Shadow Only` | `{@../ShadowEffect2D.ShadowOnly}` ✅ | Whether to render only the shadow without the node contents. |
| `Shadow Quality` | `{@../ShadowEffect2D.ShadowQuality}` ✅ | Sets the visual quality of the shadow. Lower quality uses less computing and memory resources. |
| `Shadow Type` | `{@../ShadowEffect2D.ShadowType}` ✅ | Sets the type of the shadow: * Drop Shadow appears behind or below objects. * Inner Shadow appears inside objects. |

## Slider

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Maximum Distance From Curve` | `{@../Slider.MaximumDistanceFromCurve}` ✅ | The distance from the curve where hit testing succeeds. |

## Stack Layout

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Direction` | `{@../StackLayout2D.Direction}` ✅ | Defines the axis along which the stack layout arranges its items. |
| `Reversed` | `{@../StackLayout2D.Reversed}` ✅ | Defines whether the stack layout arranges its items in reverse order. |

## Text Block

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Word Wrap` | `{@../TextBlock2D.WordWrap}` ✅ | Sets whether to break long lines into multiple lines to make the text fit within the boundaries of the Text Block node. |

## Text Block 3D

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Baseline` | `{@../TextBlock3D.Baseline}` ✅ | Font baseline in 3D space units. |
| `Two Pass Rendering` | `{@../TextBlock3D.TwoPassRendering}` ✅ | Defines whether the Text Block 3D is rendered in two passes. Disabling the two pass rendering improves performance, but can cause invalid rendering results when… |

## Text Concept

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Horizontal Fit` | `{@../TextConcept.HorizontalFit}` ✅ | Whether to horizontally scale the glyphs to make them fit into the Layout Width of the Text Block. To adjust the scale, use the Horizontal Fit Scale Limits prop… |
| `Horizontal Fit Scale Limits` | `{@../TextConcept.HorizontalFitScaleLimits}` ✅ | When the Horizontal Fit property is enabled, sets the minimum and maximum scale for glyphs when the width of text in a Text Block does not match the Layout Widt… |
| `Horizontal Padding` | `{@../TextConcept.HorizontalPadding}` ✅ | Sets the padding spaces between the content and the left and right boundaries of the Text node. |
| `Overflow` | `{@../TextConcept.Overflow}` ✅ | Sets the characters that represent the truncated text when the text does not fit in this node. The default value is ‘…’. By default, Kanzi truncates the text at… |
| `Remove Side Bearings` | `{@../TextConcept.RemoveSideBearings}` ✅ | Whether to position the leftmost characters of left-aligned text and rightmost characters of right-aligned text exactly within the boundary of the text node. |
| `Text` | `{@../TextBlock2D.Text}` ✅ | Sets the text content that the text node renders. To create a line break press Shift+Enter. |
| `Text Horizontal Alignment` | `{@../TextConcept.TextHorizontalAlignment}` ✅ | Sets the horizontal alignment of the text. |
| `Text Vertical Alignment` | `{@../TextConcept.TextVerticalAlignment}` ✅ | Sets the vertical alignment of the text. |
| `Truncation` | `{@../TextConcept.Truncation}` ✅ | Sets how Kanzi truncates text when either Truncation or Overflow property is set and the text does not fit in this node: * None disables text truncation. * At c… |
| `Truncation Direction` | `{@../TextConcept.TruncationDirection}` ✅ | Sets which part Kanzi truncates when either the Truncation or Overflow property is set and the text does not fit in this node: * Trailing truncates single- and … |
| `Vertical Padding` | `{@../TextConcept.VerticalPadding}` ✅ | Sets the padding spaces between the content and the top and bottom boundaries of the Text node. |

## Toggle Button

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Index In Group` | `{@../ToggleButton.IndexInGroup}` ✅ | Sets the index of the Toggle Button in the Toggle Button Group to which that Toggle Button is registered. If a Toggle Button does not have a local value for thi… |
| `Toggle State` | `{@../ToggleButton.ToggleState}` ✅ | Sets the toggle state of a Toggle Button. To update this property with a binding, use a to-source or two-way binding. |
| `Toggle State Count` | `{@../ToggleButton.ToggleStateCount}` ✅ | Sets the number of toggle states of a Toggle Button. |

## Trajectory Layout

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Calculated Offset` | `{@../TrajectoryLayout2D.CalculatedOffset}` ✅ | Reports the current relative offset of an item in the Grid List Box in proportional range [0, 1]. |
| `Stretch` | `{@../TrajectoryLayout2D.Stretch}` ✅ | Whether to scale this Trajectory Layout to match the layout size. |
| `Trajectory Override Offset` | `{@../TrajectoryLayout2D.TrajectoryOverrideOffset}` ✅ | Sets the offset of an item in a Trajectory Layout. When you do not set this property, the Trajectory Layout sets the offset. |

## Transform 2D

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Layout Transformation` | `{@../Node2D.LayoutTransformation}` ✅ | The 2D transformation to be applied before layouting. |
| `Perspective Transformation` | `{@../Node2D.PerspectiveTransformation}` ✅ | The 3D transformation to be applied after layouting. |
| `Perspective Transformation FOV` | `{@../Node2D.PerspectiveTransformationFOV}` ✅ | The 3D transformation field of view (degrees) to be applied after layouting. |
| `Perspective Transformation Mode` | `{@../Node2D.PerspectiveTransformationMode}` ✅ | Defines the mode of operation for the coordinate system and field of view. |
| `Perspective Transformation Origin` | `{@../Node2D.PerspectiveTransformationOrigin}` ✅ | The 3D transformation origin to be used for perspective transformation on this or child nodes. |
| `Perspective Transformation Pivot` | `{@../Node2D.PerspectiveTransformationPivot}` ✅ | The 3D pivot point in relative coordinates. |
| `Render Transformation` | `{@../Node.RenderTransformation}` ✅ | The 2D transformation to be applied after layouting. |
| `Render Transformation Origin` | `{@../Node.RenderTransformationOrigin}` ✅ | Sets the render transform origin in relative coordinates. |

## Value-Controlled Exclusive Activity Host

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Controller Property` | `{@../ValueControlledExclusiveActivityHost.ControllerProperty}` ✅ | Sets the property type that the Exclusive Activity Host node uses to switch between its child Activity nodes. |
| `Data Source Controller Property Path` | `{@../ValueControlledExclusiveActivityHost.DataSourceControllerPropertyPath}` ✅ | Sets the path in the Data Source object of an Exclusive Activity Host node to a Data Object item that the Exclusive Activity Host node uses as the Controller Pr… |

## Viewport 2D

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Camera` | `{@../Viewport2D.Camera}` ✅ | Sets which camera to use in scenes rendered by the selected Viewport 2D. If not set, Kanzi uses the camera in the scene. |
| `Hit Test Camera` | `{@../Viewport2D.HitTestCamera}` ✅ | Sets which hit test camera to use in scenes rendered by the selected Viewport 2D. If not set, Kanzi uses the camera in the scene. |
| `Render Pass Prefab` | `{@../Viewport2D.RenderPassPrefab}` ✅ | Sets which render pass prefab will be used to instantiate the render pass tree. |

## 字体 (Font)

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Character Spacing` | `{@../TextBlock2D.CharacterSpacing}` ✅ | Sets the character spacing in pixels. |
| `Fixed Character Width` | `{@../TextConcept.FixedCharacterWidth}` ✅ | When set, overrides the font advance widths to make each character take a fixed amount of space specified in pixels. |
| `Font Color` | `{@../TextConcept.FontColor}` ✅ | Sets the color of the text in a 3D text node. |
| `Font Family` | `{@../TextBlock2D.FontFamily}` ✅ | The font family used to render the text. |
| `Font Hinting Preference` | `{@../TextConcept.FontHintingPreference}` ✅ | Sets the hinting preference of the font. * No hinting: Render text without hinting the outlines of glyphs. * Native hinting: Prefer native hinter of the font ov… |
| `Font Material` | `{@../TextConcept.FontMaterial}` ✅ | Sets the material whose shader is used to render the text. The shader must use the ContentTexture uniform which is automatically filled with glyph data. |
| `Font Size` | `{@../TextBlock2D.FontSize}` ✅ | Sets the size of the font in pixels. |
| `Font Style` | `{@../TextConcept.FontStyle}` ✅ | Sets the style of the font. |
| `Font Weight` | `{@../TextConcept.FontWeight}` ✅ | Sets the weight of the font. |
| `Fractional Character Width` | `{@../TextConcept.FractionalCharacterWidth}` ✅ | Sets whether Kanzi uses fractional or rounded character widths to lay out text. In most cases fractional widths provide the best result. However, with small fon… |
| `Line Spacing` | `{@../TextConcept.LineSpacing}` ✅ | Sets the line spacing in multiples of the normal line height of the selected font. |
| `Snap Character To Pixel` | `{@../TextConcept.SnapCharacterToPixel}` ✅ | Sets whether Kanzi positions characters in 2D rendering to the nearest pixel: * When enabled, text sharpness improves, but some characters can shift a fraction … |

## 焦点 (Focus)

| UI 属性名 | 绑定写法 | 说明 |
|-----------|---------|------|
| `Focus On Press` | `{@../Node.FocusOnPress}` ✅ | Sets where to set the focus when the user presses the node that has this property: * None (0) keeps the focus where it was. This is the default. * Node (1) sets… |
| `Focus Order` | `{@../Node.FocusOrder}` ✅ | Sets the focus chain order of the node within the focus scope. |
| `Focus State` | `{@../Node.FocusState}` ✅ | Reports the focus state of a node: * No focus (0) indicates that the node is not focused. For a focus scope node indicates that none of the nodes in the scope h… |
| `Focusable` | `{@../Node.Focusable}` ✅ | Indicates whether the node can receive focus. |
| `Focused` | `{@../Node.Focused}` ✅ | Indicates whether the node has the key focus. |

---

## 绑定示例（组合用法）

```
# 按父节点实际宽度动态设置自己宽度
clamp(50, 120, {@../../../Node.ActualWidth} / 5)
# 取渲染变换的 X 位移
{@../Node.RenderTransformation}.translationX
# 条件 + 注释 + 变量
#A = {#Info/sys.ignState}
MOD(CLAMP(0,1,ABS(A-(1)))+1,2)
```
