---
name: kanzi-properties-resource
description: Kanzi 资源属性参考（Brush/Texture/Material/Style/Animation/Timeline），官方文档抓取
---

# Kanzi 资源属性大全

## 使用说明

本 skill 是 Kanzi 4.1.0 官方属性参考（来源：`docs.kanzi.com → Reference → Node and resource reference`，2026-10-14 批量抓取）。

- **特有属性**：该节点直接声明的属性（官方「X properties」表）。

- **继承属性**：从基类继承的公共属性，见文末表。

- 查某节点完整属性 = 该节点特有属性 + 继承属性表。

---

## Brush（`brush-reference`）

**属性 14 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Brush Color` | Color for brush. Set alpha to 0 to disable brush. |
| `Brush Horizontal Tiling` | Horizontal Tiling for the brush. Affects the scale of texture coordinates. |
| `Brush Modulate Color` | Modulation color for brush. Effects brush rendering that needs color modulation. |
| `Brush Texture` | Texture for brush. |
| `Brush Type` | The type of the brush. |
| `Brush Vertical Tiling` | Vertical Tiling for the brush. Affects the scale of texture coordinates. |
| `Custom Asset Thumbnail` | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Export in Asset Package` | When enabled, this item is exported into asset package if this project is saved as one. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Material` | Material used when drawing with the brush |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Texture（`texture-reference`）

**属性 8 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Custom Asset Thumbnail` | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Export in Asset Package` | When enabled, this item is exported into asset package if this project is saved as one. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Native Deployment Target` | Sets the memory in which to store this texture on your target device. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Single Texture（`single-texture-reference`）

**属性 8 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Custom Asset Thumbnail` | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Export in Asset Package` | When enabled, this item is exported into asset package if this project is saved as one. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Native Deployment Target` | Sets the memory in which to store this texture on your target device. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Cubemap Texture（`cubemap-texture-reference`）

**属性 8 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Custom Asset Thumbnail` | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Export in Asset Package` | When enabled, this item is exported into asset package if this project is saved as one. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Native Deployment Target` | Sets the memory in which to store this texture on your target device. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Volume Texture（`volume-texture-reference`）

**属性 8 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Custom Asset Thumbnail` | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Export in Asset Package` | When enabled, this item is exported into asset package if this project is saved as one. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Native Deployment Target` | Sets the memory in which to store this texture on your target device. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Render Target Texture（`render-target-texture-reference`）

**属性 8 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Custom Asset Thumbnail` | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Export in Asset Package` | When enabled, this item is exported into asset package if this project is saved as one. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Native Deployment Target` | Sets the memory in which to store this texture on your target device. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Image File（`image-file-reference`）

**属性 4 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Clamp Pixels` | Clamp the color channel maximum to the value. For SDR images the effective range is 0 to 1, and for HDR images any non-negative value. If one color channel needs to be clamped, then all other color ch… |
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Native Pixel Format` | Sets the native image format to use when exporting this image to the kzb file. Make sure that the graphics backend of your target device supports the format. |

---

## Material（`material-reference`）

**属性 145 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `A` | Tonemapping parameter A. |
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
| `B` | Tonemapping parameter B. |
| `Base Color Factor` | Sets the base color for the material. |
| `Base Color Texture` | Sets the texture that contains the base color for the material. Use the Base Color Factor property to filter the value from this texture. |
| `Blend Intensity` | Controls the intensity of materials that are blended on top of an existing color. Attached property enables overriding of the blend intensity of the used materials at render pass or object node level. |
| `Blend Mode` | Sets how to combine the color and alpha values of pixels in one layer or image with those in the underlying layer or image. |
| `Bloom Intensity` | Bloom intensity for the material. |
| `Bloom Intensity Texture` | Sets the bloom intensity texture. |
| `Bloom Radius` | Bloom radius for the material. |
| `Blur Direction` | Sets the direction for the blur. |
| `Blur Radius` | Blur radius for the material. |
| `BRDF Lookup Table` | Gets the Bidirectional Reflectance Distribution Function (BRDF) lookup table for the material. The BRDF table is a texture that contains precomputed information about how light reflects off a material… |
| `Brush Color` | Color for brush. Set alpha to 0 to disable brush. |
| `Brush Horizontal Tiling` | Horizontal Tiling for the brush. Affects the scale of texture coordinates. |
| `Brush Modulate Color` | Modulation color for brush. Effects brush rendering that needs color modulation. |
| `Brush Texture` | Texture for brush. |
| `Brush Vertical Tiling` | Vertical Tiling for the brush. Affects the scale of texture coordinates. |
| `C` | Tonemapping parameter C. |
| `Calculated Offset` | Reports the current relative offset of an item in the Grid List Box in proportional range [0, 1]. |
| `Calculated Offset` | Reports the current offset of an item in a Trajectory Layout in the proportional range [0, 1]. |
| `Clear Coat Normal Scale` | Sets the clear coat normal scale for the material. Use the scale to set the intensity of the Clear Coat Normal Texture. |
| `Clear Coat Normal Texture` | Sets the texture that contains a clear coat normal map for the material. Use the Clear Coat Normal Scale property to scale the texture value. |
| `Clear Coat Roughness Factor` | Sets the roughness of the outer clear coat layer for the material: 0 represents a smooth, glossy surface, and 1 represents a rough, diffuse surface. |
| `Clear Coat Roughness Texture` | Sets the texture that contains a clear coat roughness map for the material. Kanzi reads the roughness from the Green channel of the texture. Use the Clear Coat Roughness Factor property to scale the r… |
| `Clear Coat Strength Factor` | Sets the clear coat strength for the material: 0 represents a material with no clear coat, and 1 represents a full strength clear coat. |
| `Clear Coat Strength Texture` | Sets the texture that contains a clear coat strength map for the material. Kanzi reads the strength from the Red channel of the texture. Use the Clear Coat Strength Factor property to scale the streng… |
| `Cubemap Texture` | Sets the cubemap texture you want the Blit render pass to blit. |
| `Custom Asset Thumbnail` | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `D` | Tonemapping parameter D. |
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
| `Directional Light` | Directional light settings |
| `Directional Light View Projection` | The premultiplied projection view matrix of a directional light. |
| `Directional Shadow Map` | Depth map used to calculate directional shadows. |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Dithering Amount` | Sets the chromatic aberration dithering amount. |
| `E` | Tonemapping parameter E. |
| `Emissive Color` | Sets the color of the light that is emitted from the material surface. |
| `Emissive Factor` | Sets the color of the light that is emitted from the material. Use the Intensity (I) property field to adjust the brightness of the light. This color affects the local material rendering, but the ligh… |
| `Emissive Texture` | Sets the texture that contains the light emitted from the material. Use the Emissive Factor property to scale the value from this texture. |
| `Environment Ambient Factor` | Sets the strength of the cubemap texture to use for ambient environment light. Use the Environment Ambient Texture property to set the cubemap texture. The ambient environment light affects diffuse li… |
| `Environment Ambient Texture` | Sets the cubemap to use for the ambient environment light for the material. This cubemap affects the diffuse lighting during image based lighting. Use the Environment Ambient Factor property to set th… |
| `Environment Reflection Factor` | Sets the strength of the cubemap texture to use for specular environment light. Use the Environment Reflection Texture property to set the cubemap texture. The specular environment light affects refle… |
| `Environment Reflection Texture` | Sets the cubemap to use for the specular environment light for the material. This cubemap affects reflective lighting during image based lighting. Use the Environment Reflection Factor property to set… |
| `Export in Asset Package` | When enabled, this item is exported into asset package if this project is saved as one. |
| `Exposure` | Sets the exposure compensation for the material. The exposure compensation emulates camera exposure by controlling the total amount of light rendered. Use a negative value to darken the rendered image… |
| `F` | Tonemapping parameter F. |
| `Font Color` | Sets the color of the text in a 3D text node. |
| `Global Ambient Color` | Sets the color that is multiplied automatically with the Ambient property of the materials in the scene. Use the Intensity (I) property field to adjust the exposure of the color. |
| `Glossiness Factor` | Sets the glossiness of the material: 0 represents a rough, diffuse surface, and 1 represents a smooth, glossy surface. |
| `Glossiness Texture` | Sets the texture that contains a glossiness map for the material. Kanzi reads the glossiness from the Alpha channel of this texture. Use the Glossiness Factor property to scale the glossiness from thi… |
| `Grading Color Highlight` | Sets the color grading highlight color. |
| `Grading Color Midtone` | Sets the color grading midtone color. |
| `Grading Color Shadow` | Sets the color grading shadow color. |
| `Grading Highlight Range` | Sets the luminance range where the highlight color is applied. |
| `Grading Hue Saturation Value` | Sets the HSV adjustment for the input color. |
| `Grading Shadow Range` | Sets the luminance range where the shadow color is applied. |
| `Inner Distance` | Sets the distnace range where the vignette color transition starts. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Mask Texture` | Sets the texture that masks another texture or color. |
| `Mask Texture Offset` | Sets an offset for mask in materials. |
| `Mask Texture Tiling` | Determines the number of times a mask is presented in a material |
| `Metallic Factor` | Sets the metalness of the material: 0 represents a non-metallic or dielectric object, and 1 represents a metallic object. |
| `Metallic Texture` | Sets the texture that contains a metallic map for the material. Kanzi reads the metalness from the Blue channel of this texture. Use the Metallic Factor property to scale the value from this texture. |
| `Morph Data Texture` | Data texture to use for storing morph data when the are are too many targets to use regular attribute channels. |
| `Morphing` | Add morph weights to Model3D to enable Morphing. |
| `Normal Scale` | Sets the normal scale for the material. Use the scale to set the intensity of the Normal Texture. |
| `Normal Texture` | Sets the texture that contains a normal map for the material. Use the Normal Scale property to scale the texture value. |
| `Occlusion Render Strength` | Sets the SSAO strength for the material. Use the strength to set the intensity of the SSAO Texture. |
| `Occlusion Render Texture` | Sets the texture that contains a SSAO computed for the scene. Use the Occlusion Render Strength property to scale the strength of the SSAO. |
| `Occlusion Strength` | Sets the occlusion strength for the material. Use the strength to set the intensity of the Occlusion Texture. |
| `Occlusion Texture` | Sets the texture that contains an occlusion map for the material. Use the Occlusion Strength property to scale the occlusion from the texture. |
| `Opacity` | Opacity of the node. |
| `Outer Color` | Sets the vignette color. |
| `Outer Distance` | Sets the distnace range where the vignette color transition ends. |
| `Planar Reflection Map` | Rendered texture for planar reflections. |
| `Planar Reflection View Projection` | The premultiplied projection view matrix for planar reflections. |
| `Point Light` | Point light settings |
| `Point Shadow Map` | Depth cubemap used to calculate point light shadows. |
| `Point Shadow Near Far` | Sets the near &amp; far values used for point shadow calculations. |
| `Roughness Factor` | Sets the roughness of the material: 0 represents a smooth, glossy surface, and 1 represents a rough, diffuse surface. |
| `Roughness Texture` | Sets the texture that contains a roughness map for the material. Kanzi reads the roughness from the Green channel of the texture. Use the Roughness Factor property to scale the roughness from this tex… |
| `Show Material Debug Objects` | When enabled, Kanzi Studio does not hide material debug objects. |
| `Specular Anti-Aliasing Strength` | Sets the strength of the specular anti-aliasing effect. Higher value results in blurrier specular highlights. For no specular anti-aliasing, set the value to 0. For full specular anti-aliasing, set th… |
| `Specular Anti-Aliasing Threshold` | Sets the upper limit for the amount of specular anti-aliasing effect to apply. The default value is 0.18. |
| `Specular Color` | Sets the color of the specular reflection. |
| `Specular Color Factor` | Sets the specular color for the material. |
| `Specular Color Texture` | Sets the texture that contains the specular color for the material. Use the Specular Color Factor property to filter the value from this texture. |
| `Specular Exponent` | Sets the size of the specular highlight. |
| `Spot Light` | Spot light settings |
| `Spot Light View Projection` | The premultiplied projection view matrix of a spot light. |
| `Spot Shadow Map` | Depth map used to calculate spot shadows. |
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
| `Tone Map Linear Scale` | Sets the scale for the linear tonemap option for the material. When linear tonemapping is used, Kanzi divides all output color by the value of this property. |
| `Transition Phase` | The phase of the transition. For example, use for pixel-based effects. |
| `Use Intensity Texture` | Enable or disable the use of the Bloom Intensity texture property. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |
| `Visible Amount in Parent` | Sets the amount the node is inside its parent. Use the value of this property in shaders to implement fades. Calculated by the parent node. |
| `White Scale` | Sets the value that will be tonemapped to pure white. |

---

## Material Type（`material-type-reference`）

**属性 5 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Shader Version` | Sets the OpenGL ES version in the shaders of this material type. The value of this property overrides the #version directive in the shader source files. When you do not set this property, Kanzi uses t… |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Style（`style-reference`）

**属性 4 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Animation（`animation-reference`）

**属性 5 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Animation Clip（`animation-clip-reference`）

**属性 5 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Timeline Entry（`timeline-entry-reference`）

**属性 1 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |

---

## Timeline Sequence（`timeline-sequence-reference`）

**属性 5 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Mesh（`mesh-reference`）

**属性 5 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Plane Mesh（`plane-mesh-reference`）

**属性 5 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Material` | Use this material to override the materials defined in the clusters of the mesh. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

## Primitive Meshes（`primitive-meshes-reference`）

**属性 253 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `2D to 3D Projection Scale` | Sets the scale factor to project pixels to 3D size. When scale is 1, then the size of one pixel is one 3D space unit. |
| `A` | Tonemapping parameter A. |
| `Active Activity Index` | The index of the active Activity in the Data-Driven Exclusive Activity Host. After instantiating all Activity from a Data Source, this property refers to the only currently active Activity in this Dat… |
| `Activity Source` | The data object that provides the data for this Activity node. |
| `Activity Status` | Sets the possible states of the Activity when its Activity Host activates or deactivates that Activity. |
| `Activity Template` | If set, the Data-Driven Exclusive Activity Host uses this prefab for Activity nodes that it creates. |
| `Actual Layout Depth` | The calculated size of the node in depth direction when used in a layout. |
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
| `Calculated Offset` | Reports the current offset of an item in a Trajectory Layout in the proportional range [0, 1]. |
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
| `Constraint In World Coordinates` | Specifies if the object constraining is done in world coordinates (when false, done in local coordinates). |
| `Constraint Orientation` | Makes an object node where the property is attached to obtain orientation from target object |
| `Constraint Position` | Makes an object node where the property is attached to obtain position from target object |
| `Controller Property` | Sets the property type that the Exclusive Activity Host node uses to switch between its child Activity nodes. |
| `Cubemap Texture` | Sets the cubemap texture you want the Blit render pass to blit. |
| `Custom Asset Thumbnail` | When enabled, the asset will have selected image as thumbnail instead of the generated one. |
| `Cyclic Focus Navigation` | Sets whether the focus chain navigation within the focus scope is cyclic. When you enable this property: * When the user navigates in the forward direction and the focus reaches the last focusable UI … |
| `D` | Tonemapping parameter D. |
| `Data Context` | Source of data for this node and its descendants |
| `Data Source Controller Property Path` | Sets the path in the Data Source object of an Exclusive Activity Host node to a Data Object item that the Exclusive Activity Host node uses as the Controller Property. |
| `Depth Alignment` | The alignment in depth direction the node should use when it resides under a layout. |
| `Depth Margin` | Sets the depth distance between this node and other nodes that are adjacent to this node in a layout. To access the Depth Margin property fields in a binding, use: * X for the Back property field * Y … |
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
| `Drawn as Bounding Box` | When enabled the object is drawn its solid bounding box. |
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
| `Face to Camera Mode` | Sets how to rotate the 3D node towards a camera: * Disabled does not make the node turn to the camera. * Look at rotates the node along all axes to turn to the camera. * Billboarding keeps the node pe… |
| `Face to Camera Target Camera` | Sets the camera towards which the 3D node turns when you set the Face to Camera Mode property. The default is the Scene default camera. |
| `Final Transformation` | The combined location, orientation and scale of the node and its ancestor nodes. Automatically calculated by the system. |
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
| `Fractional Character Width` | Sets whether Kanzi uses fractional or rounded character widths to lay out text. In most cases fractional widths provide the best result. However, with small font sizes, fractional widths can cause the… |
| `Frustum Cull Margin` | The margin of the frustum cull radius of the node. For example, set the margin when a vertex shader modifies the geometry of the node. To use this property, enable the Frustum Culling property in the … |
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
| `Hit Testable Container` | When enabled, Kanzi uses the layout bounds as geometry for hit testing. |
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
| `Layout Depth` | The size of the node in depth direction when used in a layout. Overrides the default bounds of the item. |
| `Layout Height` | The height of the node when used in a layout. Overrides the default bounds of the item. |
| `Layout Transformation` | The location, orientation and scale of the node relative to its parent node. Layout Transformation affects the layout. If you do not want to affect the layout, use Render Transformation. |
| `Layout Width` | The width of the node when used in a layout. Overrides the default bounds of the item. |
| `Left Image` | The image to use in the center-left. |
| `Line Spacing` | Sets the line spacing in multiples of the normal line height of the selected font. |
| `Look At` | Makes a node to always face the node set in this property. |
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
| `Override Material` | Sets the override material to use to render the content of the 2D prefab in the Viewport 3D node. In the Viewport 3D node, bind a texture property of the override material to the Viewport3D.PrefabText… |
| `Planar Reflection Map` | Rendered texture for planar reflections. |
| `Planar Reflection View Projection` | The premultiplied projection view matrix for planar reflections. |
| `Point Shadow Map` | Depth cubemap used to calculate point light shadows. |
| `Point Shadow Near Far` | Sets the near &amp; far values used for point shadow calculations. |
| `Prefab Template` | Sets the 2D prefab whose content the Viewport 3D node renders in 3D space. |
| `Previous Final Transformation` | Final transformation (world matrix) from the previous frame, used for velocity buffer calculation. |
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
| `Tags` | List of tags attached to the item |
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
| `Value` | The current value. To update this property with a binding, use a to-source or two-way binding. |
| `Vertical Alignment` | The alignment in vertical direction the node should use when it resides under a layout. |
| `Vertical Margin` | Sets the vertical space between this node and other nodes that are adjacent to this node in a layout. To access the Vertical Margin property fields in a binding, use: * X for the Bottom property field… |
| `Vertical Padding` | Sets the padding spaces between the content and the top and bottom boundaries of the Text node. |
| `Visible` | When disabled, Kanzi does not render the node. |
| `Visible Amount in Parent` | Sets the amount the node is inside its parent. Use the value of this property in shaders to implement fades. Calculated by the parent node. |
| `White Scale` | Sets the value that will be tonemapped to pure white. |
| `Word Wrap` | Sets whether to break long lines into multiple lines to make the text fit within the boundaries of the Text Block node. |

---

## 3D Asset Source File（`3d-asset-source-file-reference`）

**属性 1 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
