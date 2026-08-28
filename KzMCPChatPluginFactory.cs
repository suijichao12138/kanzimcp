using System;
using System.ComponentModel.Composition;
using Rightware.Kanzi.Studio.PluginInterface;

namespace KzMCPChatPlugin
{
    /// <summary>
    /// Kanzi Studio MCP + 聊天助手整合插件工厂
    /// </summary>
    [Export(typeof(PluginContent))]
    public class KzMCPChatPluginFactory : PluginWindowFactory
    {
        private KanziStudio _studio;

        public string Name => "KzMCPChatPlugin";
        public string DisplayName => "AI MCP 助手";
        public string Description => "MCP Server 控制台 + AI 聊天助手";

        public CommandPlacement CommandPlacement
        {
            get
            {
                return new CommandPlacement("aiMCPMenu", ContextMenuPlacement.NONE, false, null);
            }
        }

        public uint DefaultWidth => 520;
        public uint DefaultHeight => 480;

        public bool CanExecute(PluginCommandParameter parameter)
        {
            return _studio != null && _studio.ActiveProject != null;
        }

        public void Initialize(KanziStudio studio)
        {
            _studio = studio;
        }

        public PluginWindow CreateWindow(PluginWindowState state)
        {
            return new KzMainWindow(_studio);
        }
    }
}
