# kz_mcp_http 喂狗方案（完整版）

> 目标：根治「用久了所有动作都超时，只能手动重启 kz_mcp_http 才好」的僵死问题。
> 核心思路：**用「喂狗 + 返回执行状态」取代「固定 300s 干等」**，秒级发现链路坏并自愈，同时不误杀合法长动作。

---

## 一、问题回顾（为什么现在会僵死）

### 1.1 现在的超时机制（有缺陷）

`kz_mcp_http.UserManager.relay_request`（约 line 186）目前是：

```python
try:
    return await asyncio.wait_for(fut, timeout=300.0)
except asyncio.TimeoutError:
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32000, "message": "MCP 请求超时"}}
finally:
    async with self._lock:
        self.pending.pop(req_id, None)
```

**缺陷：超时只清理本请求的 pending，不判定链路好坏。** 当链路（client连接↔relay转发↔插件server连接）坏了：

- 请求转发出去后**永远没有响应回来**
- 每个请求**默默挂满 300s** 才算超时
- copilot 以为超时重试，重试又挂 300s → **所有动作都做不了**
- 只有手动重启 kz_mcp_http 重建 client 连接清掉 pending 才恢复
- **这印证根因在「连接侧」，不在 Kanzi 服务端**（重启 Kanzi 没用，重启 kz_mcp_http 就好）

### 1.2 僵死原因分类

| 类型 | 表现 | 喂狗能否覆盖 |
|---|---|---|
| A. 连接/转发坏（僵尸链路） | 转发出去了，响应永不回来，WS 层看似还通 | ✅ 能 |
| B. 执行中插件重连 | 请求执行一半，插件 relplay 断连重连，响应竞态丢失 | ⚠️ 部分（靠 fail pending + copilot 重试兜住） |
| C. 动作真跑 >300s | 插件在处理，只是慢 | ✅ 不误杀（喂狗返回"执行中"则继续等） |
| D. 请求 id 匹配/并发重复 | 并发请求 id 重复，pending 被覆盖 | ❌ 喂狗不管，需单独修（本方案附带） |

---

## 二、方案核心设计

### 2.1 一句话

**喂狗定期并行探活插件，插件返回「执行状态」；http 据此动态决定某个 pending 请求是该「继续等」还是「立刻失败让 copilot 重试」，链路坏时秒级 fail pending + 自动重连。**

### 2.2 喂狗承载三个职责

1. **探链路连通**：喂狗响应能回来 ⇒ 链路（http client ↔ relay ↔ 插件）是通的
2. **探插件执行状态**：返回 `busy` + `active_request_id`，告诉 http 插件此刻在不在处理某请求
3. **动态判定超时**：不再用固定 300s 干等，改用执行状态判断

### 2.3 超时判定新规则（取代 300s 干等）

对每个 pending 请求，周期性用喂狗状态判断：

- **插件 `busy=true` 且 `active_request_id == 我的请求`** → 正在执行 → **继续等**（不超时不误杀，哪怕动作真跑 500s）
- **插件 `busy=false`（空闲），但我的请求还没收到响应** → 链路通但请求丢了/没到插件（竞态/转发丢）→ **立即 fail 该 pending** → 返回超时错误 → **copilot 重试（必成，因为链路是好的）**
- **喂狗连续 N 次无响应** → 链路坏（僵尸/转发死）→ **fail 所有 pending** + **自动重连**

> **300s 固定超时可以移除**（被上面动态判定取代）。可选保留一个极大兜底（如 1800s）防极端情况，但不再用 300s 干等。

---

## 三、分文件修改清单

### 文件 1：Kanzi 插件侧（server，v13 插件）——**最重要前置**

**确保 `kz_health` 并行独立处理：**
- `kz_health` **不进入请求处理队列、不等待其它动作完成**，收到立即返回
- 即使有长动作在跑，`kz_health` 也秒回 ⇒ 喂狗真实反映链路 + 执行状态

**`kz_health` 返回值扩展为：**

```json
{
  "ok": true,
  "busy": true/false,          // 插件当前是否正在执行某个 MCP 请求
  "active_request_id": "xxx"   // 正在执行的请求 id（无则 null）
}
```

- 插件需要维护一个「当前正在执行的请求 id」标记（执行开始置位、完成清空）
- 让 http 能把「插件在执行 id=X」与「我 pending 里的 X 在跑」精确对应

### 文件 2：`kz_mcp_http.py`

**新增喂狗任务（每用户独立）：**
- **每用户一条连接 + 一个喂狗任务**（随该用户连接生命周期建/停，`UserManager.connections[username]` 每用户独立）
- 定期（如每 5~10s，可配）向**该用户自己的** client 连接发 `kz_health`
- 连续 N 次（如 3 次）无响应 ⇒ 判定**该用户**链路坏

**`relay_request` 超时判定（插件串行 → 一个全局喂狗状态即可，无需每请求独立探测）：**
- 移除固定 300s 干等
- 每个 pending 用喂狗返回的 `active_request_id` **直接判定**：
  - `active_id == 我的请求` → 插件在执行 → **继续等**（不误杀长动作）
  - `active_id == 别的请求` → 插件在跑前面的（本请求**排队中**）→ **继续等**
  - `active_id == null`（空闲）且我**没收到响应** → **请求丢了** → **立刻 fail**（不等）
- 前提：**确认插件串行队列执行**（一个时刻只跑一个请求）——请在插件侧确认/保证；若插件并发才需要每请求独立探测（当前大概率串行，故不需要 `REQ_CHECK_INTERVAL`）

**链路坏处理（喂狗判定）：**
- **只 fail 该用户自己的 pending**（不跨用户误伤）
- 触发该用户 `_connect_loop` **自动重连**

**多用户隔离（方案补丁）：**
- 每个用户在 relay 用**独立通道名**（relay 按用户名分区槽位：`ws://IP:58080/<用户名>`）
- 用户 A 链路坏只影响 A，B 完全不受影响（A 的喂狗/fail/重连不触碰 B）
- 防「一个用户的 client 连接把另一用户踢掉」（配置错误共用同一通道时的槽位互踢 `old.close()`）
- 上线时校验：每个用户通道名唯一、与对应 Kanzi server 通道一致

**附带修复：请求 id 匹配**
- `handle_mcp_response` 里 id 严格化（int/str 一致转换），防并发请求 id 重复覆盖 pending

### 文件 3：`relay_multi.py`（⛔ 暂不修改）

**本阶段不修改 `relay_multi.py`，实际部署也不动此文件。**

- （原计划内容，本阶段搁置）连接切换主动通知：`_handle_server` / `_handle_client` 替换连接时广播「链接已切换」事件，让 http 收到即触发 fail pending 评估
- 上述增强**留待下一阶段**；当前喂狗 + 插件并行 + http 动态判定已能覆盖主要僵死原因，relay 无需改动

---

## 四、效果对照

| 场景 | 现在的行为 | 喂狗方案的行为 |
|---|---|---|
| 链路坏（僵尸） | 每个请求干等 300s，所有动作做不了，只能手动重启 | 喂狗秒级发现 → fail 所有 pending + 自动重连 → 秒级自愈 |
| 竞态偶发丢响应 | 挂 300s 才超时，copilot 重试 | 喂狗发现插件空闲+没收到 → 秒级 fail → copilot 重试（链路好必成） |
| 动作真跑 >300s | 被 300s 误杀，copilot 死循环重试 | 喂狗返回执行中 → 继续等 → **跑完正常返回，不误杀** |
| 并发 id 重复 | pending 覆盖，响应错配 | 修复 id 严格匹配，不再漏配 |

---

## 五、配置项（新增，放 `kz_mcp_http.py` 顶部或 users.json）

```python
HEARTBEAT_INTERVAL    = 5      # 喂狗间隔（秒）
HEARTBEAT_MAX_FAILS   = 3      # 连续 N 次无响应判定链路坏
# 注：REQ_CHECK_INTERVAL（每请求独立探测）【不需要】——插件串行时全局喂狗
#     active_request_id 即可判定每个 pending，无需每请求单独探测
MAX_REQUEST_WAIT      = 1800   # 兜底上限（可选，极长动作保护，默认不再用 300s 干等）
```

---

## 六、实施步骤

1. **改插件**：`kz_health` 并行独立 + 返回 `{busy, active_request_id}` + 维护执行中请求标记
2. **改 kz_mcp_http.py**：喂狗任务 + 动态超时判定 + fail pending + 自动重连 + id 匹配修复
3. **⛔ relay_multi.py 本阶段不修改**（实际也不动此文件；连接切换主动通知留待下一阶段）
4. **语法校验**：`python3 -m py_compile` 改动的两个文件（kz_mcp_http.py + 插件侧）
5. **同步 NAS + 部署**：Kanzi 插件加载新版 → 验证 kz_health 并行秒回 → 长动作不被误杀 → 拔线测试链路坏自愈
6. **交付**：完整修改文件发老隋

---

## 七、验证方法（部署后）

- **正常**：喂狗返回 busy=false，请求秒回
- **长动作**：发一个耗时 >300s 的动作 → 喂狗持续返回 busy=true、active_request_id=该请求 → 不超时，跑完正常收
- **链路坏**：拔掉 Kanzi 插件连接（或 kill relay 转发）→ 喂狗连续 3 次无响应 → 观察 pending 被秒级 fail + kz_mcp_http 自动重连 → copilot 重试即恢复，**无需手动重启**
- **竞态**：执行中强制插件重连 → 观察 http 收到切换通知/喂狗发现空闲 → 悬空请求秒级 fail → copilot 重试成功

---

_方案完。_
