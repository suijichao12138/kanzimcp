using System;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace KzNLPChatPlugin
{
    /// <summary>
    /// WebSocket 客户端，连接中继的 nlp_client 角色
    /// </summary>
    public class KzWSClient : IDisposable
    {
        private ClientWebSocket _ws;
        private CancellationTokenSource _cts;
        private Task _receiveTask;
        private readonly string _relayUrl;
        private readonly string _channelName;

        /// <summary>连接状态变化</summary>
        public event Action<bool> ConnectionChanged;
        /// <summary>收到消息</summary>
        public event Action<string> MessageReceived;
        /// <summary>发生错误</summary>
        public event Action<string> ErrorOccurred;

        public bool IsConnected => _ws?.State == WebSocketState.Open;

        public KzWSClient(string relayHost, int relayPort, string channelName)
        {
            _relayUrl = $"ws://{relayHost}:{relayPort}/{channelName}";
            _channelName = channelName;
        }

        public async Task ConnectAsync()
        {
            if (_ws != null)
            {
                try { _ws.Dispose(); } catch { }
            }

            _ws = new ClientWebSocket();
            _cts = new CancellationTokenSource();

            try
            {
                await _ws.ConnectAsync(new Uri(_relayUrl), _cts.Token);

                // 发送身份标识
                var authMsg = SimpleJson(new Dictionary<string, object>
                {
                    ["role"] = "nlp_client",
                    ["name"] = _channelName
                });
                var authBytes = Encoding.UTF8.GetBytes(authMsg);
                await _ws.SendAsync(new ArraySegment<byte>(authBytes),
                    WebSocketMessageType.Text, true, _cts.Token);

                ConnectionChanged?.Invoke(true);

                // 启动接收循环
                _receiveTask = ReceiveLoopAsync();
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke($"连接失败: {ex.Message}");
                ConnectionChanged?.Invoke(false);
            }
        }

        public async Task SendMessageAsync(string text)
        {
            if (_ws?.State != WebSocketState.Open) return;

            var msg = SimpleJson(new Dictionary<string, object>
            {
                ["type"] = "user_message",
                ["text"] = text
            });
            var bytes = Encoding.UTF8.GetBytes(msg);
            await _ws.SendAsync(new ArraySegment<byte>(bytes),
                WebSocketMessageType.Text, true, CancellationToken.None);
        }

        public async Task SendChoiceAsync(string selected)
        {
            if (_ws?.State != WebSocketState.Open) return;

            var msg = SimpleJson(new Dictionary<string, object>
            {
                ["type"] = "user_choice",
                ["selected"] = selected
            });
            var bytes = Encoding.UTF8.GetBytes(msg);
            await _ws.SendAsync(new ArraySegment<byte>(bytes),
                WebSocketMessageType.Text, true, CancellationToken.None);
        }

        private async Task ReceiveLoopAsync()
        {
            var buffer = new byte[8192];
            var sb = new StringBuilder();

            try
            {
                while (_ws?.State == WebSocketState.Open && !_cts.IsCancellationRequested)
                {
                    var result = await _ws.ReceiveAsync(
                        new ArraySegment<byte>(buffer), _cts.Token);

                    if (result.MessageType == WebSocketMessageType.Close)
                        break;

                    sb.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));

                    if (result.EndOfMessage)
                    {
                        var msg = sb.ToString();
                        sb.Clear();
                        MessageReceived?.Invoke(msg);
                    }
                }
            }
            catch (OperationCanceledException) { }
            catch (WebSocketException ex)
            {
                ErrorOccurred?.Invoke($"连接断开: {ex.Message}");
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke($"接收异常: {ex.Message}");
            }
            finally
            {
                ConnectionChanged?.Invoke(false);
            }
        }

        public async Task DisconnectAsync()
        {
            try
            {
                if (_ws?.State == WebSocketState.Open)
                {
                    await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure,
                        "用户断开", CancellationToken.None);
                }
            }
            catch { }
            finally
            {
                _cts?.Cancel();
                ConnectionChanged?.Invoke(false);
            }
        }

        public void Dispose()
        {
            _cts?.Cancel();
            _cts?.Dispose();
            _ws?.Dispose();
        }

        /// <summary>
        /// 极简 JSON 序列化（仅序列化基础类型和 Dictionary）
        /// </summary>
        private static string SimpleJson(Dictionary<string, object> dict)
        {
            var sb = new StringBuilder("{");
            bool first = true;
            foreach (var kv in dict)
            {
                if (!first) sb.Append(",");
                sb.Append($"\"{EscapeJson(kv.Key)}\":");
                sb.Append(ValueToJson(kv.Value));
                first = false;
            }
            sb.Append("}");
            return sb.ToString();
        }

        private static string ValueToJson(object val)
        {
            if (val == null) return "null";
            if (val is string s) return $"\"{EscapeJson(s)}\"";
            if (val is bool b) return b ? "true" : "false";
            if (val is int || val is long || val is float || val is double || val is decimal)
                return val.ToString().Replace(',', '.');
            return $"\"{EscapeJson(val.ToString())}\"";
        }

        private static string EscapeJson(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return s.Replace("\\", "\\\\")
                    .Replace("\"", "\\\"")
                    .Replace("\n", "\\n")
                    .Replace("\r", "\\r")
                    .Replace("\t", "\\t");
        }
    }
}
