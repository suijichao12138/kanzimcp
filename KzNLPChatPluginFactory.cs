using System;
using System.ComponentModel.Composition;
using Rightware.Kanzi.Studio.PluginInterface;

namespace KzNLPChatPlugin
{
    /// <summary>
    /// Kanzi Studio NLP 聊天助手插件工厂
    /// 通过自然语言让 AI 操作 Kanzi Studio
    /// </summary>
    [Export(typeof(PluginContent))]
    public class KzNLPChatPluginFactory : PluginWindowFactory
    {
        private KanziStudio _studio;

        public string Name => "KzNLPChatPlugin";
        public string DisplayName => "AI 聊天助手";
        public string Description => "通过自然语言让 AI 自动创建和编辑 Kanzi Studio UI 节点、绑定和交互";

        public CommandPlacement CommandPlacement
        {
            get
            {
                return new CommandPlacement("aiChatMenu", ContextMenuPlacement.NONE, false, null);
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
            return new KzNLPChatWindow(_studio, state.WindowNotifier);
        }
    }
}
