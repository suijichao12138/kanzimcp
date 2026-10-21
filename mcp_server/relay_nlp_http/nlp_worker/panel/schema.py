#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""schema.py — nlp_worker 配置项的「自述」定义

这是可视化配置面板的唯一真相来源。面板不认识任何配置项，
只按这里的描述渲染表单 —— 所以以后加配置项（比如多模型），
只改这个文件 + yaml_io 的读写，面板本体一行都不用动。

字段属性：
  key       YAML 里的路径（点号分隔，如 copilot.model.name）
  label     中文名
  tier      basic / advanced / expert —— 对应「基础/进阶/高级」
  type      str/int/float/bool/enum/list/secret/path/dict
  default   默认值
  help      ★ 这是干什么的（一句话说清）
  hint      ★ 填错的后果 / 注意事项（没有就不写）
  example   示例值
  options   enum 的取值
  item      如果是 list，元素长什么样
  required  必填
  restart   改了要不要重启（默认 要）
"""
from __future__ import annotations

SCHEMA_VERSION = 1

# ── 分层：面板默认只展开基础，进阶/高级折叠 ──────────────────────
TIERS = [
    {"key": "basic",    "title": "基础",  "desc": "不填就跑不起来，或者必须按你的环境改", "expanded": True},
    {"key": "advanced", "title": "进阶",  "desc": "默认值通常够用，需要时再调",         "expanded": False},
    {"key": "expert",   "title": "高级",  "desc": "绝大多数情况不用碰，改错可能出问题",   "expanded": False},
]

# ── 分组（面板按这个顺序分区）──────────────────────────────────
GROUPS = [
    # ══════════════════ 中继连接 ══════════════════
    {
        "key": "relay", "title": "中继连接",
        "desc": "nlp_worker 要连的中继服务。通道名是别人找你的地址，必须唯一。",
        "fields": [
            {"key": "relay.url", "label": "中继地址", "tier": "basic", "type": "str",
             "required": True, "placeholder": "ws://10.10.118.152:58080/suijichao",
             "example": "ws://10.10.118.152:58080/suijichao",
             "help": "中继服务的完整地址，格式 ws://主机:端口/<通道名>。",
             "hint": "必须 ws:// 或 wss:// 开头。末尾那段必须和下面「通道名」完全一样，"
                     "否则启动就报错 —— 这是最常见的填错。"},

            {"key": "relay.channel", "label": "通道名", "tier": "basic", "type": "str",
             "required": True, "placeholder": "suijichao",
             "example": "suijichao",
             "help": "你在中继上的唯一标识。飞书 bot 名、http 白名单里的用户名都用这个。",
             "hint": "必须和「中继地址」末尾那段一致，也必须出现在「允许的通道」列表里。"},

            {"key": "relay.allowed_channels", "label": "允许的通道", "tier": "basic",
             "type": "list", "item": {"type": "str", "placeholder": "suijichao"},
             "help": "允许连接的安全白名单。必须包含上面的「通道名」。",
             "hint": "列表里没有你的通道名 → 启动报错。一般就填一个，和通道名相同。"},

            {"key": "relay.identity.dedicated_principal_id", "label": "专属用户标识",
             "tier": "basic", "type": "str", "placeholder": "suijichao",
             "help": "你在这个通道里的身份标识，通常和通道名相同。",
             "hint": "改了它但没同步改中继侧配置，会导致收到的消息对不上人。"},
        ],
    },

    # ══════════════════ 工作目录与账号 ══════════════════
    {
        "key": "copilot.basic", "title": "工作目录与账号",
        "desc": "Copilot 干活的地方和登录方式。",
        "fields": [
            {"key": "copilot.working_directory", "label": "工作目录", "tier": "basic",
             "type": "path", "required": True, "example": "D:\\suijichao\\kanzi\\AIBox4",
             "help": "Copilot 操作的项目目录（你的 Kanzi 工程），必须真实存在。",
             "hint": "填了不存在的目录 → 启动报错「does not exist」。"},

            {"key": "copilot.base_directory", "label": "数据目录", "tier": "basic",
             "type": "path", "example": "./.copilot-data",
             "help": "会话状态、大输出文件的存放位置。",
             "hint": "开了「工件下载」或「大输出落盘」时必填；不填会启动失败。"},

            {"key": "copilot.use_logged_in_user", "label": "使用已登录账号",
             "tier": "basic", "type": "bool", "default": True,
             "help": "用本机 copilot 已登录的 GitHub 账号（推荐）。",
             "hint": "关了就必须填下面的 GitHub Token，否则启动失败。",
             "restart": False},
        ],
    },

    # ══════════════════ 模型 ══════════════════
    {
        "key": "copilot.model", "title": "模型", "tier": "basic",
        "desc": "用哪个模型。自带模型走 BYOK（填服务商地址和密钥）。",
        "fields": [
            {"key": "copilot.model.name", "label": "模型名", "tier": "basic", "type": "str",
             "required": True, "example": "gpt-5.4",
             "help": "模型标识。用官方账号填官方模型名；自带模型填服务商的模型名。",
             "hint": "填错 → 启动或首次对话时报「模型不存在」。可用 --list-models 查（仅官方账号）。"},

            {"key": "copilot.model.reasoning_effort", "label": "推理强度", "tier": "basic",
             "type": "enum", "options": ["", "low", "medium", "high", "xhigh", "max"],
             "default": "medium",
             "help": "模型思考的用力程度。越高越准，但越慢越贵。",
             "hint": "留空 = 用模型默认。不是所有模型都支持全部档位。"},

            {"key": "copilot.model.provider.type", "label": "服务商类型", "tier": "basic",
             "type": "enum", "options": ["github", "openai", "azure", "anthropic"],
             "default": "github",
             "help": "github = 官方账号；其余三个 = 自带模型（BYOK）。",
             "hint": "选了非 github 就必须填下面的「服务地址」，否则启动报错。"},

            {"key": "copilot.model.provider.base_url", "label": "服务地址", "tier": "basic",
             "type": "str", "example": "https://oneapi.pateo.com.cn/v1",
             "help": "自带模型（BYOK）的服务地址，以 /v1 结尾。",
             "hint": "只在使用非 github 服务商时填；github 类型填了会报错。"},

            {"key": "copilot.model.provider.api_key", "label": "API 密钥", "tier": "basic",
             "type": "secret", "example": "${PATEO_API_KEY}",
             "help": "自带模型的 API 密钥。推荐写 ${环境变量名}，密钥就不落在配置文件里。",
             "hint": "直接写明文 = 密钥进文件，注意别把这个文件发出去。"},
        ],
    },

    # ══════════════════ 权限 ══════════════════
    {
        "key": "copilot.permissions", "title": "权限",
        "desc": "Copilot 被允许做什么。默认全拒，再按清单放行。",
        "fields": [
            {"key": "copilot.permissions.default", "label": "默认策略", "tier": "basic",
             "type": "enum", "options": ["deny", "allow", "ask"], "default": "deny",
             "help": "清单里没提到的操作怎么处理。",
             "hint": "★ 用 ask 要注意：飞书链路没有审批界面，ask 会被当成 deny 处理。"},

            {"key": "copilot.permissions.allow", "label": "允许清单", "tier": "basic",
             "type": "list", "item": {"type": "str", "placeholder": "read"},
             "help": "放行的权限/工具名，支持通配（如 kanzi-*-kz_get_*）。",
             "hint": "清单太宽（如 shell）会让 Copilot 能执行任意命令，谨慎。"},

            {"key": "copilot.permissions.deny", "label": "拒绝清单", "tier": "basic",
             "type": "list", "item": {"type": "str", "placeholder": "shell"},
             "help": "明确禁止的权限/工具名。拒绝优先级高于允许。",
             "hint": "建议至少禁掉 shell 和 kz_delete_*。"},
        ],
    },

    # ══════════════════ MCP 服务器 ══════════════════
    {
        "key": "mcp_servers", "title": "MCP 服务器",
        "desc": "Copilot 能调用的工具服务。每个服务是一个条目。",
        "fields": [
            {"key": "mcp_servers", "label": "服务列表", "tier": "basic", "type": "dict_list",
             "key_label": "服务名",
             "item_fields": [
                 {"key": "enabled", "label": "启用", "type": "bool", "default": True},
                 {"key": "type", "label": "类型", "type": "enum",
                  "options": ["http", "sse", "stdio", "local"], "default": "http"},
                 {"key": "url", "label": "地址", "type": "str",
                  "placeholder": "http://10.10.118.152:9001/kanzistudio_mcp",
                  "help": "远程服务的 URL（type=http/sse 时必填）"},
                 {"key": "headers", "label": "请求头", "type": "dict",
                  "placeholder": "X-Kanzi-User: suijichao",
                  "help": "鉴权头。Kanzi MCP 必须带 X-Kanzi-User，值是通道名"},
                 {"key": "tools", "label": "工具", "type": "list",
                  "item": {"type": "str", "placeholder": "*"}},
                 {"key": "timeout_seconds", "label": "超时(秒)", "type": "int", "default": 300},
                 {"key": "command", "label": "命令", "type": "str",
                  "help": "本地服务命令（type=stdio/local 时必填）"},
             ],
             "help": "每个条目是 {服务名: {配置}}。Kanzi 链路通常配三个。",
             "hint": "★ headers 里的 X-Kanzi-User 必须和你的通道名一致，"
                     "否则 http 组件会返回 403。"},
        ],
    },

    # ══════════════════ 工件下载 ══════════════════
    {
        "key": "artifacts", "title": "工件下载",
        "desc": "让 Copilot 能自己去下载大结果文件（截图、批量数据等）。",
        "fields": [
            {"key": "artifacts.enabled", "label": "启用", "tier": "advanced",
             "type": "bool", "default": False,
             "help": "开了之后 Copilot 能拿 URL 去取文件，而不是把内容塞进对话。",
             "hint": "开了必须同时填「允许的来源」，也要填「数据目录」。"},

            {"key": "artifacts.allowed_origins", "label": "允许的来源", "tier": "advanced",
             "type": "list", "item": {"type": "str", "placeholder": "http://10.10.118.152:9001"},
             "help": "只允许从这些地址下载。必须写到 host:port，不能只写域名。",
             "hint": "格式不对 → 启动报错。地址变了这里也要改，否则下载被拒。"},
        ],
    },

    # ══════════════════ 对话与提示 ══════════════════
    {
        "key": "compatibility", "title": "对话与提示",
        "desc": "飞书里看到的效果：思考提示、进度反馈。",
        "fields": [
            {"key": "compatibility.thinking_text", "label": "思考提示语", "tier": "advanced",
             "type": "str", "default": "🤖 Copilot 思考中...",
             "help": "收到消息后先回给用户的占位文字。",
             "restart": False},

            {"key": "compatibility.progress_feedback", "label": "进度反馈",
             "tier": "advanced", "type": "bool", "default": True,
             "help": "干活过程中持续回报进度（进行了几步、调了哪些工具）。",
             "hint": "关掉就只回「思考中」和最终结果，长任务会显得没反应。",
             "restart": False},

            {"key": "compatibility.progress_min_interval_seconds",
             "label": "进度最小间隔(秒)", "tier": "advanced", "type": "float", "default": 2.0,
             "help": "两条进度之间至少隔这么久，防止刷屏。",
             "hint": "太小（<1）消息会密集刷屏；太大则进度看起来卡顿。",
             "restart": False},
        ],
    },

    # ══════════════════ 消息与队列 ══════════════════
    {
        "key": "messages", "title": "消息与队列", "tier": "advanced",
        "fields": [
            {"key": "messages.max_input_chars", "label": "输入上限(字符)", "tier": "advanced",
             "type": "int", "default": 12000,
             "help": "用户单条消息最多多长，超了会被截断或拒绝。",
             "hint": "太小 → 长消息进不来；太大 → 可能超出模型上下文。"},

            {"key": "messages.max_output_chars", "label": "输出上限(字符)", "tier": "advanced",
             "type": "int", "default": 3500,
             "help": "回复单条最多多长，超了会自动拆分成多条发送。",
             "hint": "飞书单条消息有长度限制，设太大也没用。"},
        ],
    },

    # ══════════════════ 日志 ══════════════════
    {
        "key": "logging", "title": "日志",
        "desc": "格式与 relay / http / feishu 三个组件一致。",
        "fields": [
            {"key": "logging.level", "label": "日志级别", "tier": "advanced",
             "type": "enum", "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
             "default": "INFO",
             "help": "记录多详细。平时 INFO，排错时临时换 DEBUG。",
             "hint": "DEBUG 会写很多，长期开着日志涨得快。"},

            {"key": "logging.file", "label": "日志文件", "tier": "advanced",
             "type": "path", "default": "./logs/bridge.log",
             "help": "日志写到哪。留空 = 只输出控制台。",
             "restart": False},
        ],
    },

    # ══════════════════ 高级：连接细节 ══════════════════
    {
        "key": "relay.expert", "title": "连接细节", "tier": "expert",
        "fields": [
            {"key": "relay.reconnect_delay_seconds", "label": "重连间隔(秒)",
             "tier": "expert", "type": "float", "default": 3,
             "range": [0.1, 300],
             "help": "断开后等多久重连。",
             "hint": "太小 → 中继没起来时会频繁重试刷日志。"},

            {"key": "relay.ping_interval_seconds", "label": "心跳间隔(秒)",
             "tier": "expert", "type": "float", "default": 30, "range": [0.1, 300],
             "help": "多久发一次心跳，用来确认连接还活着。"},

            {"key": "relay.ping_timeout_seconds", "label": "心跳超时(秒)",
             "tier": "expert", "type": "float", "default": 10, "range": [0.1, 300],
             "help": "心跳多久没回应就判定断线。"},

            {"key": "relay.max_message_bytes", "label": "单条消息上限(字节)",
             "tier": "expert", "type": "int", "default": 16777216,
             "help": "单条 WebSocket 消息最大字节数（默认 16MB）。",
             "hint": "太大 screenshot 之类的大消息可能被中继拒收。"},
        ],
    },

    # ══════════════════ 高级：Copilot 行为 ══════════════════
    {
        "key": "copilot.expert", "title": "Copilot 行为", "tier": "expert",
        "fields": [
            {"key": "copilot.response_timeout_seconds", "label": "总超时(秒)",
             "tier": "expert", "type": "int", "default": 600, "range": [1, 36000],
             "help": "单次任务最多跑多久，超了强制结束。",
             "hint": "长任务（比如大批量改工程）可能撞上这个上限。"},

            {"key": "copilot.max_idle_seconds", "label": "最大空闲(秒)",
             "tier": "expert", "type": "int", "default": 300, "range": [1, 36000],
             "help": "只要 Copilot 还在输出或调工具就自动续期；"
                     "超过这么久毫无动静才判定卡死。",
             "hint": "调太小会误杀正在跑的长任务；调太大则真卡死也不报错。"},

            {"key": "copilot.enable_session_store", "label": "记忆会话",
             "tier": "expert", "type": "bool", "default": True,
             "help": "保存会话上下文，重启后能接着聊。",
             "hint": "关掉后每次重启都从零开始，之前聊的它会忘。"},
        ],
    },

    # ══════════════════ 高级：存储 ══════════════════
    {
        "key": "storage", "title": "存储", "tier": "expert",
        "fields": [
            {"key": "storage.database_path", "label": "数据库文件", "tier": "expert",
             "type": "path", "default": "./data/bridge.db",
             "help": "消息去重和队列的本地数据库。",
             "hint": "换位置后旧数据不会跟着走（去重记录会重置）。"},
        ],
    },
]


# ── 面板用的遍历工具 ────────────────────────────────────────────
def all_fields():
    """摊平所有字段（含 dict_list 的子字段不展开）。"""
    for g in GROUPS:
        for f in g.get("fields", []):
            yield g, f


def fields_by_tier(tier: str):
    for g, f in all_fields():
        if f.get("tier", g.get("tier", "expert")) == tier:
            yield g, f


def find_field(key: str):
    for _g, f in all_fields():
        if f["key"] == key:
            return f
    return None
