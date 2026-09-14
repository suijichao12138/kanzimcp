using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace KzMCPChatPlugin
{
    /// <summary>
    /// WebSocket MCP Server — 连接 relay 并处理 MCP JSON-RPC 请求
    /// 直接通过 KzMCPReflectionBridge 调用 Kanzi Studio API
    /// 相当于把 server_ws.py 整体搬到 C#
    /// </summary>
    public class KzMCPServerClient : IDisposable
    {
        private readonly KzMCPReflectionBridge _bridge;

        // ★ 执行互斥 + 当前执行状态（http 侧喂狗 kz_health 所需）
        // 插件反射执行本质串行；这里用互斥保证"一个时刻只跑一个请求"，并记录
        // 正在执行的请求 id，让 kz_health 可返回 busy / active_request_id，
        // 供 http 侧动态判定"该等还是秒级 fail"。
        private readonly object _execLock = new object();
        private readonly System.Threading.SemaphoreSlim _execSem = new System.Threading.SemaphoreSlim(1, 1);  // 串行互斥(可await)
        private volatile string _activeRequestId = null;   // 当前正在执行的请求 id(null=空闲)
        private ClientWebSocket _ws;
        private CancellationTokenSource _cts;

        private string _relayUrl;
        private string _channel;
        private bool _running;
        private bool _disposed;

        /// <summary>连接状态变化</summary>
        public event Action<bool> ConnectionChanged;
        /// <summary>日志消息</summary>
        public event Action<string> LogReceived;

        public string Channel => _channel;
        public bool IsConnected => _ws?.State == WebSocketState.Open;

        private const int RECONNECT_DELAY = 3000;
        private const int PING_INTERVAL = 30000;

        public KzMCPServerClient(KzMCPReflectionBridge bridge)
        {
            _bridge = bridge ?? throw new ArgumentNullException(nameof(bridge));
        }

        /// <summary>
        /// 连接到 relay
        /// </summary>
        public async Task ConnectAsync(string relayUrl)
        {
            if (_running) return;

            _relayUrl = relayUrl;

            // 从 URL 提取 channel
            string remain = relayUrl;
            if (relayUrl.StartsWith("ws://")) remain = relayUrl.Substring(5);
            else if (relayUrl.StartsWith("wss://")) remain = relayUrl.Substring(6);
            int slashIdx = remain.IndexOf('/');
            _channel = slashIdx >= 0 ? remain.Substring(slashIdx + 1) : "default";
            if (string.IsNullOrEmpty(_channel)) _channel = "default";

            _running = true;
            _cts = new CancellationTokenSource();
            _ = Task.Run(() => RunConnectLoop(_cts.Token));
        }

        /// <summary>
        /// 断开连接
        /// </summary>
        public async Task DisconnectAsync()
        {
            _running = false;
            _cts?.Cancel();
            var ws = _ws;
            if (ws != null)
            {
                try { await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "", CancellationToken.None); }
                catch { }
                try { ws.Dispose(); }
                catch { }
                _ws = null;
            }
            FireConnectionChanged(false);
        }

        private async Task RunConnectLoop(CancellationToken ct)
        {
            while (_running && !ct.IsCancellationRequested)
            {
                try
                {
                    await FireLog($"正在连接 relay: {_relayUrl}");

                    var ws = new ClientWebSocket();
                    _ws = ws;

                    await ws.ConnectAsync(new Uri(_relayUrl), ct);
                    await FireLog("已连接到 relay");

                    // 发送身份标识
                    await SendAsync(ws, JsonUtils.Serialize(new
                    {
                        role = "server",
                        name = _channel
                    }), ct);

                    FireConnectionChanged(true);
                    await FireLog($"MCP Server 已注册到通道 [{_channel}]");

                    // 接收消息循环
                    var buffer = new byte[1024 * 64];
                    var msgBuffer = new StringBuilder();

                    while (_running && ws.State == WebSocketState.Open && !ct.IsCancellationRequested)
                    {
                        var result = await ws.ReceiveAsync(
                            new ArraySegment<byte>(buffer), ct);

                        if (result.MessageType == WebSocketMessageType.Close)
                            break;

                        msgBuffer.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));

                        if (result.EndOfMessage)
                        {
                            string raw = msgBuffer.ToString();
                            msgBuffer.Clear();
                            await HandleRelayMessage(ws, raw, ct);
                        }
                    }
                }
                catch (OperationCanceledException) { break; }
                catch (WebSocketException ex)
                {
                    await FireLog($"WebSocket 错误: {ex.Message}");
                }
                catch (Exception ex)
                {
                    await FireLog($"连接错误: {ex.Message}");
                }
                finally
                {
                    var prev = _ws;
                    if (prev != null)
                    {
                        try { prev.Dispose(); }
                        catch { }
                        _ws = null;
                    }
                    FireConnectionChanged(false);
                }

                if (_running && !ct.IsCancellationRequested)
                {
                    await FireLog($"将在 {RECONNECT_DELAY / 1000}秒后重连...");
                    try { await Task.Delay(RECONNECT_DELAY, ct); }
                    catch (OperationCanceledException) { break; }
                }
            }
        }

        private async Task HandleRelayMessage(ClientWebSocket ws, string raw, CancellationToken ct)
        {
            try
            {
                // 尝试解析为 JSON-RPC 请求
                var req = JsonUtils.Deserialize(raw);
                if (req == null) return;

                string method = JsonUtils.GetStr(req, "method");
                // ★ 修复: id 必须原样透传(JSON-RPC 允许 id 为整数或字符串)。
                //   原实现用 GetInt 取 id, 字符串 id(如 "one1"/"hb-xxx")解析失败 → 返回默认 -1,
                //   回包 id 恒为 -1 → 按 id 配对的上游(http/多脚本定向回传)永远配不上 → 请求被判丢失。
                object msgIdRaw = JsonUtils.GetRaw(req, "id");
                string msgIdStr = msgIdRaw?.ToString() ?? "";

                await FireLog($"📩 收到请求: {method}");

                string responseJson;

                if (method == "initialize")
                {
                    responseJson = JsonUtils.Serialize(new
                    {
                        jsonrpc = "2.0",
                        id = msgIdRaw,
                        result = new
                        {
                            protocolVersion = "2024-11-05",
                            capabilities = new { },
                            serverInfo = new { name = "KanziStudio MCP", version = "1.0.0" }
                        }
                    });
                    await SendAsync(ws, responseJson, ct);
                }
                else if (method == "notifications/initialized")
                {
                    // 无响应
                }
                else if (method == "ping")
                {
                    responseJson = JsonUtils.Serialize(new
                    {
                        jsonrpc = "2.0",
                        id = msgIdRaw,
                        result = "pong"
                    });
                    await SendAsync(ws, responseJson, ct);
                }
                else if (method == "tools/list")
                {
                    await FireLog($"  ↳ 列出工具 ({GetMcpTools().Count} 个)");
                    responseJson = JsonUtils.Serialize(new
                    {
                        jsonrpc = "2.0",
                        id = msgIdRaw,
                        result = new { tools = GetMcpTools() }
                    });
                    await SendAsync(ws, responseJson, ct);
                }
                else if (method == "tools/call")
                {
                    var @params = JsonUtils.GetDict(req, "params");
                    string toolName = JsonUtils.GetStr(@params, "name");
                    var arguments = JsonUtils.GetDict(@params, "arguments");

                    await FireLog($"▶ 调用工具: {toolName}");

                    // 在后台线程执行，避免阻塞接收循环
                    var wsRef = ws; // 缓存引用避免闭包竞态
                    var ctRef = ct;
                    _ = Task.Run(async () =>
                    {
                        // ★ 探活(kz_health)不排队：直接并行独立执行并返回 busy/active_request_id，
                        //   不占互斥——否则长动作会卡住喂狗、http 侧误判链路坏。
                        //   这就是方案要求的"探测必须并行"。
                        bool isHealth = (toolName == "kz_health");
                        if (!isHealth)
                            await _execSem.WaitAsync();
                        try
                        {
                            if (!isHealth)
                                _activeRequestId = msgIdStr;   // 标记当前执行中的请求
                            string resultText = ExecuteToolAsync(toolName, arguments).GetAwaiter().GetResult();
                            var resp = JsonUtils.Serialize(new
                            {
                                jsonrpc = "2.0",
                                id = msgIdRaw,
                                result = new
                                {
                                    content = new[] { new { type = "text", text = resultText } }
                                }
                            });
                            await SendAsync(wsRef, resp, ctRef);
                            await FireLog($"✅ {toolName} 成功");
                        }
                        catch (Exception ex)
                        {
                            var errResp = JsonUtils.Serialize(new
                            {
                                jsonrpc = "2.0",
                                id = msgIdRaw,
                                result = new
                                {
                                    isError = true,
                                    content = new[] { new { type = "text", text = $"❌ {ex.Message}" } }
                                }
                            });
                            try { await SendAsync(wsRef, errResp, ctRef); } catch { }
                            await FireLog($"❌ {toolName} 失败: {ex.Message}");
                        }
                        finally
                        {
                            // 清执行状态：仅当自己仍是当前执行者时归零(防覆盖新请求)
                            if (!isHealth && _activeRequestId == msgIdStr)
                                _activeRequestId = null;
                            if (!isHealth)
                                _execSem.Release();
                        }
                    });
                    return; // 不阻塞接收循环
                }
            }
            catch (Exception ex)
            {
                await FireLog($"处理消息异常: {ex.Message}");
            }
        }

        #region MCP Tools

        private List<object> GetMcpTools()
        {
            return new List<object>
            {
                new {
                    name = "kz_health",
                    description = "检查 Kanzi Studio 插件连接状态和当前工程信息",
                    inputSchema = new { type = "object", properties = new { } }
                },
                new {
                    name = "kz_list_projects",
                    description = "V12多工程：列出所有已打开的工程（含 ActiveProject/Primary 标记）。不切换当前工程。",
                    inputSchema = new { type = "object", properties = new { } }
                },
                new {
                    name = "kz_select_project",
                    description = "V12多工程：选择指定工程为『当前操作上下文』。之后所有基于 @project 的调用自动作用于该工程，且不切换 Kanzi Studio 的 ActiveProject。传入空字符串/省略则切回 ActiveProject。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            name = new { type = "string", description = "工程名（kz_list_projects 返回的 name）；空/省略=切回 ActiveProject" }
                        },
                        required = new[] { "name" }
                    }
                },
                new {
                    name = "kz_invoke",
                    description = "通用反射调用：在任意 Kanzi Studio API 对象上调用任意方法。target 额外支持 @proj:<工程名>（指定工程对象）和 @proj:<工程名>/<路径>（指定工程内节点/项目项）",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "调用目标。格式: @studio | @project | @projectItem | @obj1/@obj2 | @proj:<工程名>[/路径] | /节点路径" },
                            method = new { type = "string", description = "方法名" },
                            args = new {
                                type = "array",
                                description = "参数列表",
                                items = new { }
                            }
                        },
                        required = new[] { "target", "method" }
                    }
                },
                new {
                    name = "kz_localized_resources",
                    description = "[V13] 读取本地化表里按 locale 使用的资源（字体等 NodeResource）。普通文本读 kz_invoke get_Translations 通道；这里读本地化资源通道（GetLocalizedResourceList）。target 传本地化表路径或 @obj 引用。返回每个资源（含 ref_id 可用于继续 kz_invoke）",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "本地化表位置，如 /Localization/Localization Table 或 @obj 引用" }
                        },
                        required = new[] { "target" }
                    }
                },
                new {
                    name = "kz_ref_properties",
                    description = "列出指定引用的所有可用属性",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "对象引用ID，如 @obj1, @project, @studio" }
                        },
                        required = new[] { "target" }
                    }
                },
                new {
                    name = "kz_ref_methods",
                    description = "列出指定引用的所有可用方法",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "对象引用ID" }
                        },
                        required = new[] { "target" }
                    }
                },
                new {
                    name = "kz_list_refs",
                    description = "列出当前对象引用缓存中的所有引用",
                    inputSchema = new { type = "object", properties = new { } }
                },
                new {
                    name = "kz_create_node",
                    description = "创建 UI 节点",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            parent = new { type = "string", description = "父节点路径" },
                            type = new { type = "string", description = "节点类型，如 Button2D, TextBlock2D" },
                            name = new { type = "string", description = "新节点名称" }
                        },
                        required = new[] { "parent", "type", "name" }
                    }
                },
                new {
                    name = "kz_set_property",
                    description = "设置节点属性值",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            node_path = new { type = "string", description = "节点路径" },
                            property = new { type = "string", description = "属性名" },
                            value = new { type = "string", description = "属性值" }
                        },
                        required = new[] { "node_path", "property", "value" }
                    }
                },
                new {
                    name = "kz_get_property",
                    description = "获取节点属性值",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            node_path = new { type = "string", description = "节点路径" },
                            property = new { type = "string", description = "属性名" }
                        },
                        required = new[] { "node_path", "property" }
                    }
                },
                new {
                    name = "kz_delete_node",
                    description = "删除节点",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            node_path = new { type = "string", description = "节点路径" }
                        },
                        required = new[] { "node_path" }
                    }
                },
                new {
                    name = "kz_get_node_tree",
                    description = "获取工程节点树",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            root = new { type = "string", description = "根节点路径（可选）" }
                        }
                    }
                },
                new {
                    name = "kz_save_project",
                    description = "保存当前工程",
                    inputSchema = new { type = "object", properties = new { } }
                },
                new {
                    name = "kz_loc_entry_list",
                    description = "列出本地化表所有条目（含 type/文本/引用）。不删表不重建，直接枚举。返回每个条目的 key、是否为文本/isText、引用信息，并注册 @obj 可继续 kz_invoke。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "LocalizationTable 对象引用或路径（如 /Localization/Localization 或 @objN）" }
                        },
                        required = new[] { "target" }
                    }
                },
                new {
                    name = "kz_loc_entry_get",
                    description = "按 key(resourceName) 查本地化表单条目。返回 found/key/isText/引用。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "LocalizationTable 对象引用或路径" },
                            key = new { type = "string", description = "resourceName(Key)，只传这一个 key" }
                        },
                        required = new[] { "target", "key" }
                    }
                },
                new {
                    name = "kz_loc_entry_add",
                    description = "新增本地化表单条目，支持一次多行，每行需指定 type（text|font|style|node）。纯 Add/SetOrCreate，不删表，字体/A引用天然保留。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "LocalizationTable 对象引用或路径" },
                            rows = new {
                                type = "array",
                                items = new {
                                    type = "object",
                                    properties = new {
                                        resourceName = new { type = "string", description = "键/resourceName（唯一）" },
                                        type = new { type = "string", description = "条目类型：text(文本,默认) | font(字体) | style | node；非 text 需配 targetRef" },
                                        defaultText = new { type = "string", description = "默认文本（text 类型）" },
                                        targetRef = new { type = "string", description = "font/style/node 类型的资源引用（@objN 或路径）" }
                                    },
                                    required = new[] { "resourceName" }
                                },
                                description = "多行数组"
                            }
                        },
                        required = new[] { "target", "rows" }
                    }
                },
                new {
                    name = "kz_loc_entry_set",
                    description = "修改本地化表单条目，支持一次多行。改 defaultText/type/引用。保留原条目不删改，字体/A引用保留。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "LocalizationTable 对象引用或路径" },
                            rows = new {
                                type = "array",
                                items = new {
                                    type = "object",
                                    properties = new {
                                        resourceName = new { type = "string", description = "键/resourceName" },
                                        type = new { type = "string", description = "条目类型：text|font|style|node" },
                                        defaultText = new { type = "string", description = "默认文本" },
                                        targetRef = new { type = "string", description = "font/style/node 的资源引用" }
                                    },
                                    required = new[] { "resourceName" }
                                },
                                description = "多行数组"
                            }
                        },
                        required = new[] { "target", "rows" }
                    }
                },
                new {
                    name = "kz_loc_entry_delete",
                    description = "删除本地化表单条目，支持一次多行。按 key 单个 Remove，不删整表，其余条目/字体引用保留。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "LocalizationTable 对象引用或路径" },
                            keys = new {
                                type = "array",
                                items = new { type = "string" },
                                description = "要删除的 resourceName(Key) 数组"
                            }
                        },
                        required = new[] { "target", "keys" }
                    }
                },
                new {
                    name = "kz_loc_entry_delete_language",
                    description = "删除本地化表的一个语言（语言列）。等价 GUI 菜单删除 → Delete ProjectItem \".../Localization Table/<lang>\"，对 get_Locales 里匹配 lang 的 Locale 项目项调 Delete()。安全：只删完全匹配的那一个语言；找不到 lang 不删任何内容。target=本地化表路径或 @obj 引用，lang=语言码（缩写，如 de）。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "本地化表路径或 @obj 引用，如 /Localization/Localization Table" },
                            lang = new { type = "string", description = "要删除的语言码（缩写，如 de / fr / zh-CN）" }
                        },
                        required = new[] { "target", "lang" }
                    }
                },
                new {
                    name = "kz_loc_entry_dump",
                    description = "诊断：列出拿到 entry 的内部对象的全部接口方法（含显式接口实现），用于找读翻译/文本的隐藏入口。只读元数据。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "LocalizationTable 对象引用或路径" }
                        },
                        required = new[] { "target" }
                    }
                },
                new {
                    name = "kz_type_probe",
                    description = "只读诊断：按完整类型名探测一个类型是否能加载到 Studio 进程，并列出其构造函数和方法签名（不执行任何逻辑，不污染工程）。用于验证如 CreateLocaleCommandRecord 等命令记录是否可反射直调。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            typeName = new { type = "string", description = "完整类型名，如 Rightware.Kanzi.Tool.Logic.Project.ResourceLocalizationItems.CreateLocaleCommandRecord" }
                        },
                        required = new[] { "typeName" }
                    }
                },
                new {
                    name = "kz_loc_entry_add_language",
                    description = "给本地化表新增一个语言（语言列）。走 CreateLocaleCommandRecord.CreateProjectItem（等价 GUI 菜单\"新建语言\"）。target=本地化表路径或 @obj 引用，lang=新语言码（缩写，如 de）。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "本地化表路径或 @obj 引用，如 /Localization/Localization Table" },
                            lang = new { type = "string", description = "新语言码（缩写，如 de / fr / zh-CN）" }
                        },
                        required = new[] { "target", "lang" }
                    }
                },
                new {
                    name = "kz_loc_row_get",
                    description = "读本地化表单单行（按 key）。返回该行的 DefaultText + Translations（语言→值字典）。对文本行/字体行都适用，验证每种语言能读到什么。走 ExportTranslations。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "LocalizationTable 对象引用或路径" },
                            key = new { type = "string", description = "resourceName/key" }
                        },
                        required = new[] { "target", "key" }
                    }
                },
                new {
                    name = "kz_loc_iface",
                    description = "通用诊断：在 target 的内部对象上调指定接口 getter 或 0 参接口方法（普通反射看不到的显式接口实现）。结果注册引用 + 枚举受限列表。可传 key 作为单参（如 GetEntry(key)）。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "LocalizationTable / Localization 库 / Locale 对象引用或路径" },
                            method = new { type = "string", description = "接口/类方法名，如 get_Locales / get_Entries / GetEntry / get_ResourceReference" },
                            key = new { type = "string", description = "可选；传给方法的单参数（用于 GetEntry(key) 等）" }
                        },
                        required = new[] { "target", "method" }
                    }
                },
                new {
                    name = "kz_capture_screen",
                    description = "截取屏幕区域并返回 PNG 的 base64（用于 Preview/Studio 截图验证）。默认截整屏；可指定 x,y,width,height 区域。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            x = new { type = "integer", description = "左上角x（默认0）" },
                            y = new { type = "integer", description = "左上角y（默认0）" },
                            width = new { type = "integer", description = "宽（<=0则整屏）" },
                            height = new { type = "integer", description = "高（<=0则整屏）" },
                            maxSide = new { type = "integer", description = "缩放最大边（默认800，<=0保持原尺寸）" }
                        },
                        required = new string[0]
                    }
                },
                new {
                    name = "kz_enum_windows",
                    description = "用 user32.EnumWindows 枚举指定 PID 进程的所有顶层窗口（HWND、类名、可见性、矩形）。用于定位被 MCP 面板遮挡/不在前台的 Preview、Studio 窗口，Process.MainWindowHandle 在这种环境下常为0，EnumWindows 才可靠。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            pid = new { type = "integer", description = "目标进程 PID（如 KanziPreview 的 PID）" }
                        },
                        required = new string[] { "pid" }
                    }
                },
                new {
                    name = "kz_enum_all_windows",
                    description = "枚举系统中所有顶层窗口（无需 pid），每个带 pid/title/className/visible/坐标。用于直接找 Preview 或任意被拽出窗口的标题，不需要先拿进程 PID。",
                    inputSchema = new {
                        type = "object",
                        properties = new { }
                    }
                },
                new {
                    name = "kz_print_window",
                    description = "用 user32.PrintWindow 把指定 HWND 的窗口内容离屏渲染成 PNG(base64)。即使窗口被 MCP 面板遮挡/不在前台也能截到（不走屏幕像素）。hwnd 用 kz_enum_windows 拿到。对 OpenGL/DirectX 渲染(如 NVOpenGLPbuffer)可能抓不到 GPU 内容。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            hwnd = new { type = "integer", description = "窗口句柄（kz_enum_windows 返回的 hwnd）" },
                            maxSide = new { type = "integer", description = "缩放最大边（默认0不缩放）" }
                        },
                        required = new string[] { "hwnd" }
                    }
                },
                new {
                    name = "kz_screenshot_preview",
                    description = "一键截图 Preview；获取不到 Preview 窗口则截 Studio 主窗。不截主屏幕。内部自动判断：对 Studio 进程可见窗口 PrintWindow 试截，命中 Title/className 含 Preview 或内容最大的窗口优先。需传 Studio 进程 PID。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            pid = new { type = "integer", description = "KanziStudio 进程 PID" },
                            maxSide = new { type = "integer", description = "缩放最大边（默认1200）" }
                        },
                        required = new string[] { "pid" }
                    }
                },
                new {
                    name = "kz_modify_animation",
                    description = "给 Animation Data 加/改/删关键帧（驱动 Kanzi ModifyAnimationCommand，带撤销）。action：add(加帧) | modify(改帧，按 time 定位) | remove(删帧，按 time 定位)。keyframes 数组每项 { time(秒), value(动画属性值，数值/布尔/颜色均可), type?(LINEAR/STEP/BEZIER/HERMITE，默认LINEAR) }。animation 传目标动画路径或 @obj 引用。执行后返回中间对象 @obj 引用(parameterRef/modifiedDataRef/commandRecordRef/frames[].frameRef)，可继续用 kz_invoke 操作。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            animation = new { type = "string", description = "目标 Animation Data 路径或 @obj 引用（AnimationPluginWrapper）" },
                            action = new { type = "string", description = "操作：add(加帧) | modify(改帧) | remove(删帧)" },
                            keyframes = new {
                                type = "array",
                                items = new {
                                    type = "object",
                                    properties = new {
                                        time = new { type = "number", description = "关键帧时间（秒）" },
                                        value = new { type = "string", description = "关键帧值（数值/布尔/颜色#RRGGBB）" },
                                        type = new { type = "string", description = "插值类型：LINEAR/STEP/BEZIER/HERMITE（默认LINEAR）" }
                                    },
                                    required = new[] { "time", "value" }
                                },
                                description = "关键帧数组（[ { time, value, type? } ]）"
                            }
                        },
                        required = new[] { "animation", "action", "keyframes" }
                    }
                }
            };
        }

        private Task<string> ExecuteToolAsync(string toolName, Dictionary<string, object> args)
        {
            // 刷新工程引用
            _bridge.Refresh();

            switch (toolName)
            {
                case "kz_health":
                    string projectName;
                    try { projectName = _bridge.GetProjectName(); }
                    catch { projectName = "(取工程名被长任务暂占)"; }
                    string cur = _activeRequestId;
                    bool busy = cur != null;
                    return Task.FromResult(
                        $"✅ 连接正常\n" +
                        $"  ok: true\n" +
                        $"  busy: {busy}\n" +
                        $"  active_request_id: {(cur ?? "null")}\n" +
                        $"  工程: {projectName}");

                case "kz_list_projects":
                    try
                    {
                        _bridge.RefreshProjects();
                        var projs = _bridge.ListProjects();
                        if (projs == null || projs.Length == 0)
                            return Task.FromResult($"当前没有已打开的工程。当前 ActiveProject: {_bridge.GetProjectName()}");
                        var sb = new System.Text.StringBuilder("已打开的工程:\n");
                        foreach (var p in projs)
                        {
                            sb.Append("  · ")
                              .Append(p.TryGetValue("name", out var nn) ? nn : "?")
                              .Append("  → @proj:").Append(p.TryGetValue("name", out var n2) ? n2 : "?");
                            if (p.TryGetValue("isActive", out var ia) && ia is bool bAct && bAct) sb.Append("  [Active]");
                            if (p.TryGetValue("isPrimary", out var ip) && ip is bool bPri && bPri) sb.Append("  [Primary]");
                            sb.Append("\n");
                        }
                        sb.Append("当前 ActiveProject: ").Append(_bridge.GetProjectName());
                        return Task.FromResult(sb.ToString());
                    }
                    catch (Exception ex)
                    {
                        return Task.FromResult($"❌ kz_list_projects 失败: {ex.Message}");
                    }

                case "kz_select_project":
                    try
                    {
                        string selName = JsonUtils.GetStr(args, "name");
                        FireLogSync($"  ↳ kz_select_project: '{selName}'");
                        string msg = _bridge.SelectProject(selName);
                        return Task.FromResult($"✅ {msg}（之后 @project 相关操作作用于该工程；ActiveProject 不变）");
                    }
                    catch (Exception ex)
                    {
                        return Task.FromResult($"❌ kz_select_project 失败: {ex.Message}");
                    }

                case "kz_invoke":
                    string target = JsonUtils.GetStr(args, "target");
                    string method = JsonUtils.GetStr(args, "method");
                    var rawArgs = JsonUtils.GetList(args, "args");
                    FireLogSync($"  ↳ kz_invoke: {target}.{method}({string.Join(", ", rawArgs)})");
                    // 线程策略：状态机相关的创建/设置调用走非UI线程提速，其余反射仍走UI线程
                    bool offUi = _bridge.ShouldRunOffUiThread(target, method, rawArgs.ToArray());
                    var invokeResult = _bridge.Invoke(target, method, rawArgs.ToArray(), offUi);
                    FireLogSync($"  ↳ 线程策略: {(offUi ? "非UI线程" : "UI线程")}");
                    return Task.FromResult(FormatInvokeResult(invokeResult));

                case "kz_localized_resources":
                    string lrTarget = JsonUtils.GetStr(args, "target");
                    FireLogSync($"  ↳ kz_localized_resources: {lrTarget}");
                    var lrResult = _bridge.GetLocalizedResources(lrTarget);
                    long lrCount = 0;
                    try
                    {
                        if (lrResult is IDictionary<string, object> lrd && lrd.TryGetValue("count", out var lrc))
                            lrCount = System.Convert.ToInt64(lrc);
                    }
                    catch { }
                    FireLogSync($"  ↳ 本地化资源数: {lrCount}");
                    return Task.FromResult(FormatInvokeResult(lrResult));

                case "kz_get_return_type":
                    string rtTarget = JsonUtils.GetStr(args, "target");
                    string rtMethod = JsonUtils.GetStr(args, "method");
                    var rtRawArgs = JsonUtils.GetList(args, "args");
                    FireLogSync($"  ↳ kz_get_return_type: {rtTarget}.{rtMethod}({string.Join(", ", rtRawArgs)})");
                    var rtResult = _bridge.GetRawReturnType(rtTarget, rtMethod, rtRawArgs.ToArray());
                    return Task.FromResult($"✅ 返回类型: {rtResult}");

                case "kz_get_raw_ref":
                    string grTarget = JsonUtils.GetStr(args, "target");
                    string grMethod = JsonUtils.GetStr(args, "method");
                    var grRawArgs = JsonUtils.GetList(args, "args");
                    FireLogSync($"  ↳ kz_get_raw_ref: {grTarget}.{grMethod}({string.Join(", ", grRawArgs)})");
                    var grResult = _bridge.GetRawRef(grTarget, grMethod, grRawArgs.ToArray());
                    return Task.FromResult($"✅ 裸对象: {grResult}");

                case "kz_ref_properties":
                    string refTarget = JsonUtils.GetStr(args, "target");
                    var refProps = _bridge.GetRefProperties(refTarget);
                    var refPropsDict = refProps as Dictionary<string, object> ?? new Dictionary<string, object>();
                    return Task.FromResult(FormatRefProperties(refPropsDict));

                case "kz_ref_methods":
                    string mTarget = JsonUtils.GetStr(args, "target");
                    var refMethods = _bridge.GetRefMethods(mTarget);
                    var refMethodsDict = refMethods as Dictionary<string, object> ?? new Dictionary<string, object>();
                    return Task.FromResult(FormatRefMethods(refMethodsDict));

                case "kz_list_refs":
                    var refs = _bridge.ListRefs();
                    return Task.FromResult(FormatRefs(refs));

                case "kz_create_node":
                    string parent = JsonUtils.GetStr(args, "parent");
                    string nodeType = JsonUtils.GetStr(args, "type");
                    string nodeName = JsonUtils.GetStr(args, "name");
                    FireLogSync($"  ↳ kz_create_node: 父={parent} 类型={nodeType} 名称={nodeName}");
                    string nodePath = _bridge.CreateNode(parent, nodeType, nodeName);
                    return Task.FromResult($"✅ 节点已创建: {nodePath}");

                case "kz_set_property":
                    string nodePath2 = JsonUtils.GetStr(args, "node_path");
                    string prop = JsonUtils.GetStr(args, "property");
                    string val = JsonUtils.GetStr(args, "value");
                    FireLogSync($"  ↳ kz_set_property: {nodePath2}.{prop} = {val}");
                    _bridge.SetProperty(nodePath2, prop, val);
                    return Task.FromResult($"✅ 属性 '{prop}' 已设置");

                case "kz_get_property":
                    string getPath = JsonUtils.GetStr(args, "node_path");
                    string getProp = JsonUtils.GetStr(args, "property");
                    FireLogSync($"  ↳ kz_get_property: {getPath}.{getProp}");
                    var pv = _bridge.GetProperty(getPath, getProp);
                    return Task.FromResult($"'{getProp}' = {pv}");

                case "kz_delete_node":
                    string delPath = JsonUtils.GetStr(args, "node_path");
                    FireLogSync($"  ↳ kz_delete_node: {delPath}");
                    _bridge.DeleteNode(delPath);
                    return Task.FromResult("✅ 节点已删除");

                case "kz_get_node_tree":
                    string root = JsonUtils.GetStr(args, "root");
                    var tree = _bridge.GetNodeTree(string.IsNullOrEmpty(root) ? null : root);
                    return Task.FromResult(FormatNodeTree(tree));

                case "kz_save_project":
                    _bridge.SaveProject();
                    return Task.FromResult("✅ 工程已保存");

                case "kz_loc_entry_list":
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.LocalizationEntries(JsonUtils.GetStr(args, "target"), "list")));

                case "kz_loc_entry_get":
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.LocalizationEntries(JsonUtils.GetStr(args, "target"), "get",
                            null, null, JsonUtils.GetStr(args, "key"))));

                case "kz_loc_entry_add":
                case "kz_loc_entry_set":
                {
                    var rows = JsonUtils.GetList(args, "rows");
                    // 增/改统一走 ResourceDictionaryEntry 路径（老隋要求全 entry，不用 LocalizationTableRow/ImportTranslations）
                    var locOp = toolName == "kz_loc_entry_add" ? "add" : "set";
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.LocalizationEntries(JsonUtils.GetStr(args, "target"), locOp, rows)));
                }

                case "kz_loc_entry_delete":
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.LocalizationEntries(JsonUtils.GetStr(args, "target"), "delete",
                            null, JsonUtils.GetList(args, "keys"))));

                case "kz_loc_entry_delete_language":
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.DeleteLanguage(JsonUtils.GetStr(args, "target"),
                            JsonUtils.GetStr(args, "lang"))));

                case "kz_loc_entry_dump":
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.LocalizationDumpInterfaces(JsonUtils.GetStr(args, "target"))));

                case "kz_loc_row_get":
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.LocalizationRowsRead(JsonUtils.GetStr(args, "target"),
                            JsonUtils.GetStr(args, "key"))));

                case "kz_loc_iface":
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.LocalizationIface(JsonUtils.GetStr(args, "target"),
                            JsonUtils.GetStr(args, "method"),
                            key: JsonUtils.GetStr(args, "key"))));

                case "kz_type_probe":
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.ProbeType(JsonUtils.GetStr(args, "typeName"))));

                case "kz_loc_entry_add_language":
                    return Task.FromResult(FormatInvokeResult(
                        _bridge.AddLanguage(JsonUtils.GetStr(args, "target"),
                            JsonUtils.GetStr(args, "lang"))));

                case "kz_capture_screen":
                    int capX = (int)JsonUtils.GetInt(args, "x", 0);
                    int capY = (int)JsonUtils.GetInt(args, "y", 0);
                    int capW = (int)JsonUtils.GetInt(args, "width", 0);
                    int capH = (int)JsonUtils.GetInt(args, "height", 0);
                    int capMax = (int)JsonUtils.GetInt(args, "maxSide", 800);
                    var capResult = _bridge.CaptureScreenBase64(capX, capY, capW, capH, capMax);
                    return Task.FromResult(FormatInvokeResult(capResult));

                case "kz_enum_windows":
                    int ewPid = (int)JsonUtils.GetInt(args, "pid", 0);
                    FireLogSync($"  ↳ kz_enum_windows: pid={ewPid}");
                    var ewResult = _bridge.EnumProcessWindows(ewPid);
                    return Task.FromResult(FormatInvokeResult(ewResult));

                case "kz_enum_all_windows":
                    FireLogSync("  ↳ kz_enum_all_windows");
                    var eawResult = _bridge.EnumAllWindowsWithTitle();
                    return Task.FromResult(FormatInvokeResult(eawResult));

                case "kz_print_window":
                    long pwHwnd = (long)JsonUtils.GetInt(args, "hwnd", 0);
                    int pwMax = (int)JsonUtils.GetInt(args, "maxSide", 0);
                    FireLogSync($"  ↳ kz_print_window: hwnd={pwHwnd}");
                    var pwResult = _bridge.PrintWindowBase64(pwHwnd, pwMax);
                    return Task.FromResult(FormatInvokeResult(pwResult));

                case "kz_screenshot_preview":
                    int spPid = (int)JsonUtils.GetInt(args, "pid", 0);
                    int spMax = (int)JsonUtils.GetInt(args, "maxSide", 1200);
                    FireLogSync($"  ↳ kz_screenshot_preview: pid={spPid}");
                    var spResult = _bridge.SmartShotBase64(spPid, spMax);
                    return Task.FromResult(FormatInvokeResult(spResult));

                case "kz_modify_animation":
                    string maAnim = JsonUtils.GetStr(args, "animation");
                    string maAction = JsonUtils.GetStr(args, "action");
                    var maKeyframes = JsonUtils.GetList(args, "keyframes");
                    FireLogSync($"  ↳ kz_modify_animation: 目标={maAnim} action={maAction} 帧数={maKeyframes.Count}");
                    var maResult = _bridge.ModifyAnimation(maAnim, maAction, maKeyframes.Count > 0 ? maKeyframes : null);
                    return Task.FromResult(FormatInvokeResult(maResult));

                default:
                    throw new ArgumentException($"未知工具: {toolName}");
            }
        }

        #endregion

        #region 格式化输出

        private string FormatInvokeResult(object r, int indent = 0)
        {
            if (r == null) return "✅ 调用成功（无返回值）";
            if (r is string || r is int || r is long || r is float || r is double || r is bool)
                return $"✅ 结果: {r}";

            if (r is List<object> list)
            {
                var lines = new List<string>();
                foreach (var item in list)
                    lines.Add(FormatInvokeResult(item, indent));
                return string.Join("\n", lines);
            }

            if (r is Dictionary<string, object> dict)
            {
                string prefix = new string(' ', indent * 2);
                var items = new List<string>();
                foreach (var kv in dict)
                {
                    if (kv.Value is Dictionary<string, object> || kv.Value is List<object>)
                    {
                        items.Add($"{prefix}▪ {kv.Key}:");
                        items.Add(FormatInvokeResult(kv.Value, indent + 1));
                    }
                    else
                    {
                        items.Add($"{prefix}▪ {kv.Key} = {kv.Value}");
                    }
                }
                return string.Join("\n", items);
            }

            return $"✅ 结果: {r}";
        }

        private string FormatRefProperties(Dictionary<string, object> props)
        {
            if (props == null || props.Count == 0) return "无属性信息";
            var lines = new List<string>();
            if (props.TryGetValue("type", out var type))
                lines.Add($"类型: {type}");
            if (props.TryGetValue("properties", out var raw) && raw is List<object> list)
            {
                lines.Add("属性:");
                foreach (var item in list)
                {
                    if (item is Dictionary<string, object> p)
                    {
                        string name = JsonUtils.GetStr(p, "name");
                        string ptype = JsonUtils.GetStr(p, "type");
                        string value = JsonUtils.GetStr(p, "value");
                        lines.Add($"  ▪ {name} ({ptype}) = {value}");
                    }
                }
            }
            return string.Join("\n", lines);
        }

        private string FormatRefMethods(Dictionary<string, object> methods)
        {
            if (methods == null || methods.Count == 0) return "无方法信息";
            var lines = new List<string>();
            if (methods.TryGetValue("type", out var type))
                lines.Add($"类型: {type}");
            if (methods.TryGetValue("methods", out var raw) && raw is List<object> list)
            {
                lines.Add("方法:");
                foreach (var item in list)
                    lines.Add($"  ▪ {item}");
            }
            if (methods.TryGetValue("interfaceMethods", out var rawIface) && rawIface is List<object> ifaceList)
            {
                lines.Add("接口方法:");
                foreach (var item in ifaceList)
                    lines.Add($"  ▪ {item}");
            }
            return string.Join("\n", lines);
        }

        private string FormatRefs(Dictionary<string, object> refs)
        {
            if (refs == null || refs.Count == 0)
                return "缓存中无引用。先调用 kz_invoke 创建/获取对象。";
            var lines = new List<string> { "当前对象引用:" };
            foreach (var kv in refs)
            {
                if (kv.Value is Dictionary<string, object> info)
                    lines.Add($"  {kv.Key} → {JsonUtils.GetStr(info, "type")} ({JsonUtils.GetStr(info, "name")})");
                else
                    lines.Add($"  {kv.Key} → {kv.Value}");
            }
            return string.Join("\n", lines);
        }

        private string FormatNodeTree(object tree)
        {
            return FormatTreeInner(tree, 0);
        }

        private string FormatTreeInner(object node, int indent)
        {
            var dict = node as Dictionary<string, object>;
            if (dict == null)
                return node?.ToString() ?? "";

            string prefix = new string(' ', indent * 2);
            string name = JsonUtils.GetStr(dict, "name");
            string type = JsonUtils.GetStr(dict, "type");

            var props = JsonUtils.GetDict(dict, "properties", false);
            string propStr = "";
            if (props != null)
            {
                string text = JsonUtils.GetStr(props, "Text");
                string width = JsonUtils.GetStr(props, "Width");
                string height = JsonUtils.GetStr(props, "Height");
                var parts = new List<string>();
                if (!string.IsNullOrEmpty(text)) parts.Add($"Text={text}");
                if (!string.IsNullOrEmpty(width)) parts.Add($"Width={width}");
                if (!string.IsNullOrEmpty(height)) parts.Add($"Height={height}");
                if (parts.Count > 0) propStr = " " + string.Join(" ", parts.Select(p => $"[{p}]"));
            }

            var lines = new List<string> { $"{prefix}📁 {name} ({type}){propStr}" };

            if (dict.TryGetValue("children", out var rawChildren) && rawChildren is List<object> children)
            {
                foreach (var child in children)
                    lines.Add(FormatTreeInner(child, indent + 1));
            }

            return string.Join("\n", lines);
        }

        #endregion

        #region 工具方法

        private async Task SendAsync(ClientWebSocket ws, string text, CancellationToken ct)
        {
            if (ws.State != WebSocketState.Open) return;
            var bytes = Encoding.UTF8.GetBytes(text);
            await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, ct);
        }

        private void FireConnectionChanged(bool connected)
        {
            ConnectionChanged?.Invoke(connected);
        }

        private async Task FireLog(string msg)
        {
            LogReceived?.Invoke(msg);
            await Task.CompletedTask;
        }

        private void FireLogSync(string msg)
        {
            LogReceived?.Invoke(msg);
        }

        #endregion

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;
            _running = false;
            _cts?.Cancel();
            _ws?.Dispose();
            _ws = null;
        }
    }
}
