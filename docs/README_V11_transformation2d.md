# V11：Transformation2D 标识符（@transformation2d:）

> 基于 **V10_modify_animation** 派生，V10 一行未动（存档于 `../v10_modify_animation`，同目录 `v10_modify_animation.tar.gz`）。
> v11 在 bridge 的值解析器 `ResolveSingleArg` 追加 `@transformation2d:` 标识符，用于给
> **只接受 `Transformation2D` 类型值**的属性（典型如 `Node2D.RenderTransformation`）设值。

## 解决的问题

之前 bridge 的前缀解析只有 `@vector:` / `@vector3d:` / `@quaternion:` / `@color:` 等，
**没有 Transformation2D 类型**。而 Kanzi 2D 节点的位置/缩放/旋转是由 `Node2D.RenderTransformation`
（类型 = `Rightware.Kanzi.Studio.PluginInterface.Transformation2D`）编码的，它的实际值是
`scaleX; scaleY; rotation; translateX; translateY` 这种 5 段分号分隔格式（如 `1; 1; 0; 0; 115`）。

- 用 `@vector:` 设这个属性会把一个 **2 分量 Vector** 存进 Transformation2D 属性 → 读回 null（类型错）。
- 用裸字符串 `"1; 1; 0; 0; 115"` 也会存成字符串 → 读回 null。

V11 新增 `@transformation2d:` 前缀，构造**真正的 Transformation2D 对象**再交给属性 setter，读回正常。

## 值格式

```
@transformation2d:scaleX,scaleY,rotation,tx,ty
```

逗号分隔 5 个 double，与属性原始值 `scaleX; scaleY; rotation; tx; ty` 对应（注意用逗号，不是分号）。

例：
- 位置 X:0, Y:115，无缩放无旋转 → `@transformation2d:1,1,0,0,115`
- 位置 X:1310, Y:92，无缩放无旋转 → `@transformation2d:1,1,0,1310,92`

典型设值（给节点设 RenderTransformation）：
```
kz_set_property { path: ".../Title_Layout", property: "Node2D.RenderTransformation",
                  value: "@transformation2d:1,1,0,0,115" }
```

## 构造函数签名（反编译确认，非脑补）

用 `dnfile` 反编译 `PluginInterface.dll`（KzMCPPlugin/references/ 下的 354KB 副本）确认
`Rightware.Kanzi.Studio.PluginInterface.Transformation2D` 只有两个构造函数：

```
Transformation2D(System.Windows.Vector scale, double rotation, System.Windows.Vector translation)  // 主构造
Transformation2D(System.Windows.Media.Matrix matrix)                                               // 由 3x3 矩阵构造
```

- 成员确认：`get_Scale/set_Scale`、`get_Rotation/set_Rotation`、`get_Translation/set_Translation`、
  `AsMatrix`、`ToString`。
- 所以我们用 `@transformation2d:scaleX,scaleY,rotation,tx,ty` →
  `new Transformation2D(new Vector(scaleX, scaleY), (double)rotation, new Vector(tx, ty))`。

`ParseTransformation2D` 与既有 `ParseVector` / `ParseQuaternion` 完全同模式：
`ResolveTypeByName` 解析后 `Activator.CreateInstance(type, args)`，全程反射，不引用具体类型。

## 实现点

- 改动只在 `KzMCPReflectionBridge.cs`：
  1. `ResolveSingleArg`（约 1169 行）在 `@quaternion:` 后追加 `@transformation2d:` 分支。
  2. 新增 `ParseTransformation2D(string body)` 辅助方法（约 1356 行，紧邻 `ParseVector` / `ParseVector3D`）。
- v10 完全未动（diff 验证：仅新增行不同）。

## 待老隋在 Studio 机验证点

1. 用 `@transformation2d:1,1,0,0,115` 给 `Title_Layout` 的 `Node2D.RenderTransformation` 设值，
   `get_Translation` 应返回 `Vector(0, 115)`（X=0, Y=115）。
2. 设完读回 `get_Item` 不应再是 null。
3. 属性面板/截图确认节点位置已变（渲染层验证）。
4. 设错（少于 5 个数/非数字）应安全返回 null，不污染工程。
