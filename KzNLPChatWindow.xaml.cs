using System;
using System.Collections.Generic;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Media = System.Windows.Media;
using Rightware.Kanzi.Studio.PluginInterface;

namespace KzNLPChatPlugin
{
    public partial class KzNLPChatWindow : UserControl, PluginWindow, IDisposable
    {
#pragma warning disable CS0067
        public event EventHandler TitleChanged;
#pragma warning restore CS0067

        public string Icon => null;
        public string Title => "AI 聊天助手";
        public PluginWindowState SerializeState() => null;

        public void Dispose() => _wsClient?.Dispose();

        private readonly KanziStudio _studio;
        private KzWSClient _wsClient;
        private bool _connected;

        // 颜色常量
        private static readonly Media.SolidColorBrush
            CUser = new Media.SolidColorBrush(Media.Color.FromRgb(0x3A, 0x3A, 0x3A)),
            CAi = new Media.SolidColorBrush(Media.Color.FromRgb(0x2A, 0x2A, 0x2A)),
            CSys = new Media.SolidColorBrush(Media.Color.FromRgb(0x1E, 0x3A, 0x5F)),
            CThink = new Media.SolidColorBrush(Media.Color.FromRgb(0x33, 0x33, 0x33)),
            CError = new Media.SolidColorBrush(Media.Color.FromRgb(0x5C, 0x1A, 0x1A)),
            CChoice = new Media.SolidColorBrush(Media.Color.FromRgb(0x1A, 0x3C, 0x2E)),
            ColorBtn = new Media.SolidColorBrush(Media.Color.FromRgb(0x4C, 0xAF, 0x50)),
            W = Media.Brushes.White,
            G = new Media.SolidColorBrush(Media.Color.FromRgb(0xCC, 0xCC, 0xCC));



        public KzNLPChatWindow(KanziStudio studio, object windowNotifier)
        {
            InitializeComponent();
            _studio = studio;
            AddSysMsg("输入中继地址，点击「连接」后即可发送自然语言指令。");
        }

        #region 连接

        private async void ConnectButton_Click(object sender, RoutedEventArgs e)
        {
            string url = UrlBox.Text.Trim();
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

            // 从 URL 解析 host, port, channel
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

            UrlBox.IsEnabled = false;
            ConnectButton.IsEnabled = false;

            AddSysMsg($"正在连接 {host}:{port}/{channel} ...");

            _wsClient = new KzWSClient(host, port, channel);
            _wsClient.ConnectionChanged += OnConnChanged;
            _wsClient.MessageReceived += OnMsg;
            _wsClient.ErrorOccurred += OnErr;
            await _wsClient.ConnectAsync();
        }

        private async void DisconnectButton_Click(object sender, RoutedEventArgs e)
        {
            if (_wsClient != null)
                await _wsClient.DisconnectAsync();
        }

        private void OnConnChanged(bool connected)
        {
            Dispatcher.Invoke(() =>
            {
                _connected = connected;
                ConnectButton.IsEnabled = !connected;
                DisconnectButton.IsEnabled = connected;
                SendButton.IsEnabled = connected;
                InputBox.IsEnabled = connected;
                UrlBox.IsEnabled = !connected;
                AddSysMsg(connected ? "已连接" : "已断开");
            });
        }

        private void OnMsg(string raw)
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
                        case "executing":
                            AddAiMsg(text);
                            break;
                        case "mcp_result":
                            AddAiMsg($"✅ {text}");
                            break;
                        case "need_choice":
                            AddChoiceMsg(text, msg);
                            break;
                        case "done":
                            AddAiMsg($"🎉 {text}");
                            break;
                        case "error":
                            AddErrMsg(text);
                            break;
                        case "claude_output":
                            AddAiMsg(text);
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

        private void OnErr(string err) =>
            Dispatcher.Invoke(() => AddErrMsg(err));

        #endregion

        #region 发送

        private void InputBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter) { Send(); e.Handled = true; }
        }

        private void SendButton_Click(object sender, RoutedEventArgs e) => Send();

        private async void Send()
        {
            string text = InputBox.Text.Trim();
            if (string.IsNullOrEmpty(text) || !_connected) return;
            InputBox.Clear();
            AddUserMsg(text);
            try { await _wsClient.SendMessageAsync(text); }
            catch (Exception ex) { AddErrMsg($"发送失败: {ex.Message}"); }
        }

        private async void OnChoice(string choice)
        {
            if (!_connected) return;
            AddUserMsg($"选择: {choice}");
            try { await _wsClient.SendChoiceAsync(choice); }
            catch (Exception ex) { AddErrMsg($"发送失败: {ex.Message}"); }
        }

        #endregion

        #region 消息渲染

        private void AddUserMsg(string text) => AddBubble(CUser, "👤", text, W, false);
        private void AddAiMsg(string text) => AddBubble(CAi, "🤖", text, W, false);
        private void AddThinkMsg(string text) => AddBubble(CThink, "⏳", text, G, true);
        private void AddErrMsg(string text) => AddBubble(CError, "❌", text, new Media.SolidColorBrush(Media.Color.FromRgb(0xFF, 0x99, 0x99)), false);
        private void AddSysMsg(string text) => AddBubble(CSys, "ℹ️", text, new Media.SolidColorBrush(Media.Color.FromRgb(0xBB, 0xBB, 0xFF)), false);

        private void AddChoiceMsg(string text, Dictionary<string, object> msg)
        {
            var border = MakeBorder(CChoice);
            var stack = new StackPanel { Margin = new Thickness(4) };
            stack.Children.Add(new TextBlock
            {
                Text = $"🤖 {text}",
                TextWrapping = TextWrapping.Wrap,
                FontSize = 13,
                Foreground = W,
                
            });
            if (msg.TryGetValue("choices", out var rc) && rc is string cs)
            {
                var opts = ParseArray(cs);
                if (opts.Count > 0)
                {
                    var wp = new WrapPanel { Margin = new Thickness(0, 6, 0, 0) };
                    foreach (string c in opts)
                    {
                        var btn = new Button
                        {
                            Content = c, Height = 26, Margin = new Thickness(0, 0, 6, 4),
                            Padding = new Thickness(10, 0, 10, 0), FontSize = 12,
                            Cursor = Cursors.Hand, Background = ColorBtn,
                            Foreground = W, BorderThickness = new Thickness(0),
                            
                        };
                        string cc = c;
                        btn.Click += (s, e) => OnChoice(cc);
                        wp.Children.Add(btn);
                    }
                    stack.Children.Add(wp);
                }
            }
            border.Child = stack;
            MessagePanel.Children.Add(border);
            Scroll();
        }

        private void AddBubble(Media.SolidColorBrush bg, string prefix, string text, Media.Brush fg, bool italic)
        {
            var border = MakeBorder(bg);
            var tb = new TextBox
            {
                Text = $"{prefix} {text}",
                TextWrapping = TextWrapping.Wrap,
                FontSize = (italic ? 12 : 13),                
                FontStyle = italic ? FontStyles.Italic : FontStyles.Normal,
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
            Scroll();
        }

        private Border MakeBorder(Media.SolidColorBrush bg) => new Border
        {
            Background = bg, CornerRadius = new CornerRadius(5),
            Margin = new Thickness(0, 2, 0, 2), BorderThickness = new Thickness(0)
        };

        private void Scroll() => MessageScroller.ScrollToBottom();

        #endregion

        #region 简易 JSON

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
                i = json.IndexOf('"', ks); if (i < 0) break;
                string k = Unescape(json.Substring(ks, i - ks)); i++;
                while (i < json.Length && json[i] != ':') i++; i++;
                while (i < json.Length && char.IsWhiteSpace(json[i])) i++;
                if (i >= json.Length) break;
                object v = null;
                if (json[i] == '"')
                {
                    int vs = i + 1; i = json.IndexOf('"', vs); if (i < 0) break;
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

        private static List<string> ParseArray(string json)
        {
            var r = new List<string>();
            json = json.Trim();
            if (!json.StartsWith("[") || !json.EndsWith("]")) return r;
            json = json.Substring(1, json.Length - 2);
            int i = 0;
            while (i < json.Length)
            {
                while (i < json.Length && char.IsWhiteSpace(json[i])) i++;
                if (i >= json.Length || json[i] != '"') break;
                int vs = i + 1;
                i = json.IndexOf('"', vs); if (i < 0) break;
                r.Add(Unescape(json.Substring(vs, i - vs))); i++;
                while (i < json.Length && (char.IsWhiteSpace(json[i]) || json[i] == ',')) i++;
            }
            return r;
        }

        private static string GetStr(Dictionary<string, object> d, string k) =>
            d.TryGetValue(k, out var v) ? v?.ToString() ?? "" : "";

        private static bool GetBool(Dictionary<string, object> d, string k) =>
            d.TryGetValue(k, out var v) && v is true;

        private static string Unescape(string s)
        {
            if (string.IsNullOrEmpty(s)) return s;
            var sb = new StringBuilder(s.Length);
            for (int i = 0; i < s.Length; i++)
            {
                if (s[i] == '\\' && i + 5 < s.Length && s[i + 1] == 'u')
                {
                    if (int.TryParse(s.Substring(i + 2, 4),
                        System.Globalization.NumberStyles.HexNumber, null, out int c))
                    { sb.Append((char)c); i += 5; continue; }
                }
                if (s[i] == '\\' && i + 6 < s.Length && s[i + 1] == '\\' && s[i + 2] == 'u')
                {
                    if (int.TryParse(s.Substring(i + 3, 4),
                        System.Globalization.NumberStyles.HexNumber, null, out int c))
                    { sb.Append((char)c); i += 6; continue; }
                }
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
    }
}
