# V10：ModifyAnimation 关键帧编辑（kz_modify_animation）

> 基于 **V9_static_call** 增强，V9 一行未动（存档于 `../v9_static_call`）。
> v10 在 bridge 新增 `ModifyAnimation(...)`，并在 MCP Server 注册 `kz_modify_animation` 工具。

## 解决的问题

V9 之前无法给 Animation Data 加/改/删关键帧（`get_WrappedItem()` 返回的 `Animation` 实现了
`IEnumerable`，被 `WrapResult` 当成集合展开，拿不到内部对象 ref；`AnimationKeyFrame` 又无无参构造）。

V10 在 **bridge 内部**用 `InvokeRaw`（绕开 `WrapResult` 的 IEnumerable 展开）+ 直接反射拿裸对象，
并驱动 Kanzi 命令总线的 `ModifyAnimationCommand` 完成真正的加/改/删关键帧（带撤销）。

## 工具签名

```
kz_modify_animation {
  animation: "路径或@obj引用(AnimationPluginWrapper)",   // 必填
  action:    "add | modify | remove",                    // 必填
  keyframes: [ { time, value, type? } ]                  // 必填，至少1帧
}
```

- `action=add`：加一帧（`ModifiedAnimationData.AddKeyframe`）
- `action=modify`：改帧——**按 time 定位**已有的那一帧，替换 value（`ModifyKeyframe`）
- `action=remove`：删帧——**按 time 定位**已有的那一帧（`RemoveKeyframe`，value 可省）

每帧字段：
- `time`（number，秒）—— 关键帧时间
- `value`（string/number）—— 关键帧值。Kanzi 动画 target 绝大多数是 Number(float)，
  纯数字优先转 float；支持 bool、颜色 `#RRGGBB`/`#AARRGGBB`、字符串兜底。
- `type`（string，可选）—— 插值类型：`LINEAR`（默认）/ `STEP` / `BEZIER` / `HERMITE`

## 返回值

成功返回（含中间对象 @obj 引用，供后续 `kz_invoke` 继续用）：
```json
{
  "ok": true,
  "animation": "...",            // 目标动画名
  "action": "add|modify|remove",
  "executed": true,
  "frameCount": 1,
  "parameterRef": "@obj...",     // ModifyAnimationCommandParameter（可复用继续加帧）
  "modifiedDataRef": "@obj...",  // ModifiedAnimationData（可调 Add/Modify/RemoveKeyframe）
  "commandRecordRef": "@obj...", // ModifyAnimationCommandRecord（可 Undo/Redo）
  "frames": [ { "frameRef": "@obj...", "time": "1", "value": "2", "resultRef": "@obj..." } ]
}
```

## 典型用法

改关键帧：把 1s 时值 2 改成 1
```
kz_modify_animation { animation: "Internal.ctrlState", action: "modify",
                      keyframes: [ { time: 1, value: 1 } ] }
```

加关键帧（批量）：
```
kz_modify_animation { animation: "Internal.ctrlState", action: "add",
                      keyframes: [ { time: 0, value: 0, type: "LINEAR" },
                                   { time: 1, value: 2, type: "LINEAR" },
                                   { time: 2, value: 0, type: "LINEAR" } ] }
```

删关键帧（只按时间删 1s 那一帧）：
```
kz_modify_animation { animation: "Internal.ctrlState", action: "remove",
                      keyframes: [ { time: 1 } ] }
```

## 实现路径（全部运行时反射确认，非脑补）

```
new ModifyAnimationCommandParameter()                    // 无参构造
  → .AddAnimation(内部Animation) → ModifiedAnimationData
  → new AnimationKeyFrame(Single Time, Object Value, InterpolationType, KeyFrameInterpolationData)
       → ModifiedAnimationData.AddKeyframe|ModifyKeyframe|RemoveKeyframe(帧)
→ new ModifyAnimationCommandRecord(param)               // 构造器 (ModifyAnimationCommandParameter)
→ record.Execute()                                       // 真正执行修改（带撤销）
```

- `InterpolationType` 枚举实测 = `STEP / LINEAR / BEZIER / HERMITE`
- `AddKeyframe` / `ModifyKeyframe` / `RemoveKeyframe` 签名均为 `(AnimationKeyFrame)`
- `AnimationKeyFrame` 有完整 setter：`set_Time/set_Value/set_InterpolationType/set_ValueSource/set_IsTemporary/set_SourceProjectItemReference/set_InterpolationData`

## 关键实现点

- **内部 Animation 获取**：目标 wrapper 的 `get_WrappedItem()` 返回内部 `Animation`，
  必须**直接反射**（`GetWrappedItemRaw`）拿裸对象——不能走 `Invoke`（会因 IEnumerable 展开丢 ref）。
- **全反射**：所有 `Rightware.Kanzi.*` 类型一律 `ResolveTypeByName` 字符串解析，不引用具体类型。
- **UI 线程**：沿用 `LocalizationEdit` 模式——public 方法先判 `IsUiThread`，非 UI 线程则
  `Dispatcher.Invoke` 切到 `ModifyAnimationCore`。
- **返回值 @obj 可交互**：中间对象（parameter/modifiedData/record/每帧）都 `RegisterObject` 进对象库，
  返回的 `@objN` 可直接用于后续 `kz_invoke`（这正是"注意返回 @obj 的调用方式"——在 bridge 内部
  正确处理，不丢 ref）。

## 待老隋在 Studio 机验证点

1. `add` / `modify` / `remove` 三个 action 分别跑通
2. `modify` 按 time 定位是否精确命中目标帧
3. 数值型 value 用 float 是否被 Kanzi 接受（若某动画是 int/颜色 target，可能需要 value 走特定类型）
4. Execute 后撤销（Undo）是否生效
