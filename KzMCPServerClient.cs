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
                var msgId = JsonUtils.GetInt(req, "id");

                await FireLog($"📩 收到请求: {method}");

                string responseJson;

                if (method == "initialize")
                {
                    responseJson = JsonUtils.Serialize(new
                    {
                        jsonrpc = "2.0",
                        id = msgId,
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
                        id = msgId,
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
                        id = msgId,
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
                        try
                        {
                            string resultText = ExecuteToolAsync(toolName, arguments).GetAwaiter().GetResult();
                            var resp = JsonUtils.Serialize(new
                            {
                                jsonrpc = "2.0",
                                id = msgId,
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
                                id = msgId,
                                result = new
                                {
                                    isError = true,
                                    content = new[] { new { type = "text", text = $"❌ {ex.Message}" } }
                                }
                            });
                            try { await SendAsync(wsRef, errResp, ctRef); } catch { }
                            await FireLog($"❌ {toolName} 失败: {ex.Message}");
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
                    name = "kz_invoke",
                    description = "通用反射调用：在任意 Kanzi Studio API 对象上调用任意方法",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "调用目标。格式: @studio | @project | @projectItem | @obj1/@obj2 | /节点路径" },
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
                    name = "kz_localization",
                    description = "编辑本地化表。action：set(增/改) | delete(删) | get(查单条) | list(查全部) | backup(手动备份到工程目录) | rebuild(重建删行/改字段) | restore(从最新备份恢复)。⚠️ delete/rebuild 会删旧表重建（实现删除行/改字段），删表前【强制自动备份】到工程目录 {工程名}.localization.backup.json；若表不存在或为空则拒绝删除/重建且不覆盖备份。所有操作基于 resourceName(Key)。",
                    inputSchema = new {
                        type = "object",
                        properties = new {
                            target = new { type = "string", description = "LocalizationTable 对象引用或路径（如 /Localization/Localization 或 @project / @objN）；restore 不需要（从备份恢复）" },
                            action = new { type = "string", description = "操作：set(增/改) | delete(删，走重建删行+自动备份) | get(查单条) | list(查全部) | backup(手动备份) | rebuild(重建删行/改字段) | restore(从最新备份恢复，需该工程有备份)" },
                            rows = new {
                                type = "array",
                                items = new {
                                    type = "object",
                                    properties = new {
                                        resourceName = new { type = "string", description = "资源名/键（唯一标识，Key）" },
                                        defaultText = new { type = "string", description = "默认文本" },
                                        translations = new { type = "object", description = "语言→翻译映射，如 { \"en\": \"...\", \"zh-CHS\": \"...\" }" }
                                    },
                                    required = new[] { "resourceName" }
                                },
                                description = "set/rebuild 需要：完整行数组（增/改都传完整行，插件内部合并）"
                            },
                            keys = new {
                                type = "array",
                                items = new { type = "string" },
                                description = "delete/rebuild 需要：resourceName(Key) 数组，只传 key（要删的行）"
                            },
                            key = new { type = "string", description = "get 需要：单个 resourceName(Key)，只传 key" }
                        },
                        required = new[] { "target", "action" }
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
                    string projectName = _bridge.GetProjectName();
                    return Task.FromResult($"✅ 连接正常\n   工程: {projectName}");

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

                case "kz_localization":
                    string locTarget = JsonUtils.GetStr(args, "target");
                    string locAction = JsonUtils.GetStr(args, "action");
                    var locRows = JsonUtils.GetList(args, "rows");
                    var locKeys = JsonUtils.GetList(args, "keys");
                    string locKey = JsonUtils.GetStr(args, "key");
                    FireLogSync($"  ↳ kz_localization: 目标={locTarget} action={locAction} rows={locRows.Count} keys={locKeys.Count}");
                    var locResult = _bridge.LocalizationEdit(locTarget, locAction, locRows, locKeys, locKey);
                    return Task.FromResult(FormatInvokeResult(locResult));

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
