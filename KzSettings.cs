using System;
using Rightware.Kanzi.Studio.PluginInterface;

namespace KzMCPChatPlugin
{
    /// <summary>
    /// 插件配置持久化 —— 走 Kanzi 原生 IUserPreferences, 不建外部文件。
    ///
    /// IUserPreferences 由 KanziStudio.UserPreferences 取得, API (反编译 PluginInterface.dll 确认):
    ///   T      GetSetting&lt;T&gt;(string key, T defaultValue)
    ///   object GetSetting(string key)
    ///   void   SetSetting(string key, object value)
    ///   event  SettingChanged(EventHandler&lt;UserPreferenceSettingChangedEventArgs&gt;)
    ///
    /// 落盘位置由 Kanzi Studio 管理(随用户配置), 插件无需操心底层文件。
    /// 任何一次读写失败都不抛异常 —— 配置读写失败绝不能影响插件主流程,
    /// 失败时静默回退到传入的默认值。
    /// </summary>
    public static class KzSettings
    {
        // ---- 配置键名 ----
        public const string KeyMcpUrl = "KzMCPChatPlugin.McpUrl";
        public const string KeyChatUrl = "KzMCPChatPlugin.ChatUrl";
        public const string KeyRelayUrl = "KzMCPChatPlugin.RelayUrl";

        // ---- 默认值(XAML 同值; 仅当偏好里没有存量值时使用) ----
        public const string DefaultMcpUrl = "ws://10.10.118.152:58080/username";
        public const string DefaultChatUrl = "ws://10.10.118.152:58080/username";
        public const string DefaultRelayUrl = "ws://10.10.118.152:58080/username";

        private static IUserPreferences Prefs(KanziStudio studio)
        {
            if (studio == null) return null;
            try { return studio.UserPreferences; }
            catch { return null; }
        }

        /// <summary>读字符串设置; 无值/失败时返回 defaultValue。</summary>
        public static string Get(KanziStudio studio, string key, string defaultValue)
        {
            var p = Prefs(studio);
            if (p == null) return defaultValue;
            try
            {
                // 泛型重载: T GetSetting<T>(string key, T defaultValue)
                string v = p.GetSetting<string>(key, null);
                if (string.IsNullOrEmpty(v)) return defaultValue;
                return v;
            }
            catch
            {
                return defaultValue;
            }
        }

        /// <summary>写字符串设置(覆盖式); 失败静默忽略, 返回是否成功。</summary>
        public static bool Set(KanziStudio studio, string key, string value)
        {
            var p = Prefs(studio);
            if (p == null || string.IsNullOrEmpty(key)) return false;
            try
            {
                p.SetSetting(key, value);
                return true;
            }
            catch
            {
                return false;
            }
        }
    }
}
