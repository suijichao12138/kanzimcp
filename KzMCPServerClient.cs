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
