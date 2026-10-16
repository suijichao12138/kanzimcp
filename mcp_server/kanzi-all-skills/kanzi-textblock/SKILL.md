---
name: kanzi-textblock
description: Kanzi TextBlock2D 完整配置流程 + 可用属性表。文本节点创建、属性设置。
---

## TextBlock2D 完整配置流程

```python
# 1. 创建节点
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_create_node","arguments":{"parent":"/Screens/Screen/RootPage/Info/warning","type":"TextBlock2D","name":"text"}}})

# 2. 字号
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"AddProperty","args":["FontStyleConcept.Size"]}}})
mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"set_Item","args":["FontStyleConcept.Size", 36]}}})

# 3. 字体（ResourceReference 类型 — 先扫描项目找到资源）
# 步骤3a：扫描项目，找到 Font Families 文件夹
r = mcp({"jsonrpc":"2.0","id":"4","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"get_Children"}}})
# 从 r 中找到 "Font Families" 行的上一个 ref_id，如 @obj47

# 步骤3b：在字体文件夹中找 MiSans-Medium
r = mcp({"jsonrpc":"2.0","id":"5","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj47","method":"get_Children"}}})
# 从 r 中找到 "MiSans-Medium" 行的上一个 ref_id，如 @obj308

# 步骤3c：缓存这个 @obj 引用（发一次 get_Name 确认）
mcp({"jsonrpc":"2.0","id":"6","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj308","method":"get_Name","args":[]}}})
# 返回 MiSans-Medium 即为缓存成功

# 步骤3d：设置 FontFamily
mcp({"jsonrpc":"2.0","id":"7","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"AddProperty","args":["Node.FontFamily"]}}})
mcp({"jsonrpc":"2.0","id":"8","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"Set","args":["Node.FontFamily", "@obj308"]}}})

# 4. 状态机（同样 ResourceReference 类型）
# 步骤4a：在 "State Managers" 文件夹找目标 StateManager
r = mcp({"jsonrpc":"2.0","id":"9","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj47","method":"get_Children"}}})
# 找 "warning State Manager" 的 ref_id，如 @obj107

# 步骤4b：缓存 + 设置
mcp({"jsonrpc":"2.0","id":"10","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj107","method":"get_Name","args":[]}}})
mcp({"jsonrpc":"2.0","id":"11","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"AddProperty","args":["Node.StateManager"]}}})
mcp({"jsonrpc":"2.0","id":"12","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"Set","args":["Node.StateManager", "@obj107"]}}})

# 5. 自定义属性
mcp({"jsonrpc":"2.0","id":"13","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"/Screens/.../text","method":"AddProperty","args":["warning.value"]}}})
```
