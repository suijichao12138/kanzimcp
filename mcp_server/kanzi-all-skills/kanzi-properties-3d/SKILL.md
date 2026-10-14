---
name: kanzi-properties-3d
description: Kanzi 全部 3D 节点属性参考（含 Camera/Light/Mesh/Primitive），官方文档抓取，节点特有属性+继承属性
---

# Kanzi 3D 节点属性大全（含相机/灯光/网格）

## 使用说明

本 skill 是 Kanzi 4.1.0 官方属性参考（来源：`docs.kanzi.com → Reference → Node and resource reference`，2026-10-14 批量抓取）。

- **特有属性**：该节点直接声明的属性（官方「X properties」表）。

- **继承属性**：从基类继承的公共属性，见文末表。

- 查某节点完整属性 = 该节点特有属性 + 继承属性表。

---

## Empty Node 3D（`empty-node-3d-reference`）

**特有属性 2 个**；继承属性约 251 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |

---

## Text Block 3D（`text-block-3d-reference`）

**特有属性 8 个**；继承属性约 328 个见文末表；独有消息 0 个

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
| `Text` | Sets the text content that the text node renders. To create a line break press Shift+Enter. |

---

## Text Box 3D（`text-box-3d-reference`）

**特有属性 9 个**；继承属性约 352 个见文末表；独有消息 0 个

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
| `Font Size` | Sets the size of the font in pixels. |
| `Layout Width` | The width of the node when used in a layout. Overrides the default bounds of the item. |

---

## Viewport 3D（`viewport-3d-reference`）

**特有属性 9 个**；继承属性约 327 个见文末表；独有消息 0 个

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
| `Prefab Template` | Sets the 2D prefab whose content the Viewport 3D node renders in 3D space. |
| `Prefab Texture` | The read-only texture to which the Viewport 3D renders the content of the 2D prefab. When you set the Override Material property, you must bind a texture property of that material to this property. |

---

## Camera（`camera-reference`）

**特有属性 27 个**；继承属性约 236 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `2D to 3D Projection Scale` | Sets the scale factor to project pixels to 3D size. When scale is 1, then the size of one pixel is one 3D space unit. |
| `Actual Layout Depth` | The calculated size of the node in depth direction when used in a layout. |
| `Asymmetric FOV` | Sets the field of view of the camera in degrees toward the left, right, up, and down. Angles to the right of the center and upwards of the center are positive. To use this property, set the Projection… |
| `Constraint In World Coordinates` | Specifies if the object constraining is done in world coordinates (when false, done in local coordinates). |
| `Constraint Orientation` | Makes an object node where the property is attached to obtain orientation from target object |
| `Constraint Position` | Makes an object node where the property is attached to obtain position from target object |
| `Depth Alignment` | The alignment in depth direction the node should use when it resides under a layout. |
| `Depth Margin` | Sets the depth distance between this node and other nodes that are adjacent to this node in a layout. To access the Depth Margin property fields in a binding, use: * X for the Back property field * Y … |
| `Drawn as Bounding Box` | When enabled the object is drawn its solid bounding box. |
| `Face to Camera Mode` | Sets how to rotate the 3D node towards a camera: * Disabled does not make the node turn to the camera. * Look at rotates the node along all axes to turn to the camera. * Billboarding keeps the node pe… |
| `Face to Camera Target Camera` | Sets the camera towards which the 3D node turns when you set the Face to Camera Mode property. The default is the Scene default camera. |
| `Final Transformation` | The combined location, orientation and scale of the node and its ancestor nodes. Automatically calculated by the system. |
| `FOV` | Sets the field of view of the camera in degrees. |
| `FOV Type` | Sets the direction of the field of view: * Y FOV sets the field of view along the y axis. This is the default. * X FOV sets the field of view along the x axis. |
| `Frustum Cull Margin` | The margin of the frustum cull radius of the node. For example, set the margin when a vertex shader modifies the geometry of the node. To use this property, enable the Frustum Culling property in the … |
| `Hit Testable Container` | When enabled, Kanzi uses the layout bounds as geometry for hit testing. |
| `Layout Depth` | The size of the node in depth direction when used in a layout. Overrides the default bounds of the item. |
| `Look At` | Makes a node to always face the node set in this property. |
| `Orthogonal Plane Size` | Sets the half width or half height of the view plane of a camera that uses the relative orthogonal coordinate system: * When FOV Type is Y FOV (default value), the height. * When FOV Type is X FOV, th… |
| `Orthogonal Type` | Sets the type of the orthogonal coordinate system: * Relative sets the camera to display an area whose width is scaled with the value of the Orthogonal Plane Size property. This is the default. * Abso… |
| `Override Material` | Sets the override material to use to render the content of the 2D prefab in the Viewport 3D node. In the Viewport 3D node, bind a texture property of the override material to the Viewport3D.PrefabText… |
| `Prefab Template` | Sets the 2D prefab whose content the Viewport 3D node renders in 3D space. |
| `Previous Final Transformation` | Final transformation (world matrix) from the previous frame, used for velocity buffer calculation. |
| `Projection Type` | Sets the projection type of the camera: * Perspective projection shows objects closer to the camera larger than those that are further away. This is the default. * Asymmetric perspective projection le… |
| `Use Viewport Aspect Ratio` | Whether to use the aspect ratio setting from the viewport in render pass. When disabled, you can set the aspect ratio in the camera. |
| `Z Far` | Sets the distance to the far clipping plane of the camera. The camera shows only the objects that are closer than the value set in this property. |
| `Z Near` | Sets the distance to the near clipping plane of the camera. The camera shows only the objects that are farther away than the value set in this property. |

---

## Point Light（`point-light-reference`）

**特有属性 13 个**；继承属性约 257 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Light Type` | A reference to a light property type that defines the type of the light. |
| `Tags` | List of tags attached to the item |
| `Imported from` | The source, the project reference or the 3D asset source file from where the item was imported into this project |
| `Import Source ID` |  |
| `Original Name` | The name of the item in the import source |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Point Light Color` | Sets the color of the Point Light. Use the Intensity (I) property field to adjust the brightness of the light. |
| `Point Light Radius` | Sets the distance at which the intensity of the Point Light reaches zero. For infinite distance, set the property value to 0. |
| `Position` | A hidden property that identifies point light position and related metata. |
| `Point Light Attenuation` | Sets the effect that this Point Light has on nodes that are farther away. Distance of light from the lighted surface is input in a quadratic function, the 3 components are the constant, linear and qua… |
| `Point Shadow Softness` | Sets the softness of the shadows cast by the Point Light. |
| `Point Shadow Bias` | Sets the point shadow bias to reduce sampling artifacts. |

---

## Directional Light（`directional-light-reference`）

**特有属性 12 个**；继承属性约 259 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Light Type` | A reference to a light property type that defines the type of the light. |
| `Tags` | List of tags attached to the item |
| `Imported from` | The source, the project reference or the 3D asset source file from where the item was imported into this project |
| `Import Source ID` |  |
| `Original Name` | The name of the item in the import source |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Directional Light Color` | Sets the color of the Directional Light. Use the Intensity (I) property field to adjust the brightness of the light. |
| `Directional Light Direction` | A hidden property that identifies directional light direction and contains related metadata. |
| `Directional Shadow Bias` | Sets the directional shadow bias to reduce sampling artifacts. |
| `Directional Shadow Softness` | Sets the softness of the shadows cast by the Directional Light. |
| `Layout Transformation` | The location, orientation and scale of the node relative to its parent node. Layout Transformation affects the layout. If you do not want to affect the layout, use Render Transformation. |

---

## Spot Light（`spot-light-reference`）

**特有属性 17 个**；继承属性约 250 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Light Type` | A reference to a light property type that defines the type of the light. |
| `Tags` | List of tags attached to the item |
| `Imported from` | The source, the project reference or the 3D asset source file from where the item was imported into this project |
| `Import Source ID` |  |
| `Original Name` | The name of the item in the import source |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Effective Activity Source` | The data source for this Activity node. |
| `Spot Light Color` | Sets the color of the Spot Light. Use the Intensity (I) property field to adjust the brightness of the light. |
| `Cutoff` | Sets the angle of the light cone in degrees. |
| `Inner Angle` | Sets the inner angle of the light cone in degrees. |
| `Spot Light Radius` | Sets the distance at which the intensity of the Spot Light reaches zero. For infinite distance, set the property value to 0. |
| `Exponent` | Defines how fast a fully lit area at the center of the light cone turns into an unlit area. |
| `Position` | A hidden property that identifies spotlight position and contains related metadata. |
| `Direction` | A hidden property that identifies spotlight direction and contains related metadata. |
| `Spot Light Attenuation` | Sets the effect that this Spot Light has on nodes that are farther away. Distance of light from the lighted surface is input in a quadratic function, the 3 components are the constant, linear and quad… |
| `Spot Shadow Bias` | Sets the spot shadow bias to reduce sampling artifacts. |
| `Spot Shadow Softness` | Sets the softness of the shadows cast by the Spot Light. |

---

## Box（`box-reference`）

**特有属性 11 个**；继承属性约 244 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Mesh Material` | The material to be used for rendering the mesh |
| `GPU Memory Type` | Determines which kind of GPU memory will be used. |
| `Width` | The width of the box (along X axis) |
| `Height` | The height of the box (along Y axis) |
| `Depth` | The depth of the box (along Z axis) |
| `Subdivisions` | Sets the number of subdivisions to apply to the box. With the default value 0, each face of the box consist of one tile. Each subdivision increases the number of tiles in each face quadratically: the … |
| `Generate Tangents` | Generate tangents for this primitive |
| `Generate Normals` | Generate normals for this primitive |
| `Generate Mesh Inside Out` | Whether to flip the windings and normals of the mesh faces. Enable this property when you want to use the mesh as a skybox. |

---

## Plane（`plane-reference`）

**特有属性 12 个**；继承属性约 243 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Mesh Material` | The material to be used for rendering the mesh |
| `GPU Memory Type` | Determines which kind of GPU memory will be used. |
| `Width` | The width of the plane (along X axis) |
| `Height` | The height of the plane (along Y axis) |
| `Subdivisions` | Sets the number of subdivisions to apply to the plane. With the default value 0, the plane consist of one tile. Each subdivision increases the number of tiles in the plane quadratically: the number of… |
| `Invert U` | Whether or not to invert the texture coordinate U. Can be used for mirroring the possible displayed texture vertically. |
| `Invert V` | Whether or not to invert the texture coordinate V. Can be used for mirroring the possible displayed texture horizontally. |
| `Generate Tangents` | Generate tangents for this primitive |
| `Generate Normals` | Generate normals for this primitive |
| `Generate Mesh Inside Out` | Whether to flip the windings and normals of the mesh faces. Enable this property when you want to use the mesh as a skybox. |

---

## Sphere（`sphere-reference`）

**特有属性 10 个**；继承属性约 245 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Mesh Material` | The material to be used for rendering the mesh |
| `GPU Memory Type` | Determines which kind of GPU memory will be used. |
| `Radius` | The radius of the sphere |
| `Sphere Type` | Sets the tessellation type of the sphere: * UV Sphere consists of fans of triangles at the poles and quad faces elsewhere. This is the default. * Icosphere is a subdivided icosahedron that consists of… |
| `Subdivisions` | Sets the number of subdivisions to apply on top of the most basic sphere. Each subdivision increases the number of faces in the sphere. The default is 6. |
| `Generate Tangents` | Generate tangents for this primitive |
| `Generate Normals` | Generate normals for this primitive |
| `Generate Mesh Inside Out` | Whether to flip the windings and normals of the mesh faces. Enable this property when you want to use the mesh as a skybox. |

---

## Plane Mesh（`plane-mesh-reference`）

**特有属性 10 个**；继承属性约 -5 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Mesh Material` | The material to be used for rendering the mesh |
| `GPU Memory Type` | Determines which kind of GPU memory will be used. |
| `Width` | The width of the plane (along X axis) |
| `Height` | The height of the plane (along Y axis) |
| `Subdivisions` | Sets the number of subdivisions to apply to the plane. With the default value 0, the plane consist of one tile. Each subdivision increases the number of tiles in the plane quadratically: the number of… |
| `Invert U` | Whether or not to invert the texture coordinate U. Can be used for mirroring the possible displayed texture vertically. |
| `Invert V` | Whether or not to invert the texture coordinate V. Can be used for mirroring the possible displayed texture horizontally. |
| `Generate Tangents` | Generate tangents for this primitive |
| `Generate Normals` | Generate normals for this primitive |
| `Generate Mesh Inside Out` | Whether to flip the windings and normals of the mesh faces. Enable this property when you want to use the mesh as a skybox. |

---

## Primitive Meshes（`primitive-meshes-reference`）

**特有属性 2 个**；继承属性约 251 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |

---

## Mesh（`mesh-reference`）

**特有属性 2 个**；继承属性约 3 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Cluster Materials` | Materials for each of the clusters in the model. |
| `GPU Memory Type` | Determines which kind of GPU memory will be used. |

---

## 3D Asset Source File（`3d-asset-source-file-reference`）

**特有属性 7 个**；继承属性约 -6 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Curve Tesselation Detail` | The number of subdivisions when importing NURBS curves and tesselating them as Kanzi splines |
| `Import Source Override` | Use this setting in cases where you want to combine the contents of multiple Asset 3D files into a one hierarchy. When importing the existing items are matched based on their import source, therefore … |
| `Import Axis Transform` | Transformation that is applied to all the imported object nodes |
| `Import Scale` | Scaling that is applied to all the imported object nodes |
| `Use Free Camera Interest Position` | When enabled, Kanzi creates a camera target node at the interest position of the Free Camera nodes and adds corresponding look at constraint. This is disabled by default as free cameras are not normal… |
| `Use Camera Aspect Ratio` | Whether to use the Aspect Ratio of the active Camera node to render this asset. By default Kanzi ignores the aspect ratio of the camera. |
| `Tangent Generation Mode` | Sets how Kanzi generates vertex tangents for the meshes in this asset: * Automatic chooses the method based on the material that the mesh uses. * Legacy calculates the tangents using a legacy algorith… |

---

## 继承属性表（312 个，本类节点从基类继承的公共属性）

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
| `Auto Press Interval` | Sets the time in milliseconds after which a button that the user keeps pressed down sends the Button: Click message. While the user holds the button down, the button keeps sending the Button: Click me… |
| `B` | Tonemapping parameter B. |
| `Base Color Factor` | Sets the base color for the material. |
| `Base Color Texture` | Sets the texture that contains the base color for the material. Use the Base Color Factor property to filter the value from this texture. |
| `Baseline` | Font baseline in 3D space units. |
| `Blend Intensity` | Controls the intensity of materials that are blended on top of an existing color. Attached property enables overriding of the blend intensity of the used materials at render pass or object node level. |
| `Blend Mode` | Sets how to combine the color and alpha values of pixels in one layer or image with those in the underlying layer or image. |
| `Bloom Intensity` | Bloom intensity for the material. |
| `Bloom Intensity Texture` | Sets the bloom intensity texture. |
| `Bloom Radius` | Bloom radius for the material. |
| `Blur Direction` | Sets the direction for the blur. |
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
| `Calculated Offset` | Reports the current relative offset of an item in the Grid List Box in proportional range [0, 1]. |
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
| `Dithering Amount` | Sets the chromatic aberration dithering amount. |
| `Down On Hover` | Whether holding a finger on the device screen and moving it over the button transitions the button to the down state. |
| `E` | Tonemapping parameter E. |
| `Effectively Enabled` | Indicates whether this node and its ancestor nodes are enabled. Use this property in state managers and bindings to observe whether a node is effectively enabled. To enable or disable a node, use the … |
| `Emissive Color` | Sets the color of the light that is emitted from the material surface. |
| `Emissive Factor` | Sets the color of the light that is emitted from the material. Use the Intensity (I) property field to adjust the brightness of the light. This color affects the local material rendering, but the ligh… |
| `Emissive Texture` | Sets the texture that contains the light emitted from the material. Use the Emissive Factor property to scale the value from this texture. |
| `Enabled` | Whether this node is enabled. When you disable this property in a node, that node and its descendant nodes in the same overlay focus scope are effectively disabled. Effectively disabling a node remove… |
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
| `Font Style` | Sets the style of the font. |
| `Font Weight` | Sets the weight of the font. |
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
| `Hit Testable` | When enabled, the node can be hit tested. Enabling Hit Testable for a 2D node enables hit testing only for that node. Enabling Hit Testable for a 3D node enables hit testing also for the child nodes. … |
| `Hold Interval` | Sets the amount of time in milliseconds that the user must hold the button pressed down for Kanzi to recognize it as a long-press gesture. To disable the long-press gesture, set to 0. |
| `Horizontal Alignment` | The alignment in horizontal direction the node should use when it resides under a layout. |
| `Horizontal Fit` | Whether to horizontally scale the glyphs to make them fit into the Layout Width of the Text Block. To adjust the scale, use the Horizontal Fit Scale Limits property. |
| `Horizontal Fit Scale Limits` | When the Horizontal Fit property is enabled, sets the minimum and maximum scale for glyphs when the width of text in a Text Block does not match the Layout Width of that Text Block. For example: * Min… |
| `Horizontal Margin` | Sets the horizontal space between this node and other nodes that are adjacent to this node in a layout. To access the Horizontal Margin property fields in a binding, use: * X for the Left property fie… |
| `Horizontal Padding` | Sets the padding spaces between the content and the left and right boundaries of the Text node. |
| `Hover` | Indicates whether a node is the foremost hit testable node under the cursor. |
| `Index In Group` | Sets the index of the Toggle Button in the Toggle Button Group to which that Toggle Button is registered. If a Toggle Button does not have a local value for this property, it is not registered to the … |
| `Inner Distance` | Sets the distnace range where the vignette color transition starts. |
| `Is Down` | Indicates whether the button is pressed and in the down state. |
| `Is Value Changing` | Whether the value is currently changing. |
| `Item Index` | Reports the index of the item in the List Box Item Container. |
| `Layout Height` | The height of the node when used in a layout. Overrides the default bounds of the item. |
| `Left Image` | The image to use in the center-left. |
| `Line Spacing` | Sets the line spacing in multiples of the normal line height of the selected font. |
| `Mask Texture` | Sets the texture that masks another texture or color. |
| `Mask Texture Offset` | Sets an offset for mask in materials. |
| `Mask Texture Tiling` | Determines the number of times a mask is presented in a material |
| `Maximum Distance From Curve` | The distance from the curve where hit testing succeeds. |
| `Maximum Value` | The maximum value that the range allows. |
| `Metallic Factor` | Sets the metalness of the material: 0 represents a non-metallic or dielectric object, and 1 represents a metallic object. |
| `Metallic Texture` | Sets the texture that contains a metallic map for the material. Kanzi reads the metalness from the Blue channel of this texture. Use the Metallic Factor property to scale the value from this texture. |
| `Minimum Value` | The minimum value that the range allows. |
| `Morph Data Texture` | Data texture to use for storing morph data when the are are too many targets to use regular attribute channels. |
| `Morphing` | Add morph weights to Model3D to enable Morphing. |
| `Node.Path` | Full path to the node. |
| `Normal Scale` | Sets the normal scale for the material. Use the scale to set the intensity of the Normal Texture. |
| `Normal Texture` | Sets the texture that contains a normal map for the material. Use the Normal Scale property to scale the texture value. |
| `Normalized Value` | The current value normalized to range [0, 1]. |
| `Occlusion Render Strength` | Sets the SSAO strength for the material. Use the strength to set the intensity of the SSAO Texture. |
| `Occlusion Render Texture` | Sets the texture that contains a SSAO computed for the scene. Use the Occlusion Render Strength property to scale the strength of the SSAO. |
| `Occlusion Strength` | Sets the occlusion strength for the material. Use the strength to set the intensity of the Occlusion Texture. |
| `Occlusion Texture` | Sets the texture that contains an occlusion map for the material. Use the Occlusion Strength property to scale the occlusion from the texture. |
| `Opacity` | Opacity of the node. |
| `Outer Color` | Sets the vignette color. |
| `Outer Distance` | Sets the distnace range where the vignette color transition ends. |
| `Overflow` | Sets the characters that represent the truncated text when the text does not fit in this node. The default value is ‘…’. By default, Kanzi truncates the text at the end. Use the Truncation Direction p… |
| `Planar Reflection Map` | Rendered texture for planar reflections. |
| `Planar Reflection View Projection` | The premultiplied projection view matrix for planar reflections. |
| `Point Shadow Map` | Depth cubemap used to calculate point light shadows. |
| `Point Shadow Near Far` | Sets the near &amp; far values used for point shadow calculations. |
| `Remove Side Bearings` | Whether to position the leftmost characters of left-aligned text and rightmost characters of right-aligned text exactly within the boundary of the text node. |
| `Render Transformation` | The location, orientation, and scale of the node relative to its parent node. Render transformation does not affect the layout of the node. |
| `Right Image` | The image to use in the center-right. |
| `Roughness Factor` | Sets the roughness of the material: 0 represents a smooth, glossy surface, and 1 represents a rough, diffuse surface. |
| `Roughness Texture` | Sets the texture that contains a roughness map for the material. Kanzi reads the roughness from the Green channel of the texture. Use the Roughness Factor property to scale the roughness from this tex… |
| `Row` | The row into which grid layout places the item. |
| `Row Span` | Defines the number of rows an item in a grid layout occupies. |
| `Selected` | Indicates whether the List Box item held by this List Box Item Container is selected. The List Box sets the value of this property. |
| `Selected Item Index` | Sets the index of the item that is currently selected in the List Box node. A List Box node updates this property when the user scrolls that List Box node. To select an item in the List Box node, set … |
| `Show Material Debug Objects` | When enabled, Kanzi Studio does not hide material debug objects. |
| `Side` | The docking side of an item in the dock layout. |
| `Snap Character To Pixel` | Sets whether Kanzi positions characters in 2D rendering to the nearest pixel: * When enabled, text sharpness improves, but some characters can shift a fraction of a pixel. * When disabled, certain com… |
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
| `Value` | The current value. To update this property with a binding, use a to-source or two-way binding. |
| `Vertical Alignment` | The alignment in vertical direction the node should use when it resides under a layout. |
| `Vertical Margin` | Sets the vertical space between this node and other nodes that are adjacent to this node in a layout. To access the Vertical Margin property fields in a binding, use: * X for the Bottom property field… |
| `Vertical Padding` | Sets the padding spaces between the content and the top and bottom boundaries of the Text node. |
| `Visible` | When disabled, Kanzi does not render the node. |
| `Visible Amount in Parent` | Sets the amount the node is inside its parent. Use the value of this property in shaders to implement fades. Calculated by the parent node. |
| `White Scale` | Sets the value that will be tonemapped to pure white. |
| `Word Wrap` | Sets whether to break long lines into multiple lines to make the text fit within the boundaries of the Text Block node. |
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
| `Trajectory` | Sets the trajectory along which the Trajectory List Box 3D arranges its items. |
| `Primary Direction` | The direction along which the layout arranges items until the layout limit in that direction is reached. |
| `Secondary Direction` | The direction along which the flow layout arranges lines of the primary direction. |
| `Columns` | Defines the number of columns in a grid layout and how the grid layout distributes the content in columns. |
| `Layout Direction` | The direction in which the items are arranged when you add them to a grid layout. |
| `Rows` | Defines the number of rows in a grid layout and how the grid layout distributes the content in rows. |
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
| `Start Offset` | Sets the offset of the starting position of the items on the trajectory in the range [0, 1], where 0 is the beginning and 1 is the end of the trajectory. |
| `Composition Background Color` | Sets the color that highlights the text that the user composes using an input method editor (IME). |
| `Composition Font Color` | Sets the color of the text that the user composes using an input method editor (IME). |
| `Selection Background Color` | Sets the color that highlights the selected text. |
| `Selection Font Color` | Sets the color of the selected text. |
| `Composition Text` | Reports the text that the user composes in the Text Box using an input method editor (IME). |
| `Cursor Position` | Sets the position of the cursor in the text shown in the Text Box node. |
| `Cursor Prefab` | Sets the prefab template that defines the appearance of the cursor instead of the default cursor. |
| `Display Text` | Reports the text that the Text Box displays. |
| `Echo Mode` | Sets how the Text Box node shows text: * Normal makes the inserted characters visible. * No Echo makes the inserted characters invisible. * Password makes the inserted character visible for a certain … |
| `Edit Mode` | Sets how the Text Box node enters the editing state: * Automatic makes the Text Box enter the editing state when focused, and leave the editing state when focus is lost. * Triggered requires the user … |
| `Has Selection` | Indicates whether any of the text in the Text Box node is selected. |
| `Hide Text Hint When Editing` | Sets whether to hide the placeholder content, which you set using the Text Hint Prefab property, when the Text Box node is in the editing state. To hide the placeholder content only when the user ente… |
| `Input Method Action` | Sets the label of the user action button on the on-screen keyboard for this Text Box. By default uses the label of the default input method of the operating system. |
| `Input Type` | Sets the input type of the input methods that provide the input layout to let the user enter and edit text of specific type in the Text Box node: * Default for the default input type of the input meth… |
| `Is Composing Text` | Reports the text composition state of the Text Box node. |
| `Is Editing` | Reports the editing state of the Text Box node. |
| `Maximum Text Length` | Sets the maximum length of text that the user can insert in the Text Box node. The unit is a UTF-8 character and the buffer byte length can be greater for multi-byte characters. |
| `Password Echo Timeout` | When the Echo Mode property is set to Password, this property sets the time in milliseconds that an inserted character is visible before being masked. |
| `Password Masking Character` | When the Echo Mode property is set to Password, this property sets the character that masks each character that the application user enters. |
| `Read Only` | Sets whether the Text Box node is editable. When you enable this property, you can set the text only through the Text property and the user cannot edit the text in the Text Box node. |
| `Selection End Cursor Position` | The position of the cursor that marks the end of text selection in the Text Box node. |
| `Selection End Prefab` | Sets the prefab template that defines the appearance of the selection handle at the end of text selection instead of the default handle. |
| `Selection Start Cursor Position` | The position of the cursor that marks the beginning of text selection in the Text Box node. |
| `Selection Start Prefab` | Sets the prefab template that defines the appearance of the selection handle at the beginning of text selection instead of the default handle. |
| `Text Hint Prefab` | Sets the prefab template for showing placeholder content when the Text Box node is empty. |
| `Text Key Navigation Direction` | Sets the text key navigation direction. |
| `Aspect Ratio` | Sets the aspect ratio of the camera. |
| `Light Type Name` | The property type name of the light. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Material` | Use this material to override the materials defined in the clusters of the mesh. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

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
