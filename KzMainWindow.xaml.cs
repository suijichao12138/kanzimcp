using System;
using System.Collections.Generic;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Media = System.Windows.Media;
using Rightware.Kanzi.Studio.PluginInterface;

namespace KzMCPChatPlugin
{
    /// <summary>
    /// 主窗口：上下结构 — 连接栏 / MCP 日志 / 聊天消息 / 输入框
    /// </summary>
    public partial class KzMainWindow : UserControl, PluginWindow, IDisposable
    {
        #pragma warning disable CS0067
        public event EventHandler TitleChanged;
        #pragma warning restore CS0067

        public string Icon => null;
        public string Title => "AI MCP 助手";
        public PluginWindowState SerializeState() => null;

        private readonly KanziStudio _studio;
        private readonly KzMCPReflectionBridge _bridge;
        private readonly KzMCPServerClient _mcpClient;
#pragma warning disable CS0649
        private KzWSClient _wsClient;
#pragma warning restore CS0649
        private bool _chatConnected;

        // 颜色常量（聊天气泡用）
        private static readonly Media.SolidColorBrush
            CUser = new Media.SolidColorBrush(Media.Color.FromRgb(0x3A, 0x3A, 0x3A)),
            CAi = new Media.SolidColorBrush(Media.Color.FromRgb(0x2A, 0x2A, 0x2A)),
            CSys = new Media.SolidColorBrush(Media.Color.FromRgb(0x1E, 0x3A, 0x5F)),
            CThink = new Media.SolidColorBrush(Media.Color.FromRgb(0x33, 0x33, 0x33)),
            CError = new Media.SolidColorBrush(Media.Color.FromRgb(0x5C, 0x1A, 0x1A)),
            W = Media.Brushes.White,
            G = new Media.SolidColorBrush(Media.Color.FromRgb(0xCC, 0xCC, 0xCC));

        public KzMainWindow(KanziStudio studio)
        {
            InitializeComponent();

            _studio = studio;
            _bridge = new KzMCPReflectionBridge(studio);
            _mcpClient = new KzMCPServerClient(_bridge);

            _mcpClient.ConnectionChanged += OnMCPConnectionChanged;
            _mcpClient.LogReceived += OnMCPLog;

            // 从 Kanzi 用户偏好恢复上次的地址(无存量值则用 XAML 默认值)
            LoadSavedUrls();

            // 工程信息
            try
            {
                _bridge.Refresh();
                MCPLog("工程: " + _bridge.GetProjectName());
            }
            catch { }

            MCPLog("AI MCP 助手已加载");
        }

        #region MCP Server 连接

        private void OnMCPConnectionChanged(bool connected)
        {
            Dispatcher.Invoke(() =>
            {
                ConnectMCPBtn.IsEnabled = !connected;
                DisconnectMCPBtn.IsEnabled = connected;
                MCPUrlBox.IsEnabled = !connected;
                MCPStatus.Text = connected ? "●" : "○";
                MCPStatus.Foreground = connected ? new Media.SolidColorBrush(Media.Colors.Lime) : new Media.SolidColorBrush(Media.Colors.Gray);
                MCPLog($"MCP Server {(connected ? "已连接" : "已断开")}");
                if (connected)
                {
                    // 连接成功时覆盖式保存当前地址
                    KzSettings.Set(_studio, KzSettings.KeyMcpUrl, MCPUrlBox.Text.Trim());
                    RefreshProjectInfo();
                }
            });
        }

        /// <summary>插件窗口构造时, 用用户偏好里存过的地址覆盖 XAML 默认值。</summary>
        private void LoadSavedUrls()
        {
            try
            {
                MCPUrlBox.Text = KzSettings.Get(_studio, KzSettings.KeyMcpUrl, KzSettings.DefaultMcpUrl);
                ChatUrlBox.Text = KzSettings.Get(_studio, KzSettings.KeyChatUrl, KzSettings.DefaultChatUrl);
            }
            catch { }
        }

        private void OnMCPLog(string msg)
        {
            Dispatcher.Invoke(() => MCPLog(msg));
        }

        private void MCPLog(string msg)
        {
            MCPLogBox.AppendText($"[{DateTime.Now:HH:mm:ss}] {msg}\n");
            MCPLogBox.ScrollToEnd();
        }

        private void RefreshProjectInfo()
        {
            try
            {
                _bridge.Refresh();
                MCPLog("工程: " + _bridge.GetProjectName());
            }
            catch { }
        }

        private async void ConnectMCP_Click(object sender, RoutedEventArgs e)
        {
            string url = MCPUrlBox.Text.Trim();
            if (string.IsNullOrEmpty(url)) return;
            ConnectMCPBtn.IsEnabled = false;
            MCPLog($"正在连接 MCP Server: {url}");
            await _mcpClient.ConnectAsync(url);
        }

        private async void DisconnectMCP_Click(object sender, RoutedEventArgs e)
        {
            await _mcpClient.DisconnectAsync();
        }

        #endregion

        #region 聊天助手

        private async void ConnectChat_Click(object sender, RoutedEventArgs e)
        {
            string url = ChatUrlBox.Text.Trim();
            if (string.IsNullOrEmpty(url))
            {
                AddSysMsg("请输入中继地址");
                return;
            }
            if (!url.StartsWith("ws://") && !url.StartsWith("wss://"))
            {
                AddSysMsg("地址格式：ws://host:port/用户名");
                return;
            }

            // 解析 host, port, channel
            string remain = url.StartsWith("ws://") ? url.Substring(5) : url.Substring(6);
            string channel = "default";
            int slashIdx = remain.IndexOf('/');
            if (slashIdx >= 0)
            {
                channel = remain.Substring(slashIdx + 1);
                remain = remain.Substring(0, slashIdx);
            }
            int colonIdx = remain.IndexOf(':');
            string host = remain;
            int port = 58080;
            if (colonIdx >= 0)
            {
                host = remain.Substring(0, colonIdx);
                int.TryParse(remain.Substring(colonIdx + 1), out port);
            }

            ChatUrlBox.IsEnabled = false;
            ConnectChatBtn.IsEnabled = false;

            AddSysMsg($"正在连接 {host}:{port}/{channel} ...");

            _wsClient = new KzWSClient(host, port, channel);
            _wsClient.ConnectionChanged += OnChatConnectionChanged;
            _wsClient.MessageReceived += OnChatMessage;
            _wsClient.ErrorOccurred += OnChatError;
            await _wsClient.ConnectAsync();
        }

        private async void DisconnectChat_Click(object sender, RoutedEventArgs e)
        {
            if (_wsClient != null)
                await _wsClient.DisconnectAsync();
        }

        private void OnChatConnectionChanged(bool connected)
        {
            Dispatcher.Invoke(() =>
            {
                _chatConnected = connected;
                ConnectChatBtn.IsEnabled = !connected;
                DisconnectChatBtn.IsEnabled = connected;
                SendButton.IsEnabled = connected;
                InputBox.IsEnabled = connected;
                ChatUrlBox.IsEnabled = !connected;
                ChatStatus.Text = connected ? "●" : "○";
                ChatStatus.Foreground = connected ? new Media.SolidColorBrush(Media.Colors.Lime) : new Media.SolidColorBrush(Media.Colors.Gray);
                AddSysMsg(connected ? "已连接" : "已断开");
                if (connected)
                {
                    // 连接成功时覆盖式保存当前地址
                    KzSettings.Set(_studio, KzSettings.KeyChatUrl, ChatUrlBox.Text.Trim());
                }
            });
        }

        private void OnChatMessage(string raw)
        {
            Dispatcher.Invoke(() =>
            {
                try
                {
                    var msg = ParseJson(raw);
                    string type = GetStr(msg, "type");
                    string text = GetStr(msg, "text");

                    switch (type)
                    {
                        case "connected":
                            if (!GetBool(msg, "server_online"))
                                AddSysMsg("提示：当前通道没有 Kanzi MCP Server 在线");
                            break;
                        case "thinking":
                            AddThinkMsg(text);
                            break;
                        case "claude_output":
                            AddAiMsg(text);
                            break;
                        case "error":
                            AddErrMsg(text);
                            break;
                        case "server_disconnected":
                            AddSysMsg($"MCP 连接断开: {text}");
                            break;
                        default:
                            AddAiMsg(text);
                            break;
                    }
                }
                catch
                {
                    AddErrMsg($"消息解析失败:\n{raw}");
                }
            });
        }

        private void OnChatError(string err)
        {
            Dispatcher.Invoke(() => AddErrMsg(err));
        }

        private void InputBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter) { SendChat(); e.Handled = true; }
        }

        private void SendButton_Click(object sender, RoutedEventArgs e) => SendChat();

        private async void SendChat()
        {
            string text = InputBox.Text.Trim();
            if (string.IsNullOrEmpty(text) || !_chatConnected) return;
            InputBox.Clear();
            AddUserMsg(text);
            try { await _wsClient.SendMessageAsync(text); }
            catch (Exception ex) { AddErrMsg($"发送失败: {ex.Message}"); }
        }

        #endregion

        #region 消息渲染

        private void AddUserMsg(string text) => AddBubble(CUser, "👤", text, W);
        private void AddAiMsg(string text) => AddBubble(CAi, "🤖", text, W);
        private void AddThinkMsg(string text) => AddBubble(CThink, "⏳", text, G);
        private void AddErrMsg(string text) => AddBubble(CError, "❌", text, new Media.SolidColorBrush(Media.Color.FromRgb(0xFF, 0x99, 0x99)));
        private void AddSysMsg(string text) => AddBubble(CSys, "ℹ️", text, new Media.SolidColorBrush(Media.Color.FromRgb(0xBB, 0xBB, 0xFF)));

        private void AddBubble(Media.SolidColorBrush bg, string prefix, string text, Media.Brush fg)
        {
            var border = new Border
            {
                Background = bg,
                CornerRadius = new CornerRadius(5),
                Margin = new Thickness(0, 2, 0, 2),
                BorderThickness = new Thickness(0)
            };
            var tb = new TextBox
            {
                Text = $"{prefix} {text}",
                TextWrapping = TextWrapping.Wrap,
                FontSize = 13,
                Foreground = fg,
                Background = Media.Brushes.Transparent,
                BorderThickness = new Thickness(0),
                IsReadOnly = true,
                IsTabStop = false,
                Margin = new Thickness(8, 5, 8, 5),
                MinHeight = 20
            };
            border.Child = tb;
            MessagePanel.Children.Add(border);
            MessageScroller.ScrollToBottom();
        }

        #endregion

        #region 清空日志

        private void ClearLog_Click(object sender, RoutedEventArgs e)
        {
            MCPLogBox.Clear();
            MCPLog("日志已清空");
        }

        #endregion

        #region 简易 JSON 解析

        private static Dictionary<string, object> ParseJson(string json)
        {
            var r = new Dictionary<string, object>();
            json = json.Trim();
            if (!json.StartsWith("{") || !json.EndsWith("}")) return r;
            json = json.Substring(1, json.Length - 2);
            int i = 0;
            while (i < json.Length)
            {
                while (i < json.Length && char.IsWhiteSpace(json[i])) i++;
                if (i >= json.Length || json[i] != '"') break;
                int ks = i + 1;
                i = FindJsonStringEnd(json, ks); if (i < 0) break;
                string k = Unescape(json.Substring(ks, i - ks)); i++;
                while (i < json.Length && json[i] != ':') i++; i++;
                while (i < json.Length && char.IsWhiteSpace(json[i])) i++;
                if (i >= json.Length) break;
                object v = null;
                if (json[i] == '"')
                {
                    int vs = i + 1; i = FindJsonStringEnd(json, vs); if (i < 0) break;
                    v = Unescape(json.Substring(vs, i - vs)); i++;
                }
                else if (json[i] == '{' || json[i] == '[')
                {
                    int d = 1, ns = i; i++;
                    while (i < json.Length && d > 0)
                    {
                        if (json[i] == '{' || json[i] == '[') d++;
                        else if (json[i] == '}' || json[i] == ']') d--;
                        i++;
                    }
                    v = json.Substring(ns, i - ns);
                }
                else
                {
                    int vs = i;
                    while (i < json.Length && json[i] != ',' && json[i] != '}' && !char.IsWhiteSpace(json[i])) i++;
                    string seg = json.Substring(vs, i - vs);
                    if (seg == "true") v = true;
                    else if (seg == "false") v = false;
                    else if (seg == "null") v = null;
                    else v = seg;
                }
                r[k] = v;
                while (i < json.Length && (char.IsWhiteSpace(json[i]) || json[i] == ',')) i++;
            }
            return r;
        }

        private static string GetStr(Dictionary<string, object> d, string k) =>
            d.TryGetValue(k, out var v) ? v?.ToString() ?? "" : "";

        // ★ 转义感知的 JSON 字符串结束引号查找:
        //   从 start(开引号之后的索引) 开始跳过 \x 转义序列,
        //   返回真正的结束引号索引。绝不把 \" 里的引号误当字符串结束。
        //   (修复: 手写 IndexOf('"') 会在含 \" 的长回答处截断 text,
        //    导致显示不全、末尾停在反斜杠 \ 上。)
        private static int FindJsonStringEnd(string json, int start)
        {
            int i = start;
            while (i < json.Length)
            {
                if (json[i] == '\\') { i += 2; continue; } // 跳过转义序列 \x
                if (json[i] == '"') return i;               // 真正的结束引号
                i++;
            }
            return -1;
        }

        private static bool GetBool(Dictionary<string, object> d, string k) =>
            d.TryGetValue(k, out var v) && v is true;

        private static string Unescape(string s)
        {
            if (string.IsNullOrEmpty(s) || !s.Contains("\\")) return s;
            var sb = new StringBuilder(s.Length);
            for (int i = 0; i < s.Length; i++)
            {
                if (s[i] == '\\' && i + 1 < s.Length)
                {
                    var n = s[i + 1];
                    if (n == '"') sb.Append('"');
                    else if (n == '\\') sb.Append('\\');
                    else if (n == 'n') sb.Append('\n');
                    else if (n == 'r') sb.Append('\r');
                    else if (n == 't') sb.Append('\t');
                    else sb.Append(n);
                    i++; continue;
                }
                sb.Append(s[i]);
            }
            return sb.ToString();
        }

        #endregion

        public void Dispose()
        {
            _wsClient?.Dispose();
            _mcpClient?.Dispose();
        }
    }
}
