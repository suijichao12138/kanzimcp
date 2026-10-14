---
name: kanzi-properties-layout
description: Kanzi 布局节点属性参考（Grid/Stack/Dock/Flow/Content/Trajectory Layout 2D+3D），官方文档抓取
---

# Kanzi 布局节点属性大全

## 使用说明

本 skill 是 Kanzi 4.1.0 官方属性参考（来源：`docs.kanzi.com → Reference → Node and resource reference`，2026-10-14 批量抓取）。

- **特有属性**：该节点直接声明的属性（官方「X properties」表）。

- **继承属性**：从基类继承的公共属性，见文末表。

- 查某节点完整属性 = 该节点特有属性 + 继承属性表。

---

## Grid Layout 2D（`grid-layout-2d-reference`）

**特有属性 6 个**；继承属性约 303 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Columns` | Defines the number of columns in a grid layout and how the grid layout distributes the content in columns. |
| `Rows` | Defines the number of rows in a grid layout and how the grid layout distributes the content in rows. |
| `Layout Width` | The width of the node when used in a layout. Overrides the default bounds of the item. |
| `Layout Height` | The height of the node when used in a layout. Overrides the default bounds of the item. |

---

## Stack Layout 2D（`stack-layout-2d-reference`）

**特有属性 4 个**；继承属性约 302 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Direction` | Defines the axis along which the stack layout arranges its items. |
| `Reversed` | Defines whether the stack layout arranges its items in reverse order. |

---

## Dock Layout 2D（`dock-layout-2d-reference`）

**特有属性 2 个**；继承属性约 305 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |

---

## Flow Layout 2D（`flow-layout-2d-reference`）

**特有属性 2 个**；继承属性约 306 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |

---

## Content Layout 2D（`content-layout-2d-reference`）

**特有属性 4 个**；继承属性约 388 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Component Type` | The component type of this component node |

---

## Trajectory Layout 2D（`trajectory-layout-2d-reference`）

**特有属性 3 个**；继承属性约 309 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Trajectory` | Sets the Trajectory along which this Trajectory Layout node arranges its items. |

---

## Grid Layout 3D（`grid-layout-3d-reference`）

**特有属性 9 个**；继承属性约 326 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Imported from` | The source, the project reference or the 3D asset source file from where the item was imported into this project |
| `Import Source ID` |  |
| `Original Name` | The name of the item in the import source |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Component Type` | The component type of this component node |
| `Columns` | Defines the number of columns in a grid layout and how the grid layout distributes the content in columns. |
| `Rows` | Defines the number of rows in a grid layout and how the grid layout distributes the content in rows. |

---

## Stack Layout 3D（`stack-layout-3d-reference`）

**特有属性 9 个**；继承属性约 328 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Imported from` | The source, the project reference or the 3D asset source file from where the item was imported into this project |
| `Import Source ID` |  |
| `Original Name` | The name of the item in the import source |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Component Type` | The component type of this component node |
| `Direction` | Defines the axis along which the stack layout arranges its items. |
| `Reversed` | Defines whether the stack layout arranges its items in reverse order. |

---

## Dock Layout 3D（`dock-layout-3d-reference`）

**特有属性 7 个**；继承属性约 331 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Imported from` | The source, the project reference or the 3D asset source file from where the item was imported into this project |
| `Import Source ID` |  |
| `Original Name` | The name of the item in the import source |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Component Type` | The component type of this component node |

---

## Flow Layout 3D（`flow-layout-3d-reference`）

**特有属性 7 个**；继承属性约 330 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Imported from` | The source, the project reference or the 3D asset source file from where the item was imported into this project |
| `Import Source ID` |  |
| `Original Name` | The name of the item in the import source |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Component Type` | The component type of this component node |

---

## Content Layout 3D（`content-layout-3d-reference`）

**特有属性 7 个**；继承属性约 333 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Imported from` | The source, the project reference or the 3D asset source file from where the item was imported into this project |
| `Import Source ID` |  |
| `Original Name` | The name of the item in the import source |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Component Type` | The component type of this component node |

---

## Trajectory Layout 3D（`trajectory-layout-3d-reference`）

**特有属性 9 个**；继承属性约 326 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Imported from` | The source, the project reference or the 3D asset source file from where the item was imported into this project |
| `Import Source ID` |  |
| `Original Name` | The name of the item in the import source |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Component Type` | The component type of this component node |
| `Trajectory` | Sets the Trajectory along which this Trajectory Layout node arranges its items. |
| `Start Offset` | Sets the offset of the starting position of the items on the trajectory in the range [0, 1], where 0 is the beginning and 1 is the end of the trajectory. |

---

## 继承属性表（364 个，本类节点从基类继承的公共属性）

| 属性 | 说明 |
|------|------|
| `A` | Tonemapping parameter A. |
| `Active Activity Index` | The index of the active Activity in the Data-Driven Exclusive Activity Host. After instantiating all Activity from a Data Source, this property refers to the only currently active Activity in this Dat… |
| `Activity Source` | The data object that provides the data for this Activity node. |
| `Activity Status` | Sets the possible states of the Activity when its Activity Host activates or deactivates that Activity. |
| `Activity Template` | If set, the Data-Driven Exclusive Activity Host uses this prefab for Activity nodes that it creates. |
| `Actual Layout Height` | The calculated height of the node when used in a layout. |
| `Actual Layout Width` | The calculated width of the node when used in a layout. |
| `Alpha Cutoff` | Sets the cutoff threshold for alpha cutting. If the alpha value is less than the value of this property, Kanzi discards the fragment. The default value is 0.5. |
| `Ambient Color` | Sets the color of the material when lights are not present. Use the Intensity (I) property field to adjust the exposure of the color. |
| `Ambient Occlusion Blur Direction` | Blur direction of the ambient occlusion bilateral blur. |
| `Ambient Occlusion Focal Length` | HBAO input property for focal length. |
| `Ambient Occlusion LinMAD` | HBAO input property for LinMAD uniform. |
| `Ambient Occlusion Radius` | Screen-space ambient occlusion (SSAO) effect radius. Used to calculate the SSAO texture. |
| `Ambient Occlusion Strength` | Screen-space ambient occlusion (SSAO) strength. Used to calculate the SSAO texture. |
| `Ambient Occlusion UV to View A` | HBAO input property for UVToViewA uniform. |
| `Ambient Occlusion UV to View B` | HBAO input property for UVToViewB uniform. |
| `Amount` | Sets the chromatic aberration amount. |
| `Aspect Ratio` | Determines the proportion of width and height. You cannot set both the Aspect Ratio and both, Width and Height. |
| `Auto Press Interval` | Sets the time in milliseconds after which a button that the user keeps pressed down sends the Button: Click message. While the user holds the button down, the button keeps sending the Button: Click me… |
| `B` | Tonemapping parameter B. |
| `Background Brush` | The background brush to paint the background of 2D nodes. |
| `Base Color Factor` | Sets the base color for the material. |
| `Base Color Texture` | Sets the texture that contains the base color for the material. Use the Base Color Factor property to filter the value from this texture. |
| `Baseline` | Font baseline in 3D space units. |
| `Blend Intensity` | Controls the intensity of materials that are blended on top of an existing color. Attached property enables overriding of the blend intensity of the used materials at render pass or object node level. |
| `Blend Mode` | Sets how to combine the color and alpha values of pixels in one layer or image with those in the underlying layer or image. |
| `Bloom Intensity` | Bloom intensity for the material. |
| `Bloom Intensity Texture` | Sets the bloom intensity texture. |
| `Bloom Radius` | Bloom radius for the material. |
| `Blur Direction` | Sets the direction for the blur. |
| `Blur Quality` | Sets the visual quality of the blur. Lower quality uses less computing and memory resources. |
| `Blur Radius` | Blur radius for the material. |
| `Bottom Image` | The image to use in middle of the bottom row. |
| `Bottom-Left Image` | Image to use in the bottom-left corner. |
| `Bottom-Right Image` | The image to use in the bottom-right corner. |
| `BRDF Lookup Table` | Gets the Bidirectional Reflectance Distribution Function (BRDF) lookup table for the material. The BRDF table is a texture that contains precomputed information about how light reflects off a material… |
| `Bring Activated Activity To Front` | Sets whether to show the activated Activity in front within its Parallel Activity Host. This property affects the z-order of the activated Activity within the same Activity priority layer: * When enab… |
| `Brush Color` | Color for brush. Set alpha to 0 to disable brush. |
| `Brush Horizontal Tiling` | Horizontal Tiling for the brush. Affects the scale of texture coordinates. |
| `Brush Modulate Color` | Modulation color for brush. Effects brush rendering that needs color modulation. |
| `Brush Texture` | Texture for brush. |
| `Brush Vertical Tiling` | Vertical Tiling for the brush. Affects the scale of texture coordinates. |
| `C` | Tonemapping parameter C. |
| `Cache Valid` | Indicates whether the node is cached. To disable the cache for one frame, disable this property. |
| `Caching Mode` | Sets the caching mode of this node: * Disabled sets Kanzi to render the node and its descendants normally, without caching. This is the default. * Enabled sets Kanzi to cache the node and its descenda… |
| `Calculated Offset` | Reports the current relative offset of an item in the Grid List Box in proportional range [0, 1]. |
| `Camera` | Sets which camera to use in scenes rendered by the selected Viewport 2D. If not set, Kanzi uses the camera in the scene. |
| `Center Image` | The image to use in the center. |
| `Character Spacing` | Sets the character spacing in pixels. |
| `Clear Coat Normal Scale` | Sets the clear coat normal scale for the material. Use the scale to set the intensity of the Clear Coat Normal Texture. |
| `Clear Coat Normal Texture` | Sets the texture that contains a clear coat normal map for the material. Use the Clear Coat Normal Scale property to scale the texture value. |
| `Clear Coat Roughness Factor` | Sets the roughness of the outer clear coat layer for the material: 0 represents a smooth, glossy surface, and 1 represents a rough, diffuse surface. |
| `Clear Coat Roughness Texture` | Sets the texture that contains a clear coat roughness map for the material. Kanzi reads the roughness from the Green channel of the texture. Use the Clear Coat Roughness Factor property to scale the r… |
| `Clear Coat Strength Factor` | Sets the clear coat strength for the material: 0 represents a material with no clear coat, and 1 represents a full strength clear coat. |
| `Clear Coat Strength Texture` | Sets the texture that contains a clear coat strength map for the material. Kanzi reads the strength from the Red channel of the texture. Use the Clear Coat Strength Factor property to scale the streng… |
| `Clip Children` | Sets whether to clip the child nodes of this node. Kanzi clips the child nodes whose bounding box is completely outside of the bounding box of their parent node. Use this property with layout nodes. T… |
| `Code Behind Source` | Sets the metaclass name of the code behind class for this node. |
| `Color Font Material` | Sets the material whose shader is used to render the text containing colored glyphs. The shader must use the ContentTexture uniform which is automatically filled with glyph data. |
| `Column` | The column into which grid layout places the item. |
| `Column Span` | Defines the number of columns an item in a grid layout occupies. |
| `Command` | The command executed by a UI control |
| `Composition Brush` | The brush to use to compose 2D nodes to screen. |
| `Content Gradient` | Sets the gradient along which the content fades out: * Start sets the minimum intensity at which the content starts to fade out. * Softness sets the difference in intensity it takes for the content to… |
| `Content Mask` | Sets the color that masks color components relevant to the outline calculation. The comparison value is the result of a dot product between the mask and the content RGBA color value. By default Kanzi … |
| `Content Stretch` | Sets how the content that belongs to this node is stretched (as opposed to manipulating the actual node size). |
| `Content Threshold` | Sets the threshold at which the value Kanzi calculates using the content mask is considered valid. When the value calculated from masking the content exceeds this value, that pixel is part of the outl… |
| `Controller Property` | Sets the property type that the Exclusive Activity Host node uses to switch between its child Activity nodes. |
| `Cubemap Texture` | Sets the cubemap texture you want the Blit render pass to blit. |
| `Custom Asset Thumbnail` | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `Cyclic Focus Navigation` | Sets whether the focus chain navigation within the focus scope is cyclic. When you enable this property: * When the user navigates in the forward direction and the focus reaches the last focusable UI … |
| `D` | Tonemapping parameter D. |
| `Data Context` | Source of data for this node and its descendants |
| `Data Source Controller Property Path` | Sets the path in the Data Source object of an Exclusive Activity Host node to a Data Object item that the Exclusive Activity Host node uses as the Controller Property. |
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Detail Base Color Factor` | Sets the detail base color for the material. The detail base color is alpha blended with the standard base color. |
| `Detail Base Color Texture` | Sets the detail texture that contains the base color for the material. Use the Detail Base Color Factor property to filter the value from this texture. The detail base color is alpha blended with the … |
| `Detail Clear Coat Normal Scale` | Sets the detail clear coat normal scale for the material. Use the scale to set the intensity of the Detail Clear Coat Normal Texture. |
| `Detail Clear Coat Normal Texture` | Sets the detail texture that contains a clear coat normal map for the material. Use the Detail Clear Coat Normal Scale property to scale the texture value. |
| `Detail Clear Coat Roughness Texture` | Sets the detail texture that contains a clear coat roughness map for the material. Use the Clear Coat Roughness Factor and Clear Coat Roughness Texture properties to scale the roughness from this text… |
| `Detail Clear Coat Strength Texture` | Sets the detail texture that contains a clear coat strength map for the material. Kanzi reads the strength from the Red channel of the texture. Use the Clear Coat Strength Factor and Clear Coat Streng… |
| `Detail Diffuse Color Factor` | Sets the detail diffuse color for the material. Kanzi alpha blends the detail diffuse color with the standard diffuse color. |
| `Detail Diffuse Color Texture` | Sets the detail texture that contains the diffuse color for the material. Use the Detail Diffuse Color Factor property to filter the value from this texture. Kanzi alpha blends the detail diffuse colo… |
| `Detail Emissive Factor` | Sets the color of the light that is emitted from a detail texture for the material. Use the Intensity (I) property field to adjust the brightness of the light. This color affects the local material re… |
| `Detail Emissive Texture` | Sets the detail texture that contains the light emitted from the material. Use the Detail Emissive Factor property to scale the value from this texture. Use the Detail Texture Tiling and Detail Textur… |
| `Detail Glossiness Texture` | Sets the detail texture that contains a glossiness map for the material. Kanzi reads the glossiness from the Alpha channel of this texture. Use the Glossiness Factor and Glossiness Texture properties … |
| `Detail Metallic Texture` | Sets the detail texture that contains a metallic map for the material. Kanzi reads the metalness from the Blue channel of this texture. Use the Metallic Factor and Metallic Texture properties to scale… |
| `Detail Normal Scale` | Sets the detail normal scale for the material. Use the scale to set the intensity of the Detail Normal Texture. |
| `Detail Normal Texture` | Sets the detail texture that contains a normal map for the material. Use the Detail Normal Scale property to scale the texture value. |
| `Detail Occlusion Strength` | Sets the detail occlusion strength for the material. Use the strength to set the intensity of the Detail Occlusion Texture. |
| `Detail Occlusion Texture` | Sets the detail texture that contains an occlusion map for the material. Kanzi reads the occlusion from the Red channel of this texture. Use the Detail Occlusion Strength property to scale the occlusi… |
| `Detail Roughness Texture` | Sets the detail texture that contains a roughness map for the material. Kanzi reads the roughness from the Green channel of the texture. Use the Roughness Factor and Roughness Texture properties to sc… |
| `Detail Specular Color Factor` | Sets the detail specular color for the material. Kanzi alpha blends the detail specular color with the standard specular color. |
| `Detail Specular Color Texture` | Sets the detail texture that contains the specular color for the material. Use the Detail Specular Color Factor property to filter the value from this texture. Kanzi alpha blends the detail specular c… |
| `Detail Texture Offset` | Sets the detail texture offset for the material. Kanzi adds this value to the UVs to produce a second set of detail UVs to use for all detail texture properties. |
| `Detail Texture Tiling` | Sets the detail texture tiling factor for the material. Kanzi multiplies this value by the UVs to produce a second set of detail UVs to use for all detail texture properties. |
| `Diffuse Color` | Sets the color of the material when it is lit by a light. |
| `Diffuse Color Factor` | Sets the diffuse color for the material. |
| `Diffuse Color Texture` | Sets the texture that contains the diffuse color for the material. Use the Diffuse Color Factor property to filter the value from this texture. |
| `Directional Light View Projection` | The premultiplied projection view matrix of a directional light. |
| `Directional Shadow Map` | Depth map used to calculate directional shadows. |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Disable Render Target Clear Color` | Do not clear render target buffers before rendering into it even if necessary. |
| `Dithering Amount` | Sets the chromatic aberration dithering amount. |
| `Down On Hover` | Whether holding a finger on the device screen and moving it over the button transitions the button to the down state. |
| `E` | Tonemapping parameter E. |
| `Effect` | Reports the runtime effect instance that this node uses. Kanzi sets the value of this property internally when the value of the Effect Prefab property in this node changes. |
| `Effect Prefab` | The 2D Effect to use for this node. |
| `Effectively Enabled` | Indicates whether this node and its ancestor nodes are enabled. Use this property in state managers and bindings to observe whether a node is effectively enabled. To enable or disable a node, use the … |
| `Emissive Color` | Sets the color of the light that is emitted from the material surface. |
| `Emissive Factor` | Sets the color of the light that is emitted from the material. Use the Intensity (I) property field to adjust the brightness of the light. This color affects the local material rendering, but the ligh… |
| `Emissive Texture` | Sets the texture that contains the light emitted from the material. Use the Emissive Factor property to scale the value from this texture. |
| `Enabled` | Whether to apply this effect. |
| `Environment Ambient Factor` | Sets the strength of the cubemap texture to use for ambient environment light. Use the Environment Ambient Texture property to set the cubemap texture. The ambient environment light affects diffuse li… |
| `Environment Ambient Texture` | Sets the cubemap to use for the ambient environment light for the material. This cubemap affects the diffuse lighting during image based lighting. Use the Environment Ambient Factor property to set th… |
| `Environment Reflection Factor` | Sets the strength of the cubemap texture to use for specular environment light. Use the Environment Reflection Texture property to set the cubemap texture. The specular environment light affects refle… |
| `Environment Reflection Texture` | Sets the cubemap to use for the specular environment light for the material. This cubemap affects reflective lighting during image based lighting. Use the Environment Reflection Factor property to set… |
| `Export in Asset Package` | When enabled, this item is exported into asset package if this project is saved as one. |
| `Exposure` | Sets the exposure compensation for the material. The exposure compensation emulates camera exposure by controlling the total amount of light rendered. Use a negative value to darken the rendered image… |
| `F` | Tonemapping parameter F. |
| `Fixed Character Width` | When set, overrides the font advance widths to make each character take a fixed amount of space specified in pixels. |
| `Focus On Press` | Sets where to set the focus when the user presses the node that has this property: * None (0) keeps the focus where it was. This is the default. * Node (1) sets the focus to the node. * Node or ancest… |
| `Focus Order` | Sets the focus chain order of the node within the focus scope. |
| `Focus Scope Type` | Sets the type of the focus scope node: * Group groups focusable nodes. * Fence keeps the focus chain navigation inside the scope and does not allow the focus chain navigation to enter or leave that sc… |
| `Focus State` | Reports the focus state of a node: * No focus (0) indicates that the node is not focused. For a focus scope node indicates that none of the nodes in the scope have focus. * Logical focus (1) indicates… |
| `Focusable` | Indicates whether the node can receive focus. |
| `Focused` | Indicates whether the node has the key focus. |
| `Font Color` | Sets the color of the text in a 3D text node. |
| `Font Family` | The font family used to render the text. |
| `Font Hinting Preference` | Sets the hinting preference of the font. * No hinting: Render text without hinting the outlines of glyphs. * Native hinting: Prefer native hinter of the font over the auto-hinter of the rasterizer. * … |
| `Font Material` | Sets the material whose shader is used to render the text. The shader must use the ContentTexture uniform which is automatically filled with glyph data. |
| `Font Size` | Sets the size of the font in pixels. |
| `Font Style` | Sets the style of the font. |
| `Font Weight` | Sets the weight of the font. |
| `Force Composition` | Force rendering to composing target even if not otherwise necessary. |
| `Foreground Brush` | The foreground brush to paint the foreground of 2D nodes. |
| `Foreground Hint` | Give a hint of the type of the foreground of 2D nodes: * None renders the background brush after rendering the node. * Translucent renders the background brush before the content of the node. * Occlud… |
| `Fractional Character Width` | Sets whether Kanzi uses fractional or rounded character widths to lay out text. In most cases fractional widths provide the best result. However, with small font sizes, fractional widths can cause the… |
| `Global Ambient Color` | Sets the color that is multiplied automatically with the Ambient property of the materials in the scene. Use the Intensity (I) property field to adjust the exposure of the color. |
| `Glossiness Factor` | Sets the glossiness of the material: 0 represents a rough, diffuse surface, and 1 represents a smooth, glossy surface. |
| `Glossiness Texture` | Sets the texture that contains a glossiness map for the material. Kanzi reads the glossiness from the Alpha channel of this texture. Use the Glossiness Factor property to scale the glossiness from thi… |
| `Grading Color Highlight` | Sets the color grading highlight color. |
| `Grading Color Midtone` | Sets the color grading midtone color. |
| `Grading Color Shadow` | Sets the color grading shadow color. |
| `Grading Highlight Range` | Sets the luminance range where the highlight color is applied. |
| `Grading Hue Saturation Value` | Sets the HSV adjustment for the input color. |
| `Grading Shadow Range` | Sets the luminance range where the shadow color is applied. |
| `Hit Test Camera` | Sets which hit test camera to use in scenes rendered by the selected Viewport 2D. If not set, Kanzi uses the camera in the scene. |
| `Hit Testable` | When enabled, the node can be hit tested. Enabling Hit Testable for a 2D node enables hit testing only for that node. Enabling Hit Testable for a 3D node enables hit testing also for the child nodes. … |
| `Hold Interval` | Sets the amount of time in milliseconds that the user must hold the button pressed down for Kanzi to recognize it as a long-press gesture. To disable the long-press gesture, set to 0. |
| `Horizontal Alignment` | The alignment in horizontal direction the node should use when it resides under a layout. |
| `Horizontal Fit` | Whether to horizontally scale the glyphs to make them fit into the Layout Width of the Text Block. To adjust the scale, use the Horizontal Fit Scale Limits property. |
| `Horizontal Fit Scale Limits` | When the Horizontal Fit property is enabled, sets the minimum and maximum scale for glyphs when the width of text in a Text Block does not match the Layout Width of that Text Block. For example: * Min… |
| `Horizontal Margin` | Sets the horizontal space between this node and other nodes that are adjacent to this node in a layout. To access the Horizontal Margin property fields in a binding, use: * X for the Left property fie… |
| `Horizontal Padding` | Sets the padding spaces between the content and the left and right boundaries of the Text node. |
| `Hover` | Indicates whether a node is the foremost hit testable node under the cursor. |
| `Image` | The image to display. |
| `Index In Group` | Sets the index of the Toggle Button in the Toggle Button Group to which that Toggle Button is registered. If a Toggle Button does not have a local value for this property, it is not registered to the … |
| `Inner Distance` | Sets the distnace range where the vignette color transition starts. |
| `Invert Content Mask` | Whether to invert the value that Kanzi calculates using content masking. |
| `Invert Mask` | Whether to invert the mask so that transparent areas become opaque and opaque areas become transparent. |
| `Is Down` | Indicates whether the button is pressed and in the down state. |
| `Is Value Changing` | Whether the value is currently changing. |
| `Item Index` | Reports the index of the item in the List Box Item Container. |
| `Layout Direction` | The direction in which the items are arranged when you add them to a grid layout. |
| `Layout Transformation` | The 2D transformation to be applied before layouting. |
| `Left Image` | The image to use in the center-left. |
| `Line Spacing` | Sets the line spacing in multiples of the normal line height of the selected font. |
| `Mask Channel` | Sets the texture channel to use as the input for the mask: * Alpha uses the alpha channel from the texture. This is the default. * Red uses the red color channel from the texture. * Green uses the gre… |
| `Mask Height` | Sets the height of the mask to use in a layout. This value overrides the height of the texture that you use as the mask. |
| `Mask Horizontal Alignment` | Sets the horizontal alignment of the mask effect: * Left aligns the left edge of the mask with the left edge of the node. This is the default. * Right aligns the right edge of the mask with the right … |
| `Mask Offset` | Sets the mask offset along the X and Y axes in pixels. Kanzi applies the mask offset after stretch, alignment, and scale. |
| `Mask Scale` | Sets the factor by which to scale the mask. Kanzi applies the scale after stretch and alignment. |
| `Mask Strength` | Sets the strength of the mask effect in the range from 0 to 1: * 0 disables the mask effect. * 1 applies the mask at full strength. This is the default. * Any value between 0 and 1 partially applies t… |
| `Mask Stretch` | Sets the stretch mode of the mask effect: * None disables stretching. This is the default. * Fill stretches the mask to fill the node. * Uniform stretches the mask using uniform scaling to fill the no… |
| `Mask Texture` | Sets the texture that masks another texture or color. |
| `Mask Texture Offset` | Sets an offset for mask in materials. |
| `Mask Texture Tiling` | Determines the number of times a mask is presented in a material |
| `Mask Vertical Alignment` | Sets the vertical alignment of the mask effect: * Bottom aligns the bottom edge of the mask with the bottom edge of the node. * Top aligns the top edge of the mask with the top edge of the node. This … |
| `Mask Width` | Sets the width of the mask to use in a layout. This value overrides the width of the texture that you use as the mask. |
| `Masked Blur` | Sets whether to blur only the pixels whose alpha channel value is not zero. When you enable this property, the blur does not spread to fully transparent pixels and the edges of the content stay sharp.… |
| `Maximum Distance From Curve` | The distance from the curve where hit testing succeeds. |
| `Maximum Value` | The maximum value that the range allows. |
| `Metallic Factor` | Sets the metalness of the material: 0 represents a non-metallic or dielectric object, and 1 represents a metallic object. |
| `Metallic Texture` | Sets the texture that contains a metallic map for the material. Kanzi reads the metalness from the Blue channel of this texture. Use the Metallic Factor property to scale the value from this texture. |
| `Minimum Value` | The minimum value that the range allows. |
| `Mipmap Mode` | Sets the mipmap mode to use with the temporary composition targets to which Kanzi renders this node. |
| `Morph Data Texture` | Data texture to use for storing morph data when the are are too many targets to use regular attribute channels. |
| `Morphing` | Add morph weights to Model3D to enable Morphing. |
| `Multisample Level` | Sets the amount of multisample anti-aliasing to apply to the temporary composition targets to which Kanzi renders this node. |
| `Node.Path` | Full path to the node. |
| `Normal Scale` | Sets the normal scale for the material. Use the scale to set the intensity of the Normal Texture. |
| `Normal Texture` | Sets the texture that contains a normal map for the material. Use the Normal Scale property to scale the texture value. |
| `Normalized Value` | The current value normalized to range [0, 1]. |
| `Occlusion Render Strength` | Sets the SSAO strength for the material. Use the strength to set the intensity of the SSAO Texture. |
| `Occlusion Render Texture` | Sets the texture that contains a SSAO computed for the scene. Use the Occlusion Render Strength property to scale the strength of the SSAO. |
| `Occlusion Strength` | Sets the occlusion strength for the material. Use the strength to set the intensity of the Occlusion Texture. |
| `Occlusion Texture` | Sets the texture that contains an occlusion map for the material. Use the Occlusion Strength property to scale the occlusion from the texture. |
| `Off-Screen Rendering` | When set and the node has an explicitly set render target, do not render the resulting framebuffer to screen. |
| `Opacity` | Opacity of the node. |
| `Outer Color` | Sets the vignette color. |
| `Outer Distance` | Sets the distnace range where the vignette color transition ends. |
| `Outline Color` | Sets the color of the outline. |
| `Outline Inner Softness` | Sets the softness of the outline relative to its width inside the content area. For a sharp outline, set to 0. For a fade-in that takes the complete outline width to reach maximum value, set to 1. By … |
| `Outline Inner Width` | Sets the width of the outline in pixels inside the content area. By default, this property uses the value of the Outline Width property. |
| `Outline Method` | Sets the method for outline calculation: * Box uses box search which potentially consumes less memory but is slower. * Two-pass uses two-pass search which potentially consumes more memory but is faste… |
| `Outline Softness` | Sets the softness of the outline. For a sharp outline, set to 0. For a fade-in that takes the complete outline width to reach maximum value, set to 1. The default value is 0.27. |
| `Outline Texture` | Sets the texture to apply to the outline. Kanzi applies to the outline only the top row of pixels from this texture. Set Outline Color to the color with which you want to modulate the colors in this t… |
| `Outline Texture Offset` | Sets the relative starting offset for sampling the outline texture. The default value is 0.0. |
| `Outline Texture Tiling` | Sets the number of times the texture wraps around within the outline area. To repeat a texture, set its Wrap Mode to Repeat. The default value is 1.0 |
| `Outline Width` | Sets the width of the outline in pixels outside the content area. The default value is 4 pixels. |
| `Overflow` | Sets the characters that represent the truncated text when the text does not fit in this node. The default value is ‘…’. By default, Kanzi truncates the text at the end. Use the Truncation Direction p… |
| `Override Shadow Offset` | Sets the offset of the shadow from the object along the x and y axes in pixels. When you set this property, the Shadow Angle and Shadow Distance properties have no effect. To disable the offset overri… |
| `Perspective Transformation` | The 3D transformation to be applied after layouting. |
| `Perspective Transformation FOV` | The 3D transformation field of view (degrees) to be applied after layouting. |
| `Perspective Transformation Mode` | Defines the mode of operation for the coordinate system and field of view. |
| `Perspective Transformation Origin` | The 3D transformation origin to be used for perspective transformation on this or child nodes. |
| `Perspective Transformation Pivot` | The 3D pivot point in relative coordinates. |
| `Pixel Format` | The pixel format of the node if rendering to a texture. |
| `Planar Reflection Map` | Rendered texture for planar reflections. |
| `Planar Reflection View Projection` | The premultiplied projection view matrix for planar reflections. |
| `Point Shadow Map` | Depth cubemap used to calculate point light shadows. |
| `Point Shadow Near Far` | Sets the near &amp; far values used for point shadow calculations. |
| `Remove Side Bearings` | Whether to position the leftmost characters of left-aligned text and rightmost characters of right-aligned text exactly within the boundary of the text node. |
| `Render Pass Prefab` | Sets which render pass prefab will be used to instantiate the render pass tree. |
| `Render Self` | Whether the node renders itself. Does not affect the rendering of child nodes. |
| `Render Target` | Forces the node to be rendered into a given render target texture. When set to “No Target”, regular conditions whether node is rendered to a texture, such as opacity and rotation, are applied. |
| `Render Target Minimum Height` | Sets the minimum height of implicitly generated render targets. |
| `Render Target Minimum Width` | Sets the minimum width of implicitly generated render targets. |
| `Render Target Reallocation Limit` | The change in size that triggers reallocation of a render target. |
| `Render Transformation` | The 2D transformation to be applied after layouting. |
| `Render Transformation Origin` | Sets the render transform origin in relative coordinates. |
| `Right Image` | The image to use in the center-right. |
| `Roughness Factor` | Sets the roughness of the material: 0 represents a smooth, glossy surface, and 1 represents a rough, diffuse surface. |
| `Roughness Texture` | Sets the texture that contains a roughness map for the material. Kanzi reads the roughness from the Green channel of the texture. Use the Roughness Factor property to scale the roughness from this tex… |
| `Row` | The row into which grid layout places the item. |
| `Row Span` | Defines the number of rows an item in a grid layout occupies. |
| `Selected` | Indicates whether the List Box item held by this List Box Item Container is selected. The List Box sets the value of this property. |
| `Selected Item Index` | Sets the index of the item that is currently selected in the List Box node. A List Box node updates this property when the user scrolls that List Box node. To select an item in the List Box node, set … |
| `Shadow Angle` | Sets the direction of the shadow as an angle relative to the positive x axis. The default is 45 degrees. When you set the Override Shadow Offset property, this property has no effect. |
| `Shadow Blur Radius` | Sets the softness of the shadow by defining the distance in pixels the shadow blur extends outward from an edge. For a shadow with sharp edges, set to 0. The default is 8 pixels. |
| `Shadow Color` | Sets the color and alpha of the shadow. |
| `Shadow Distance` | Sets how far to move the shadow from the object in the direction set by the Shadow Angle property. The default is 10 pixels. When you set the Override Shadow Offset property, this property has no effe… |
| `Shadow Only` | Whether to render only the shadow without the node contents. |
| `Shadow Quality` | Sets the visual quality of the shadow. Lower quality uses less computing and memory resources. |
| `Shadow Type` | Sets the type of the shadow: * Drop Shadow appears behind or below objects. * Inner Shadow appears inside objects. |
| `Show Material Debug Objects` | When enabled, Kanzi Studio does not hide material debug objects. |
| `Side` | The docking side of an item in the dock layout. |
| `Snap Character To Pixel` | Sets whether Kanzi positions characters in 2D rendering to the nearest pixel: * When enabled, text sharpness improves, but some characters can shift a fraction of a pixel. * When disabled, certain com… |
| `Snap to Pixel` | Snap the translation of the node and its size into pixel boundary. |
| `Specular Anti-Aliasing Strength` | Sets the strength of the specular anti-aliasing effect. Higher value results in blurrier specular highlights. For no specular anti-aliasing, set the value to 0. For full specular anti-aliasing, set th… |
| `Specular Anti-Aliasing Threshold` | Sets the upper limit for the amount of specular anti-aliasing effect to apply. The default value is 0.18. |
| `Specular Color` | Sets the color of the specular reflection. |
| `Specular Color Factor` | Sets the specular color for the material. |
| `Specular Color Texture` | Sets the texture that contains the specular color for the material. Use the Specular Color Factor property to filter the value from this texture. |
| `Specular Exponent` | Sets the size of the specular highlight. |
| `Spot Light View Projection` | The premultiplied projection view matrix of a spot light. |
| `Spot Shadow Map` | Depth map used to calculate spot shadows. |
| `State Manager` | Sets the State Manager to the node. |
| `Step Value` | The minimum amount that the value of the range can change at a time. |
| `Stretch` | Whether to scale this Trajectory Layout to match the layout size. |
| `Style` | Sets a style to the node. |
| `Text` | Sets the text content that the text node renders. To create a line break press Shift+Enter. |
| `Text Horizontal Alignment` | Sets the horizontal alignment of the text. |
| `Text Vertical Alignment` | Sets the vertical alignment of the text. |
| `Texture` | Sets the texture of the material. |
| `Texture 0` | Sets the first texture you want the Blit render pass to blit. |
| `Texture 1` | Sets the second texture you want the Blit render pass to blit. |
| `Texture 2` | Sets the third texture you want the Blit render pass to blit. |
| `Texture 3` | Sets the fourth texture you want the Blit render pass to blit. |
| `Texture 4` | Sets the fifth texture you want the Blit render pass to blit. |
| `Texture 5` | Sets the sixth texture you want the Blit render pass to blit. |
| `Texture 6` | Sets the seventh texture you want the Blit render pass to blit. |
| `Texture 7` | Sets the eighth texture you want the Blit render pass to blit. |
| `Texture 8` | Sets the ninth texture you want the Blit render pass to blit. |
| `Texture 9` | Sets the tenth texture you want the Blit render pass to blit. |
| `Texture Offset` | Sets an offset for texture in materials. |
| `Texture Tiling` | Determines the number of times a texture is presented in a material. |
| `Toggle State` | Sets the toggle state of a Toggle Button. To update this property with a binding, use a to-source or two-way binding. |
| `Toggle State Count` | Sets the number of toggle states of a Toggle Button. |
| `Tone Map Linear Scale` | Sets the scale for the linear tonemap option for the material. When linear tonemapping is used, Kanzi divides all output color by the value of this property. |
| `Top Image` | The image to use in the middle of the top row. |
| `Top-Left Image` | The image to use in the top-left corner. |
| `Top-Right Image` | The image to use in the top-right corner. |
| `Trajectory Override Offset` | Sets the offset of an item in a Trajectory Layout. When you do not set this property, the Trajectory Layout sets the offset. |
| `Transition Phase` | The phase of the transition. For example, use for pixel-based effects. |
| `Truncation` | Sets how Kanzi truncates text when either Truncation or Overflow property is set and the text does not fit in this node: * None disables text truncation. * At character truncates text character by cha… |
| `Truncation Direction` | Sets which part Kanzi truncates when either the Truncation or Overflow property is set and the text does not fit in this node: * Trailing truncates single- and multiline text at the end. Default value… |
| `Two Pass Rendering` | Defines whether the Text Block 3D is rendered in two passes. Disabling the two pass rendering improves performance, but can cause invalid rendering results when glyph bounds overlap. |
| `Use Intensity Texture` | Enable or disable the use of the Bloom Intensity texture property. |
| `Use Screen Space` | Whether to layout the mask relative to the screen instead of the node. |
| `Value` | The current value. To update this property with a binding, use a to-source or two-way binding. |
| `Vertical Alignment` | The alignment in vertical direction the node should use when it resides under a layout. |
| `Vertical Margin` | Sets the vertical space between this node and other nodes that are adjacent to this node in a layout. To access the Vertical Margin property fields in a binding, use: * X for the Bottom property field… |
| `Vertical Padding` | Sets the padding spaces between the content and the top and bottom boundaries of the Text node. |
| `Visible` | When disabled, Kanzi does not render the node. |
| `Visible Amount in Parent` | Sets the amount the node is inside its parent. Use the value of this property in shaders to implement fades. Calculated by the parent node. |
| `White Scale` | Sets the value that will be tonemapped to pure white. |
| `Word Wrap` | Sets whether to break long lines into multiple lines to make the text fit within the boundaries of the Text Block node. |
| `Last Item Fill` | Whether the last item of the dock layout is given the remaining free space. |
| `Primary Direction` | The direction along which the layout arranges items until the layout limit in that direction is reached. |
| `Secondary Direction` | The direction along which the flow layout arranges lines of the primary direction. |
| `Align To Tangent` | Whether to align the Trajectory List Box 3D items to match the tangent of the trajectory. |
| `Allowed Scroll Axis` | Sets the axis on which you want to allow this Trajectory List Box 3D node to scroll. |
| `Cursor Offset` | Sets the offset of the position to use to select the active item, in proportional range [0,1]. |
| `Dragging Acceleration` | Sets the acceleration of the Trajectory List Box 3D when the user scrolls the Trajectory List Box 3D by dragging the pointer. The higher the value, the quicker the Trajectory List Box 3D reaches its f… |
| `Dragging Drag` | Sets the amount that drag affects the movement of the Trajectory List Box 3D when the user scrolls the Trajectory List Box 3D by dragging the pointer. The lower the value, the higher the drag and the … |
| `Dragging Impulse` | Sets the amount of impulse to generate from the pointer movement when the user scrolls the Trajectory List Box 3D by dragging the pointer. |
| `Item Area Begin` | Sets the proportional offset where the part of the trajectory meant for the fully visible Trajectory List Box 3D items starts. Kanzi uses the values of the Item Area Begin and Item Area End properties… |
| `Item Area End` | Sets the proportional offset where the part of the trajectory meant for the fully visible Trajectory List Box 3D items ends. Kanzi uses the values of the Item Area Begin and Item Area End properties t… |
| `Looping` | Whether to show items in the Trajectory List Box 3D from the beginning after reaching the last item. |
| `Maximum Number of Touches` | Sets the maximum number of touch points allowed on the Trajectory List Box 3D area for scrolling. |
| `Minimum Number of Touches` | Sets the minimum number of touch points required on the Trajectory List Box 3D area for scrolling. |
| `Recognition Threshold` | Sets the distance in pixels that the pointer has to move for the scrolling to start in the Trajectory List Box 3D. |
| `Reversed Scrolling` | Whether the scroll position in the Trajectory List Box node increases in relation to the direction of the pan gesture. This reverses the direction of scrolling. By default, the scroll position decreas… |
| `Scroll Position` | Sets the scroll position of the Trajectory List Box 3D along the x and y axes as a relative position within the list box area. Use this property to move the list to a scroll position immediately, with… |
| `Scroll Sensitivity` | Sets the amount that the scroll value changes relative to the movement of the pointer on the scroll view plane of the Trajectory List Box 3D. The default value 1 makes the Trajectory List Box 3D scrol… |
| `Sliding Acceleration` | Sets the acceleration of the Trajectory List Box 3D after the user releases the pointer with which they scroll the Trajectory List Box 3D. The higher the value, the quicker the Trajectory List Box 3D … |
| `Sliding Drag` | Sets how much drag affects the movement of the Trajectory List Box 3D after the user releases the pointer with which they scroll the Trajectory List Box 3D. The lower the value, the higher the drag an… |
| `Spacing` | Sets the distance between the items in the Trajectory List Box 3D. |
| `Swipe Distance` | Sets the distance that a swipe sends the scroll value in the Trajectory List Box 3D, relative to the speed of the pointer. |
| `Items Source` | Data object which provides data sources for list items. |
| `Cell Height` | Sets the height of each cell in the Grid List Box. |
| `Cell Width` | Sets the width of each cell in the Grid List Box. |
| `Scroll Speed` | Reports the current scroll speed of the Grid List Box. |
| `Scroll Target Position` | Reports the current target scroll value of the Grid List Box. |
| `Scrolling` | Reports whether the Grid List Box is currently scrolling. |
| `Item Container Generator` | Sets the name of the item container generator type to use to provide item containers dynamically for the List Box. |
| `Item Container Template` | Sets the List Box Item Container prefab that sets the appearance and behavior of the List Box items. |
| `Item Generator` | Sets the name of the item generator type to use to provide items dynamically to the List Box. |
| `Item Template` | Sets the prefab to use for the List Box items. |
| `Keep Alive Item Count` | Sets the size of the buffer for invisible List Box items. Kanzi returns to the Item Generator those invisible items that do not fit in the buffer. |
| `Selection Behavior` | Sets how the List Box behaves when the user selects an item. ‘Bring to Center’ sets the List Box to bring an item to the center of the List Box area when the user selects that item. |
| `Looping X Enabled` | Sets the node controlled by a Scroll View node to start scrolling from the beginning when the scroll reaches the scroll bounds on the x axis. When the scroll value reaches the maximum value of the bou… |
| `Looping Y Enabled` | Sets the node controlled by a Scroll View node to start scrolling from the beginning when the scroll reaches the scroll bounds on the y axis. When the scroll value reaches the maximum value of the bou… |
| `Maximum Zoom` | Sets the maximum zoom level. |
| `Minimum Zoom` | Sets the minimum zoom level. |
| `Reversed X Axis Scroll` | Whether the scroll position of the x axis increases in relation to the direction of the pan gesture. This reverses the direction of scrolling. By default, the scroll position decreases in relation to … |
| `Reversed Y Axis Scroll` | Whether the scroll position of the y axis increases in relation to the direction of the pan gesture. This reverses the direction of scrolling. By default, the scroll position decreases in relation to … |
| `Scroll Bounds Maximum` | Sets the coordinates of the bottom-right corner of the scroll bounds rectangle. Scroll bounds define where the scrolling begins and ends. |
| `Scroll Bounds Minimum` | Sets the coordinates of the top-left corner of the scroll bounds rectangle. Scroll bounds define where the scrolling begins and ends. |
| `Step Multiplier` | Sets the smallest distance that a Scroll View scrolls. |
| `Zoom` | Sets the current zoom level. |
| `Zoom Affects Scrolling` | Controls whether the scroll position is scaled, according to the zoom level. |
| `Zoom Enabled` | Sets whether to install a pinch manipulator that generates zoom messages. |
| `Override Distance` | Sets the distance between the items in this Trajectory Layout. When you do not set this property, the Trajectory Layout calculates the distance automatically. |
| `Layout Depth` | The size of the node in depth direction when used in a layout. Overrides the default bounds of the item. |
| `Constraint In World Coordinates` | Specifies if the object constraining is done in world coordinates (when false, done in local coordinates). |
| `Constraint Orientation` | Makes an object node where the property is attached to obtain orientation from target object |
| `Constraint Position` | Makes an object node where the property is attached to obtain position from target object |
| `Face to Camera Mode` | Sets how to rotate the 3D node towards a camera: * Disabled does not make the node turn to the camera. * Look at rotates the node along all axes to turn to the camera. * Billboarding keeps the node pe… |
| `Face to Camera Target Camera` | Sets the camera towards which the 3D node turns when you set the Face to Camera Mode property. The default is the Scene default camera. |
| `Look At` | Makes a node to always face the node set in this property. |
| `Hit Testable Container` | When enabled, Kanzi uses the layout bounds as geometry for hit testing. |
| `Actual Layout Depth` | The calculated size of the node in depth direction when used in a layout. |
| `Depth Margin` | Sets the depth distance between this node and other nodes that are adjacent to this node in a layout. To access the Depth Margin property fields in a binding, use: * X for the Back property field * Y … |
| `Drawn as Bounding Box` | When enabled the object is drawn its solid bounding box. |
| `Frustum Cull Margin` | The margin of the frustum cull radius of the node. For example, set the margin when a vertex shader modifies the geometry of the node. To use this property, enable the Frustum Culling property in the … |
| `Final Transformation` | The combined location, orientation and scale of the node and its ancestor nodes. Automatically calculated by the system. |
| `Previous Final Transformation` | Final transformation (world matrix) from the previous frame, used for velocity buffer calculation. |
| `Override Material` | Sets the override material to use to render the content of the 2D prefab in the Viewport 3D node. In the Viewport 3D node, bind a texture property of the override material to the Viewport3D.PrefabText… |
| `Prefab Template` | Sets the 2D prefab whose content the Viewport 3D node renders in 3D space. |
| `2D to 3D Projection Scale` | Sets the scale factor to project pixels to 3D size. When scale is 1, then the size of one pixel is one 3D space unit. |
| `Depth Alignment` | The alignment in depth direction the node should use when it resides under a layout. |
| `Depth Padding` | Sets the padding spaces between the content and the front and back boundaries of the Content Layout 3D node. |

---

## 通用消息表（112 个，所有节点共有）

| 属性 | 说明 |
|------|------|
| `Activity Host: Activity Prefab Attached` | An Activity Host sends this message when it attaches the prefab of the Activity that is activated. |
| `Activity Host: Activity Prefab Detached` | An Activity Host sends this message when it detaches the prefab of the Activity that is deactivated. |
| `Activity: Activated` | An Activity sends this message when it is activated. |
| `Activity: Activating` | An Activity sends this message when it is in the activating state. |
| `Activity: Deactivated` | An Activity sends this message when it is deactivated. |
| `Activity: Deactivating` | An Activity sends this message when it is in the deactivating state. |
| `Activity: Status Changed` | An Activity sends this message when the value of its Activity Status property changes. |
| `Animation Player: Completed` | Occurs when an Animation Player completes animation playback. |
| `Animation Player: Started` | Occurs when an Animation Player starts animation playback. |
| `Animation Player: Stopped` | Occurs when an Animation Player stops animation playback. |
| `Button: Cancel` | Occurs when a user lifts their finger outside of a Button that they previously pressed. |
| `Button: Click` | Occurs when a user lifts their finger on top of a Button that they previously pressed and when the time set by the Auto Press Interval property in the pressed Button expires. |
| `Button: Down` | Occurs when the user presses down the Button. |
| `Button: Enter` | Button: Enter trigger is set off: * When the user presses down the button. * When the user presses down the button, moves the pointer outside of the button area, and then moves the pointer back to the… |
| `Button: Leave` | Button: Leave trigger is set off: * When the user presses down the button and then lifts the pointer. * When the user presses down the button and then moves the pointer outside of the button area. * W… |
| `Button: Long Press` | Occurs when the user presses down a Button and holds the Button pressed for the amount of milliseconds defined in the Hold Interval property of that Button. |
| `Click: Begin` | Occurs when the user presses a hit-testable node with a Click Manipulator. You cannot use this trigger with nodes that handle input by default, such as Button and Toggle Button nodes. |
| `Click: Cancel` | Occurs when the user first presses a hit-testable node with a Click Manipulator, then moves the pointer outside of the node area, and lifts the pointer. You cannot use this trigger with nodes that han… |
| `Click: Click` | Occurs when the user presses and releases a hit-testable node with a Click Manipulator, while the pointer is still within the node area and Kanzi does not recognize another gesture. You cannot use thi… |
| `Click: Enter` | Occurs when the user presses a hit-testable node with a Click Manipulator and then every time the user moves the pointer on top of that node while still holding down the pointer. You cannot use this t… |
| `Click: Leave` | Occurs when the user presses a hit-testable node with a Click Manipulator and then every time the user moves the pointer outside of that node. You cannot use this trigger with nodes that handle input … |
| `Command: Command` | Command message arguments |
| `Data Trigger` | Monitors changes in properties and data source values. Use a Data Trigger to apply an action to either set a property value of a target node or activate an Activity node. |
| `Drag and Drop: Drag and Drop Canceled` | Occurs when focus moves away from the node during the drag-and-drop gesture. |
| `Drag and Drop: Drag and Drop Finished` | Occurs when the user lifts their finger after starting the drag-and-drop gesture. |
| `Drag and Drop: Drag and Drop Moved` | Occurs when the user moves their finger after starting the drag-and-drop gesture. |
| `Drag and Drop: Drag and Drop Started` | Occurs when the user holds their finger for 500ms on the node. |
| `Focus: About To Gain Focus` | Kanzi sends this message before a focusable node receives focus. |
| `Focus: About To Lose Focus` | Kanzi sends this message before the focused node loses focus. |
| `Focus: Focus Entered Focus Scope` | When focus enters a focus scope, Kanzi sends this message to the focus scope node that contains the node that gains focus. |
| `Focus: Focus Gained` | Kanzi sends this message to the node that received focus. |
| `Focus: Focus Left Focus Scope` | When focus leaves a focus scope, Kanzi sends this message to the focus scope node that contains the node that loses focus. |
| `Focus: Focus Lost` | Kanzi sends this message to the node that lost focus. |
| `Focus: Input Outside Overlay` | Kanzi sends this message to an overlay focus scope when the application area outside the boundaries of that overlay receives input. |
| `Focus: Overlay Brought To Front` | Occurs when an overlay focus scope becomes the foremost overlay scope in the overlay focus scope stack. |
| `Focus: Overlay Gained Focus` | When an overlay scope gains focus, Kanzi sends this message to the overlay scope node that contains the node that gains focus. |
| `Focus: Overlay Lost Focus` | When an overlay scope loses focus, Kanzi sends this message to the overlay scope node that contains the node that loses focus. |
| `Focus: Overlay Sent To Back` | Occurs when an overlay focus scope is no longer the foremost overlay scope in the overlay focus scope stack. |
| `Key Input: Key Canceled` | Occurs when Kanzi recognizes a key-canceled gesture. A key-canceled gesture occurs when Kanzi recognizes that the user canceled a gesture. |
| `Key Input: Key Pressed` | Occurs when Kanzi recognizes a key-pressed gesture. A key-pressed gesture occurs when Kanzi recognizes a key event that contains all the elements that compose that gesture. |
| `Key Input: Key Released` | Occurs when Kanzi recognizes a key-released gesture. A key-released gesture occurs when Kanzi recognizes the release of one of the elements that compose that gesture. |
| `Key Navigation: Key Navigation Canceled` | Occurs when the key-pressed gesture is canceled for the navigation direction. |
| `Key Navigation: Key Navigation Finished` | Occurs when Kanzi recognizes the key-released gesture for the navigation direction. To capture key navigation gestures for a node, create a Navigation Manipulator component in that node. |
| `Key Navigation: Key Navigation Started` | Occurs when Kanzi recognizes the key-pressed and key repeat gestures for the navigation direction. To capture key navigation gestures for a node, create a Navigation Manipulator component in that node… |
| `List Box: Item Loaded` | Occurs when an item is loaded to the working memory. To set how many items you want to keep loaded in the working memory at a time, use the Keep Alive Item Count property. |
| `List Box: Item Selected` | Occurs when an item is selected. |
| `List Box: Item Unloaded` | Occurs when an item is unloaded from the working memory. To set how many items you want to keep loaded in the working memory at a time, use the Keep Alive Item Count property. |
| `List Box: Scroll Finished` | Occurs when the List Box stops scrolling. |
| `List Box: Scroll Started` | Occurs when the List Box starts to scroll. |
| `List Box: Scrolled` | Occurs when the List Box scrolls. |
| `List Box: Target Changed` | Occurs when List Box gets a new target item. |
| `List Box: User Scroll Finished` | Occurs when the application user stops scrolling the List Box. |
| `List Box: User Scroll Started` | Occurs when the application user starts to scroll the List Box. |
| `Long Press: Long Press` | Occurs when the user presses a hit-testable node with a Long-Press Manipulator and holds the press for the time that you set in the Long-Press Manipulator. You cannot use this trigger with nodes that … |
| `Long Press: Long Press Cancel` | Occurs during the long-press gesture when the user moves the focus away from a hit-testable node with a Long-Press Manipulator. You cannot use this trigger with nodes that handle input by default, suc… |
| `Message Trigger` |  |
| `Multi-Click: Intermediate Click` | Occurs when the user presses and releases a hit-testable node with a Multi-Click Manipulator that is set to send messages for intermediate clicks. To set a Multi-Click Manipulator to send messages for… |
| `Multi-Click: Multi-Click` | Occurs when the user presses and releases a hit-testable node with a Multi-Click Manipulator a specified number of times (default 2) within a set amount of time (default 250 ms) between presses. You c… |
| `Multi-Click: Multi-Click Canceled` | Occurs during the multi-click gesture when the user moves the focus away from a hit-testable node with a Multi-Click Manipulator. You cannot use this trigger with nodes that handle input by default, s… |
| `On Attached` | This trigger is set off when the item is initialized. For example, when you add a node to the node tree, or enter a state that contains this trigger. |
| `On Property Change` | Occurs when a property is changed |
| `On Timer` | Occurs when timer interval is elapsed |
| `Page (deprecated): Activated (deprecated)` | Page has been activated. |
| `Page (deprecated): Deactivated (deprecated)` | Page has been deactivated. |
| `Page Host (deprecated): Page Navigation Finished (deprecated)` | Page host has finished navigation process. |
| `Page Host (deprecated): Page Navigation Started (deprecated)` | Page host has started navigation process. |
| `Pan: Pan Canceled` | Occurs when focus moves away from the node during the pan gesture. |
| `Pan: Pan Entered` | Occurs when the pan gesture enters the node to which the Pan Manipulator is attached. |
| `Pan: Pan Finished` | Occurs when the user lifts their finger after Kanzi recognizes a pan gesture. |
| `Pan: Pan Left` | Occurs when the pan gesture leaves the node to which the Pan Manipulator is attached. |
| `Pan: Pan Moved` | Occurs when the user changes the position of their finger and that change exceeds the recognition thresholds. |
| `Pan: Pan Started` | Occurs when the user presses down their finger on the node. If the user lifts their finger before exceeding the position change threshold, Kanzi cancels the pan gesture. |
| `Pinch: Pinch Canceled` | Occurs when focus moves away from the node during the pinch gesture. |
| `Pinch: Pinch Finished` | Occurs when the user lifts their finger after Kanzi recognizes a pinch gesture. |
| `Pinch: Pinch Moved` | Occurs when the user changes the position of their finger and that change exceed the scale or rotation threshold. |
| `Pinch: Pinch Started` | Occurs when the user presses down their finger. If the user lifts their finger before it exceeds the scale or rotate threshold, Kanzi cancels the pinch. |
| `Prefab View: Asynchronous Load Completed` | Occurs when asynchronous loading of resources from a prefab has been finished. |
| `Property Target Easing Interpolator: Easing Interpolation Completed` | Occurs when Property Target Easing Interpolator completes its interpolation. |
| `Property Target Interpolator: Interpolation Completed` | Occurs when property target interpolator completes interpolation. |
| `Range: Value Change Finished` | Occurs when the range value stops changing. |
| `Range: Value Change Started` | Occurs when the range value starts changing. |
| `Range: Value Changed` | Occurs when the range value has changed. |
| `Scroll View: Scroll Ended` | Occurs when the scroll position of a Scroll View node stops changing. |
| `Scroll View: Scroll Started` | Occurs when the scroll position of a Scroll View node starts changing. |
| `Scroll View: Scroll Zoomed` | Occurs when the zoom level of a Scroll View node changes. |
| `Scroll View: Scrolled` | Occurs when the scroll position of a Scroll View node changes. |
| `Scroll View: Snap Request` | Occurs when a Scroll View node requests snapping target from the hosting component. |
| `Scroll View: User Scroll Ended` | Occurs when the user stops scrolling a Scroll View node. |
| `Scroll View: User Scroll Started` | Occurs when the user starts scrolling a Scroll View node. |
| `State Manager: Entered State` | Occurs when a state manager has entered a state. |
| `State Manager: Left State` | Occurs when a state manager has left a state. |
| `State Manager: Transition Finished` | Occurs when a state manager finishes a transition to a state. |
| `State Manager: Transition Started` | Occurs when a state manager begins a transition to a state. |
| `Text Box: Composition Text Changed` | Occurs when the text produced in an Input Method Editor is updated in a Text Box node. |
| `Text Box: Composition Text Committed` | Occurs: * When the text produced in an Input Method Editor is committed to the cached text in a Text Box node. * When a trigger executes the Text Box: Commit Composition Text action. |
| `Text Box: Cursor Moved` | Occurs when the user moves the cursor in a Text Box node. |
| `Text Box: Editing Finished` | Occurs when a Text Box node leaves the editing state after the user modified the text content. |
| `Text Box: Editing Started` | Occurs when the user makes the first modification to the text in a Text Box node that is in the editing state. |
| `Text Box: Entered Editing State` | Occurs when a Text Box node enters the editing state. |
| `Text Box: Input Method Action` | Occurs when the user taps the action button on their on-screen keyboard while editing the text in a Text Box node. |
| `Text Box: Input Method Available` | Occurs when an input method becomes available to a Text Box node. For example, an on-screen keyboard becomes available when it appears on the screen. |
| `Text Box: Input Method Unavailable` | Occurs when the input method that is composing text in a Text Box node becomes unavailable. For example, an on-screen keyboard becomes unavailable when the user hides it. |
| `Text Box: Left Editing State` | Occurs when a Text Box node leaves the editing state |
| `Text Box: Selection Changed` | Occurs when the user changes the text selection in a Text Box node. |
| `Text Box: Selection Cleared` | Occurs when the user clears or resets the text selection in a Text Box node. |
| `Text Box: Selection Started` | Occurs when the user starts selecting text in a Text Box node. |
| `Text Box: Text Changed` | Occurs when the user changes the text in a Text Box node. |
| `Text Box: Text Composition Canceled` | Occurs: * When the text composition in a Text Box node is canceled by Input Method that is in text composition state. * When a trigger executes the Text Box: Cancel Text Composition action. |
| `Toggle Button Group: Toggled` | Occurs when the toggle state of a Toggle Button node in a Toggle Button Group node changes. |
| `Toggle Button: State Toggled` | Occurs when the toggle state of a Toggle Button changes. |
| `Toggle Button: Toggled Off` | Occurs when a Toggle Button is toggled off. |
| `Toggle Button: Toggled On` | Occurs when a Toggle Button is toggled on. |
