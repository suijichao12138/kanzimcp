---
name: kanzi-properties-all
description: Kanzi 全部节点属性合并版（离线数据源）。search_property 的查询库；冷门属性按节点分组查这里。nlp 不加载此文件（大），需要时用工具查询。
---

# Kanzi 全部节点属性大全（合并版）

> 由 7 个分册合并（2d/3d/layout/control/resource/structure/trajectory），官方 4.1.0 抓取。
> **用途**：search_property 的数据源 + 冷门属性人工查证。按 `## 节点名` 分组。

## Text Block 2D（`text-block-2d-reference`）

**特有属性 1 个**；继承属性约 305 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Text` | Sets the text content that the text node renders. To create a line break press Shift+Enter. |


## Image（`image-reference`）

**特有属性 3 个**；继承属性约 303 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Image` | The image to display. |


## Nine Patch Image（`nine-patch-image-reference`）

**特有属性 16 个**；继承属性约 295 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Stretch Type Top` | Sets how to display the top image: * Stretch: Scales the image to fill the space between the top-left and top-right images. * Wrap: When the width of the space between the top-left and top-right image… |
| `Stretch Type Bottom` | Sets how to display the bottom image: * Stretch: Scales the image to fill the space between the bottom-left and bottom-right images. * Wrap: When the width of the space between the bottom-left and bot… |
| `Stretch Type Left` | Sets how to display the left image: * Stretch: Scales the image to fill the space between the top-left and bottom-left images. * Wrap: When the height of the space between the top-left and bottom-left… |
| `Stretch Type Right` | Sets how to display the right image: * Stretch: Scales the image to fill the space between the top-right and bottom-right images. * Wrap: When the height of the space between the top-right and bottom-… |
| `Stretch Type Center` | Sets how to display the center image: * Stretch: Scales the image to fill the width and height of the center of the nine patch image. * Wrap: When the height and width of the center exceed the size of… |
| `Top-Left Image` | The image to use in the top-left corner. |
| `Top Image` | The image to use in the middle of the top row. |
| `Top-Right Image` | The image to use in the top-right corner. |
| `Left Image` | The image to use in the center-left. |
| `Center Image` | The image to use in the center. |
| `Right Image` | The image to use in the center-right. |
| `Bottom-Left Image` | Image to use in the bottom-left corner. |
| `Bottom Image` | The image to use in middle of the bottom row. |
| `Bottom-Right Image` | The image to use in the bottom-right corner. |


## Progressive Rendering Viewport 2D（`progressive-rendering-viewport-2d-reference`）

**特有属性 5 个**；继承属性约 303 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Foreground Hint` | Give a hint of the type of the foreground of 2D nodes: * None renders the background brush after rendering the node. * Translucent renders the background brush before the content of the node. * Occlud… |
| `Timeline` | The animation timeline to play in Progressive Rendering Viewport 2D |
| `Render Pass Prefab` | Sets which render pass prefab will be used to instantiate the render pass tree. |


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


## Mesh（`mesh-reference`）

**特有属性 2 个**；继承属性约 3 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Cluster Materials` | Materials for each of the clusters in the model. |
| `GPU Memory Type` | Determines which kind of GPU memory will be used. |


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
| `Font Color` | ⚠️ 只能给 Text Block 3D 文本设颜色；不能设置 Text Block 2D 的颜色（2D 用 Node2D.ForegroundBrush）。 |
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


## Stack Layout 2D（`stack-layout-2d-reference`）

**特有属性 4 个**；继承属性约 302 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Direction` | Defines the axis along which the stack layout arranges its items. |
| `Reversed` | Defines whether the stack layout arranges its items in reverse order. |


## Flow Layout 2D（`flow-layout-2d-reference`）

**特有属性 2 个**；继承属性约 306 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |


## Trajectory Layout 2D（`trajectory-layout-2d-reference`）

**特有属性 3 个**；继承属性约 309 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Trajectory` | Sets the Trajectory along which this Trajectory Layout node arranges its items. |


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

## Button 3D（`button-3d-reference`）

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


## Slider 3D（`slider-3d-reference`）

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


## Toggle Button 3D（`toggle-button-3d-reference`）

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
| `Index In Group` | Sets the index of the Toggle Button in the Toggle Button Group to which that Toggle Button is registered. If a Toggle Button does not have a local value for this property, it is not registered to the … |
| `Is Checked` | When enabled, the toggle button is in On state. Works only when a toggle button has two states. |


## Toggle Button Group 3D（`toggle-button-group-3d-reference`）

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


## Grid List Box 3D（`grid-list-box-3d-reference`）

**特有属性 13 个**；继承属性约 319 个见文末表；独有消息 0 个

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
| `Focus Scope Type` | Sets the type of the focus scope node: * Group groups focusable nodes. * Fence keeps the focus chain navigation inside the scope and does not allow the focus chain navigation to enter or leave that sc… |
| `Cell Width` | Sets the width of each cell in the Grid List Box. |
| `Cell Height` | Sets the height of each cell in the Grid List Box. |
| `Layout Width` | The width of the node when used in a layout. Overrides the default bounds of the item. |
| `Layout Height` | The height of the node when used in a layout. Overrides the default bounds of the item. |
| `Layout Depth` | The size of the node in depth direction when used in a layout. Overrides the default bounds of the item. |


## List Box Item Container 3D（`list-box-item-container-3d-reference`）

**特有属性 8 个**；继承属性约 332 个见文末表；独有消息 0 个

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
| `Focus Scope Type` | Sets the type of the focus scope node: * Group groups focusable nodes. * Fence keeps the focus chain navigation inside the scope and does not allow the focus chain navigation to enter or leave that sc… |


## Scroll View 2D（`scroll-view-2d-reference`）

**特有属性 3 个**；继承属性约 330 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Focusable` | Indicates whether the node can receive focus. |


## 继承属性表（363 个，本类节点从基类继承的公共属性）

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
| `Direction` | Defines the axis along which the stack layout arranges its items. |
| `Directional Light View Projection` | The premultiplied projection view matrix of a directional light. |
| `Directional Shadow Map` | Depth map used to calculate directional shadows. |
| `Disable KZB Export` | Disables the exporting of the item into KZB. Can be used for, e.g. letting items out from certain profiles. The disabled items are always included in preview. |
| `Disable Render Target Clear Color` | Do not clear render target buffers before rendering into it even if necessary. |
| `Dithering Amount` | Sets the chromatic aberration dithering amount. |
| `Double-Click Enabled` | Whether to install a multi-click manipulator that generates double-click messages. Use this property to enable the double-click gesture for a Button node or List Box items. To enable double-click for … |
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
| `Focus State` | Reports the focus state of a node: * No focus (0) indicates that the node is not focused. For a focus scope node indicates that none of the nodes in the scope have focus. * Logical focus (1) indicates… |
| `Focused` | Indicates whether the node has the key focus. |
| `Font Color` | ⚠️ 只能给 Text Block 3D 文本设颜色；不能设置 Text Block 2D 的颜色（2D 用 Node2D.ForegroundBrush）。 |
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
| `Inner Distance` | Sets the distnace range where the vignette color transition starts. |
| `Invert Content Mask` | Whether to invert the value that Kanzi calculates using content masking. |
| `Invert Mask` | Whether to invert the mask so that transparent areas become opaque and opaque areas become transparent. |
| `Is Down` | Indicates whether the button is pressed and in the down state. |
| `Is Value Changing` | Whether the value is currently changing. |
| `Item Index` | Reports the index of the item in the List Box Item Container. |
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
| `Reversed` | Defines whether the stack layout arranges its items in reverse order. |
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
| `Align To Tangent` | Whether to align the Trajectory List Box 3D items to match the tangent of the trajectory. |
| `Cursor Offset` | Sets the offset of the position to use to select the active item, in proportional range [0,1]. |
| `Dragging Acceleration` | Sets the acceleration of the Trajectory List Box 3D when the user scrolls the Trajectory List Box 3D by dragging the pointer. The higher the value, the quicker the Trajectory List Box 3D reaches its f… |
| `Dragging Drag` | Sets the amount that drag affects the movement of the Trajectory List Box 3D when the user scrolls the Trajectory List Box 3D by dragging the pointer. The lower the value, the higher the drag and the … |
| `Dragging Impulse` | Sets the amount of impulse to generate from the pointer movement when the user scrolls the Trajectory List Box 3D by dragging the pointer. |
| `Item Area Begin` | Sets the proportional offset where the part of the trajectory meant for the fully visible Trajectory List Box 3D items starts. Kanzi uses the values of the Item Area Begin and Item Area End properties… |
| `Item Area End` | Sets the proportional offset where the part of the trajectory meant for the fully visible Trajectory List Box 3D items ends. Kanzi uses the values of the Item Area Begin and Item Area End properties t… |
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
| `Primary Direction` | The direction along which the layout arranges items until the layout limit in that direction is reached. |
| `Secondary Direction` | The direction along which the flow layout arranges lines of the primary direction. |
| `Columns` | Defines the number of columns in a grid layout and how the grid layout distributes the content in columns. |
| `Layout Direction` | The direction in which the items are arranged when you add them to a grid layout. |
| `Rows` | Defines the number of rows in a grid layout and how the grid layout distributes the content in rows. |
| `Items Source` | Data object which provides data sources for list items. |
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
| `Current Button Index` | The index of the Toggle Button that is toggled on in the Toggle Button Group. To update this property with a binding, use a to-source or two-way binding. |
| `Item Count` | Reports the number of items in the List Box, including virtual items. |
| `Depth Padding` | Sets the padding spaces between the content and the front and back boundaries of the Content Layout 3D node. |


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
| `Font Color` | ⚠️ 只能给 Text Block 3D 文本设颜色；不能设置 Text Block 2D 的颜色（2D 用 Node2D.ForegroundBrush）。 |
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


## Style（`style-reference`）

**属性 4 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |


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


## 3D Asset Source File（`3d-asset-source-file-reference`）

**属性 1 个（完整清单）**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |

## Activity 3D（`activity-3d-reference`）

**特有属性 11 个**；继承属性约 329 个见文末表；独有消息 0 个

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
| `Depth Alignment` | The alignment in depth direction the node should use when it resides under a layout. |
| `Horizontal Alignment` | The alignment in horizontal direction the node should use when it resides under a layout. |
| `Vertical Alignment` | The alignment in vertical direction the node should use when it resides under a layout. |
| `Save Last Focused Node` | When this property is enabled, Kanzi remembers the last-focused node in this Activity and sets the key focus to that node when you activate this Activity again. This is the default. When you do not wa… |


## Exclusive Activity Host 3D（`exclusive-activity-host-3d-reference`）

**特有属性 11 个**；继承属性约 327 个见文末表；独有消息 0 个

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
| `Exclusive Activity Host Content` | Describes the content of an Exclusive Activity Host node. An Exclusive Activity Host uses the value of this property to instantiate Activity prefabs and control the status and lifetime of its child Ac… |
| `Depth Alignment` | The alignment in depth direction the node should use when it resides under a layout. |
| `Horizontal Alignment` | The alignment in horizontal direction the node should use when it resides under a layout. |
| `Vertical Alignment` | The alignment in vertical direction the node should use when it resides under a layout. |


## Parallel Activity Host 3D（`parallel-activity-host-3d-reference`）

**特有属性 11 个**；继承属性约 326 个见文末表；独有消息 0 个

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
| `Parallel Activity Host Content` | Describes the content of a Parallel Activity Host. The Parallel Activity Host uses this content to instantiate Activity prefabs and control the status and lifetime of its child Activities. This proper… |
| `Depth Alignment` | The alignment in depth direction the node should use when it resides under a layout. |
| `Horizontal Alignment` | The alignment in horizontal direction the node should use when it resides under a layout. |
| `Vertical Alignment` | The alignment in vertical direction the node should use when it resides under a layout. |


## Data-Driven Exclusive Activity Host 3D（`data-driven-exclusive-activity-host-3d-reference`）

**特有属性 10 个**；继承属性约 328 个见文末表；独有消息 0 个

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
| `Depth Alignment` | The alignment in depth direction the node should use when it resides under a layout. |
| `Horizontal Alignment` | The alignment in horizontal direction the node should use when it resides under a layout. |
| `Vertical Alignment` | The alignment in vertical direction the node should use when it resides under a layout. |


## Page (deprecated)（`page-reference`）

**特有属性 3 个**；继承属性约 271 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Keep Active` | Always activate this Page node when its parent is active. |


## Scene（`scene-reference`）

**特有属性 5 个**；继承属性约 248 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Preview Camera` | Sets the camera through which Kanzi Studio Preview shows the Scene. |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |
| `Hit Testing Camera` | Sets the camera to use to hit test the objects in the Scene. The default is the camera that you set with the Camera property. |
| `Camera` | Sets the camera through which the Kanzi application shows the Scene. |


## Prefab View 3D（`prefab-view-3d-reference`）

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


## Prefab Placeholder 3D（`prefab-placeholder-3d-reference`）

**特有属性 3 个**；继承属性约 252 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Tags` | List of tags attached to the item |
| `Prefab Template` | The prefab template to use for this 3D prefab placeholder |
| `Effective Data Context` | The data context in the current node that is resolved from data context properties and bindings |


## Render Pass（`render-pass-reference`）

**特有属性 127 个**；继承属性约 24 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Acceleration Structure` |  |
| `Acceleration Structure` |  |
| `Addressing Mode` | Sets how Kanzi handles the texture coordinates of the automatically generated composition target textures outside of the [0, 0] - [1, 1] rectangle: * Repeat sets the texture to repeat outside of these… |
| `Alpha To Coverage Enabled` | Sets whether Alpha To Coverage is enabled or not. |
| `Blue Noise` |  |
| `Calculated Camera Matrix` | The camera matrix that the render pass calculates during rendering from the settings of the Camera and passes to the shader. |
| `Calculated Camera Position` | The camera position that the render pass calculates during rendering from the settings of the Camera and passes to the shader. |
| `Calculated Homogeneous View Position` | The homogeneous view position that the render pass calculates during rendering from the settings of the Camera and passes to the shader. |
| `Calculated Projection Matrix` | The projection matrix that the render pass calculates during rendering from the settings of the Camera and passes to the shader. |
| `Calculated Projection Near And Far Planes` | The distances to the camera near and far planes that the render pass calculates during rendering from the settings of the Camera and passes to the shader. |
| `Clear Color 0` | Sets the color that you want the Clear render pass to use to clear the first (default) color buffer. |
| `Clear Color 1` | Sets the color that you want the Clear render pass to use to clear the second color buffer. |
| `Clear Color 2` | Sets the color that you want the Clear render pass to use to clear the third color buffer. |
| `Clear Color 3` | Sets the color that you want the Clear render pass to use to clear the fourth color buffer. |
| `Clear Depth` | Sets the depth that you want the Clear render pass to use to clear the depth buffer. |
| `Clear Stencil` | Sets the clear stencil that you want the Clear render pass to use to clear the stencil buffer. |
| `Color Mipmap Material 0` | Sets the material to use to generate the mipmaps for the first color result texture (Result Texture 0) of a Composition Target Render Pass. To use the default mipmap generation, remove the property or… |
| `Color Mipmap Material 1` | Sets the material to use to generate the mipmaps for the second color result texture (Result Texture 1) of a Composition Target Render Pass. To use the default mipmap generation, remove the property o… |
| `Color Mipmap Material 2` | Sets the material to use to generate the mipmaps for the third color result texture (Result Texture 2) of a Composition Target Render Pass. To use the default mipmap generation, remove the property or… |
| `Color Mipmap Material 3` | Sets the material to use to generate the mipmaps for the fourth color result texture (Result Texture 3) of a Composition Target Render Pass. To use the default mipmap generation, remove the property o… |
| `Color Write Mode` | Sets which channels the render pass writes to the color buffer. To disable the color write, set the property to None. |
| `Composition Target` | Sets the target to which you want to render the result of this Cubemap render pass. |
| `Composition Target 0` | Sets the first color target to which you want to render the result of the child render passes of this render pass. |
| `Composition Target 1` | Sets the second color target to which you want to render the result of the child render passes of this render pass. |
| `Composition Target 2` | Sets the third color target to which you want to render the result of the child render passes of this render pass. |
| `Composition Target 3` | Sets the fourth color target to which you want to render the result of the child render passes of this render pass. |
| `Cubemap Mipmap Material` | Sets the material to use to generate the mipmaps for the color Result Texture of a Cubemap Render Pass. To use the default mipmap generation, remove the property or set it to the default value ‘&lt; N… |
| `Cull Mode` | Sets the culling of the triangle faces in the rendered meshes: * Back renders the triangles whose normal points towards a Camera node. * Front renders the triangles whose normal points away from a Cam… |
| `Current Mipmap Level` | Reports the mipmap level that Kanzi is generating. Use this property in a material that you use to customize how Kanzi generates mipmaps for the composition targets of a Composition Target Render Pass… |
| `Denoiser Mode` | Temporal clamping/rejection mode: 0 - none, 1 - reject using depth min max, 2 - reject using filter |
| `Depth Compare Function` | Sets the comparison function to be used with comparison samplers of the Composition Target render pass’ depth target. |
| `Depth Compare Function` | Sets the comparison function to be used with comparison samplers of the Cubemap render pass’ depth target. |
| `Depth Format` | Sets the format of the automatically created depth render buffer used for the cubemap rendering. If this property is not set, the depth requirement and format are autodetected. |
| `Depth Mipmap Material` | Sets the material to use to generate the mipmaps for the Result Depth Texture of a Composition Target Render Pass. To use the default mipmap generation, remove the property or set it to the default va… |
| `Depth Renderbuffer Format` | Sets the format of the automatically created depth renderbuffers. When you do not set this property, Kanzi sets the depth renderbuffer format automatically to the best available format, in most cases … |
| `Depth Renderbuffer Format` | Sets the format of the automatically created depth renderbuffers. When you do not set this property, Kanzi sets the depth renderbuffer format automatically to the best available format, in most cases … |
| `Depth Target` | Sets the depth target to which you want to render the result of the child render passes of this render pass. |
| `Depth Target` | Sets the target for depth rendering for this Cubemap render pass. |
| `Depth Test Function` | Controls whether the depth test discards a fragment. |
| `Depth Texture` |  |
| `Depth Texture Format` | Sets the format of the automatically created Result Depth Texture. |
| `Depth Write Enabled` | Sets whether the render pass writes to the depth buffer. |
| `Directional Lights` | Use this property to bind the directional light set for rendering. |
| `Engine Factory Name` | The factory name for this composer. Can be used to instantiate composer or render pass from plugin. |
| `Face Update Rate` | Sets the number of cubemap faces to update each frame or at the rate that you set with the Render Pass &gt; Update Rate property. The default value is 6. |
| `Filter` | Sets the filter that the Node List render pass uses to filter or sort a list of incoming nodes. |
| `Filter Mode` | Sets how Kanzi handles accessing the texture samples of the automatically generated composition target: * Nearest takes the color from the nearest sample. * Linear interpolates color from neighboring … |
| `Filter Mode` | Sets how Kanzi handles accessing the texture samples of the automatically generated composition cubemap target: * Nearest takes the color from the nearest sample. * Linear interpolates color from neig… |
| `Frustum Culling` | Enable to disable rendering objects that are not inside the view frustum. Trades GPU rendering time for CPU cull test time. |
| `GBuffer Depth` |  |
| `GBuffer Depth` |  |
| `GBuffer Normal` |  |
| `GBuffer Normal` |  |
| `GBuffer Roughness` |  |
| `Height` | Sets the absolute height for the automatically created composition target textures. If this property is not set, the size is taken from the current composition stack state using the values of the Reso… |
| `History Certainty Threshold` |  |
| `History Depth Texture` |  |
| `Input Viewport Area` | Reports the viewport area relative to the composition space as passed from the parent render pass. To access the Input Viewport Area property fields in a binding, use: * X for the offset along the x a… |
| `Light` |  |
| `Material` | Sets to the Material that you want a Blit render pass to use to blit one or more textures. |
| `Material` | Sets the material that will be used to render all nodes rendered by this DrawObjectsWithMaterialRenderPass. |
| `Material` | Sets the material that will have all other Material Setup render pass properties set to. |
| `Material` | Sets the material that will be used to render all nodes rendered by this RaytracedReflectionRenderPass. |
| `Material` | Sets the material that will be used to render all nodes rendered by this RaytracedShadowRenderPass. |
| `Material Requirements` | Sets the material requirements required from materials selected for rendering. |
| `Minimum Unreprojected Shadow` |  |
| `Mipmap Source Texture` | Reports the texture that contains the render target texture for which Kanzi creates mipmaps. Use this property as the source texture in a material that you use to customize how Kanzi generates mipmaps… |
| `Node List` | Input node list range. Set by a binding from nearest parent node list. |
| `Object Source` | Sets the object source which collects the nodes that you want to use for ray tracing. To render all nodes in a Scene node (Root Object Source), do not set the value for this property. |
| `Object Source` | Sets the object source which collects the nodes that you want to render with this render pass. To render all nodes in a Scene node (Root Object Source), do not set the value for this property. |
| `Output Acceleration Structure` | Built acceleration structure resource. |
| `Output Denoised Shadow Mask` |  |
| `Output Directional Lights` | Kanzi uses this property to allow binding to directional light set. |
| `Output Node List` | Output node list range. Set by Node List render pass as result of filtering the Input Node List. |
| `Output Point Lights` | Kanzi uses this property to allow binding to point light set. |
| `Output Reflection Texture` |  |
| `Output Shadow Mask Texture` |  |
| `Output Spot Lights` | Kanzi uses this property to allow binding to spot light set. |
| `Output Viewport` | Viewport applied by the rendering of the render pass. |
| `Override Camera` | Sets the Camera node that you want to use to render the nodes to the composition cubemap texture. To use the default Camera node in that Scene node, do not set the value for this property. |
| `Pixel Format 0` | Sets on the GPU the target pixel format of the first automatically created composition target texture. |
| `Pixel Format 1` | Sets on the GPU the target pixel format of the second automatically created composition target texture. |
| `Pixel Format 2` | Sets on the GPU the target pixel format of the third automatically created composition target texture. |
| `Pixel Format 3` | Sets on the GPU the target pixel format of the fourth automatically created composition target texture. |
| `Point Lights` | Use this property to bind the point light set for rendering. |
| `Polygon Depth Offset` | Sets the polygon depth offset to apply to the element that the Pipeline State render pass renders: * Derivative multiplier sets the multiplier for the depth change derivative for the fragment. * Const… |
| `Previous Camera Matrix` | Camera matrix from the previous frame, used for velocity buffer calculation. |
| `Previous Projection Matrix` | Projection matrix from the previous frame, used for velocity buffer calculation. |
| `Ray Maximum Trace Distance` |  |
| `Ray Maximum Trace Distance` |  |
| `Raytraced Reflection Maximum Roughness` |  |
| `Reflection Resolution Scale` |  |
| `Reproject Depth Sensitivity` |  |
| `Resolution` | Sets the dimensions of the automatically created composition cubemap target textures. The default value is 64. |
| `Resolution Divisor` | Sets the resolution divisor for the automatically created composition target textures. Together with the Resolution Multiplier property, this property sets the size of the composition target in relati… |
| `Resolution Multiplier` | Sets the resolution multiplier for the automatically created composition target textures. Together with the Resolution Divisor property, this property sets the size of the composition target in relati… |
| `Resolve Immediately` | Whether to resolve multisamples and generate mipmaps for the composition target texture immediately after rendering. By default, the Composition Target render pass resolves multisamples and generates … |
| `Resolve Immediately` | Whether to generate mipmaps for the composition target texture immediately after rendering. By default the Cubemap render pass generates mipmaps immediately. When you continue rendering to the composi… |
| `Result Depth Texture` | The depth texture to which the Composition Target render pass renders its content. |
| `Result Depth Texture` | The cubemap depth texture to which the Cubemap render pass renders its content. |
| `Result Texture` | The result cubemap texture that was rendered to by the Cubemap render pass. |
| `Result Texture 0` | The first color texture to which the Composition Target render pass renders its content. |
| `Result Texture 1` | The second color texture to which the Composition Target render pass renders its content. |
| `Result Texture 2` | The third color texture to which the Composition Target render pass renders its content. |
| `Result Texture 3` | The fourth color texture to which the Composition Target render pass renders its content. |
| `Scissor Area` | Sets the scissor test in the current rendering Viewport 2D node. You can define the scissor in either relative or absolute coordinates, the default is relative. Use the Scissor Mode property to set th… |
| `Scissor Mode` | Sets the scissor test coordinate mode. |
| `Shadow Map Resolution Scale` |  |
| `Shadow Mask` |  |
| `Shadow Projection Fitting Enabled` | Controls how the directional light shadow projection is calculated Enabling this will fit the lights projection to the area covered by the main camera. |
| `Shadow Projection Margin` | Use to add extra margin by scaling the area of the projection |
| `Shadow Projection Range` | Use to limit the projection to a smaller proportional slice (X: near, Y: far) of the main camera frustum. For example if X: 0.0, Y: 0.5 means only the closest half of the camera frustum is guaranteed … |
| `Sorting Order` | Sets the sorting order for render entries. |
| `Spot Lights` | Use this property to bind the spot light set for rendering. |
| `Stencil Fail Operation` | Sets the operation that the render pass performs when the stencil test fails. |
| `Stencil Function Mask` | Sets a mask on which the AND operation is executed with both the reference value and the stored stencil value when the test is done. |
| `Stencil Function Reference Value` | Sets the reference value for the stencil test. |
| `Stencil Pass Depth Fail Operation` | Sets the operation that the render pass performs when the stencil test passes, but the depth test fails. |
| `Stencil Pass Depth Pass Operation` | Sets the operation that the render pass performs when both, the stencil and the depth test, pass. |
| `Stencil Test Function` | Controls whether the stencil test discards a fragment. |
| `Stencil Write Enabled` | Sets whether to enable writing to the stencil buffer. |
| `Update Rate` | Sets the rate at which to render the render pass. To render every frame, set to 1. To render every second frame, set to 2, and so on. To render only once, set to 0. |
| `Update Rate Offset` | Sets a frame offset to the rendering rate that you set with the Update Rate property. This lets you cascade multiple updating render passes to different frames. |
| `Velocity Texture` |  |
| `Viewport Area` | Modifies the current rendering Viewport node. You can define the Viewport in either relative or absolute coordinates, the default is relative. Use the Viewport Mode property to set the coordinate type… |
| `Viewport Mode` | Sets the coordinate type for the Viewport node. |
| `Width` | Sets the absolute width for the automatically created composition target textures. If this property is not set, the size is taken from the current composition stack state using the values of the Resol… |


## Bookmark（`bookmark-reference`）

**特有属性 1 个**；继承属性约 0 个见文末表；独有消息 0 个

### 特有属性

| 属性 | 说明 |
|------|------|
| `Target` | The target of the bookmark |


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

## 官方属性参考（Kanzi 4.1.0，2026-10-14 批量抓取）

轨迹节点用于 Trajectory Layout 中定义对象运动路径，各有少量专属参数。


## Arc Trajectory（`arc-trajectory-reference`）

**属性 4 个**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |


## Ellipse Trajectory（`ellipse-trajectory-reference`）

**属性 4 个**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |


## Rectangle Trajectory（`rectangle-trajectory-reference`）

**属性 4 个**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |


## Spline Trajectory（`spline-trajectory-reference`）

**属性 4 个**

### 属性

| 属性 | 说明 |
|------|------|
| `Description` | Add a description of the purpose of this item. To export descriptions to a plain text file, select File &gt; Export &gt; Export Descriptions. When you export the kzb file, this description is not incl… |
| `Is Used by Code` | Whether or not the application code uses this asset. Used for determining unused assets. |
| `Keep Alive Behavior` | The keep-alive behavior of this resource. Can be used to deny unloading of the resource. |
| `Visibility Across Projects` | Sets whether this resource is available to referencing projects: * Project setting uses the value of the Resource Visibility Across Projects property of the project. * Private makes the resource avail… |

---

# 高频属性分组（含绑定写法，来源 quickref）

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
| `Maximum Value` | `{@../RangeConcept.Maximum}` ✅ | The maximum value that the range allows. |
| `Minimum Value` | `{@../RangeConcept.Minimum}` ✅ | The minimum value that the range allows. |
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
| `Word Wrap` | `{@../TextBlockConcept.WordWrap}` ✅ | Sets whether to break long lines into multiple lines to make the text fit within the boundaries of the Text Block node. |

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
| `Text` | `{@../TextConcept.Text}` ✅ | Sets the text content that the text node renders. To create a line break press Shift+Enter. |
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
| `Font Family` | `{@../Node.FontFamily}` ✅ | The font family used to render the text. |
| `Font Hinting Preference` | `{@../TextConcept.FontHintingPreference}` ✅ | Sets the hinting preference of the font. * No hinting: Render text without hinting the outlines of glyphs. * Native hinting: Prefer native hinter of the font ov… |
| `Font Material` | `{@../TextConcept.FontMaterial}` ✅ | Sets the material whose shader is used to render the text. The shader must use the ContentTexture uniform which is automatically filled with glyph data. |
| `Font Size` | `{@../FontStyleConcept.Size}` ✅ | Sets the size of the font in pixels. |
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
