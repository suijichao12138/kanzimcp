using System;
using System.Windows;
using System.Windows.Controls;
using Rightware.Kanzi.Studio.PluginInterface;

namespace KzMCPChatPlugin
{
    /// <summary>
    /// MCP Server 控制台 Tab
    /// </summary>
    public partial class KzMCPServerWindow : UserControl, IDisposable
    {
        private readonly KzMCPServerClient _mcpClient;
        private readonly KzMCPReflectionBridge _bridge;
        private readonly KanziStudio _studio;
        private bool _connected;

        public KzMCPServerWindow(KzMCPServerClient mcpClient, KzMCPReflectionBridge bridge,
                                 KanziStudio studio = null)
        {
            InitializeComponent();
            _mcpClient = mcpClient;
            _bridge = bridge;
            _studio = studio;

            _mcpClient.ConnectionChanged += OnConnectionChanged;
            _mcpClient.LogReceived += OnLog;

            // 从 Kanzi 用户偏好恢复上次的地址(无存量值则用 XAML 默认值)
            try
            {
                RelayUrlBox.Text = KzSettings.Get(_studio, KzSettings.KeyRelayUrl,
                                                  KzSettings.DefaultRelayUrl);
            }
            catch { }

            RefreshProjectInfo();
        }

        private void OnConnectionChanged(bool connected)
        {
            _connected = connected;
            Dispatcher.Invoke(() =>
            {
                ConnectMCPBtn.IsEnabled = !connected;
                DisconnectMCPBtn.IsEnabled = connected;
                StatusIcon.Text = connected ? "🟢" : "⚫";
                StatusText.Text = connected ? "已连接" : "未连接";
                ChannelText.Text = _mcpClient.Channel;
                Log($"MCP Server {(connected ? "已连接" : "已断开")}");
                if (connected)
                {
                    // 连接成功时覆盖式保存当前地址
                    KzSettings.Set(_studio, KzSettings.KeyRelayUrl, RelayUrlBox.Text.Trim());
                    RefreshProjectInfo();
                }
            });
        }

        private void OnLog(string msg)
        {
            Dispatcher.Invoke(() => Log(msg));
        }

        private void Log(string msg)
        {
            LogBox.AppendText($"[{DateTime.Now:HH:mm:ss}] {msg}\n");
            LogBox.ScrollToEnd();
        }

        private void RefreshProjectInfo()
        {
            try
            {
                _bridge.Refresh();
                string name = _bridge.GetProjectName();
                ProjectInfo.Text = $"工程：{name}";
            }
            catch
            {
                ProjectInfo.Text = "工程：无法获取";
            }
        }

        private async void ConnectMCP_Click(object sender, RoutedEventArgs e)
        {
            string url = RelayUrlBox.Text.Trim();
            if (string.IsNullOrEmpty(url))
            {
                Log("请输入 relay 地址");
                return;
            }
            ConnectMCPBtn.IsEnabled = false;
            Log($"正在连接 {url} ...");
            await _mcpClient.ConnectAsync(url);
        }

        private async void DisconnectMCP_Click(object sender, RoutedEventArgs e)
        {
            await _mcpClient.DisconnectAsync();
        }

        public void Dispose()
        {
            _mcpClient.ConnectionChanged -= OnConnectionChanged;
            _mcpClient.LogReceived -= OnLog;
        }
    }
}
