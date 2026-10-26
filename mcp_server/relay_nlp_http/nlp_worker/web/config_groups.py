#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config_groups.py — config.yaml 的分组定义（网页配置管理的唯一真相来源）

网页不认识任何具体配置项，只按这里的 field spec 渲染表单。
以后加/改配置项，只改这个文件即可，web 前端与 API 不用动。

field spec 字段说明：
  key        : yaml 点号路径（相对该组根）
  label      : 表单显示名
  type       : str | int | float | bool | enum | list | dict | textarea | secret
  default    : 空值时显示
  help       : 说明文字
  env        : 若值为 ${KEY} 引用环境变量，填 KEY（用于 .env 联动显示/反向索引）
  required   : 是否必填（仅展示，校验交给 validate）
  enum_values: type=enum 时的候选项

注意：config.yaml 里可能引用 ${KEY}（如 api_key: ${OPENAI_API_KEY}）。
保存时保持 ${KEY} 占位不变，真实值只在表单"显示"时从 .env 展开 ——
绝不要把真实密钥写回 config.yaml。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ${KEY} 环境变量占位匹配（与 copilot_runtime._ENV_PATTERN 一致）
ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True, slots=True)
class FieldSpec:
    key: str
    label: str
    type: str = "str"
    default: object = None
    help: str = ""
    env: str | None = None
    required: bool = False
    enum_values: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GroupSpec:
    """一个配置分组（= 网页上一个独立页面）。"""

    key: str               # 顶层 yaml key，如 "relay" / "copilot"
    title: str             # 页面标题
    description: str = ""
    fields: list[FieldSpec] = field(default_factory=list)
    # 该组是否整段可编辑（如 relay/copilot 是 dict；skills.entries / mcp_servers
    # 是列表/映射，单独特殊处理）
    kind: str = "fields"   # fields | dict_of_servers | skill_entries


def _f(**kw) -> FieldSpec:
    return FieldSpec(**kw)


GROUPS: list[GroupSpec] = [
    GroupSpec(
        key="web",
        title="网页控制台",
        description="本网页端自身配置（监听地址/端口/启停）。修改后需重启 nlp_worker 生效。",
        fields=[
            _f(key="enabled", label="启用网页控制台", type="bool", default=True,
               help="false 则不启动本网页服务"),
            _f(key="listen_host", label="监听 IP", type="str", default="127.0.0.1",
               help="127.0.0.1 仅本机；0.0.0.0 或局域网 IP 可被其他机器访问"),
            _f(key="listen_port", label="监听端口", type="int", default=8400),
        ],
    ),
    GroupSpec(
        key="relay",
        title="连接 Relay",
        description="与 relay 中转服务器的连接配置。",
        fields=[
            _f(key="url", label="Relay URL", type="str", required=True,
               help="ws://host:port/channel"),
            _f(key="channel", label="通道名", type="str", required=True),
            _f(key="role", label="角色", type="enum", default="nlp_worker",
               enum_values=["nlp_worker", "client"]),
            _f(key="reconnect_delay_seconds", label="重连间隔(秒)", type="int", default=3),
            _f(key="ping_interval_seconds", label="Ping 间隔(秒)", type="int", default=30),
            _f(key="ping_timeout_seconds", label="Ping 超时(秒)", type="int", default=10),
            _f(key="max_message_bytes", label="最大消息字节", type="int", default=16777216),
            _f(key="allowed_channels", label="允许通道", type="list", default=["suijichao"]),
            _f(key="identity.mode", label="身份模式", type="enum", default="dedicated_channel",
               enum_values=["dedicated_channel", "shared"]),
            _f(key="identity.dedicated_principal_id", label="专属用户 ID", type="str"),
            _f(key="identity.include_thread_scope", label="包含线程范围", type="bool", default=True),
        ],
    ),
    GroupSpec(
        key="copilot",
        title="Copilot 模型",
        description="Copilot 会话、模型、system prompt、权限配置。",
        fields=[
            _f(key="github_token", label="GitHub Token", type="secret", default="null",
               env="GITHUB_TOKEN", help="留 null 用登录用户；或 ${GITHUB_TOKEN}"),
            _f(key="use_logged_in_user", label="使用登录用户", type="bool", default=True),
            _f(key="working_directory", label="工作目录", type="str", default="."),
            _f(key="base_directory", label="数据目录", type="str", default="./.copilot-data"),
            _f(key="response_timeout_seconds", label="响应超时(秒)", type="int", default=600),
            _f(key="max_idle_seconds", label="最大空闲(秒)", type="int", default=300),
            _f(key="kanzi_probe_url", label="Kanzi 活性探测 URL", type="str"),
            _f(key="resume_failure", label="恢复失败策略", type="enum", default="error",
               enum_values=["error", "new"]),
            _f(key="configuration_change", label="配置变更策略", type="enum", default="error",
               enum_values=["error", "new", "resume"]),
            _f(key="enable_session_store", label="启用会话存储", type="bool", default=True),
            _f(key="infinite_session.enabled", label="自动压缩上下文", type="bool", default=True,
               help="无限会话：上下文利用率到阈值自动后台压缩历史，防长对话溢出"),
            _f(key="infinite_session.background_compaction_threshold", label="后台压缩阈值", type="float", default=0.80,
               help="上下文利用率到 0.80(80%) 时后台异步压缩，会话不中断"),
            _f(key="infinite_session.buffer_exhaustion_threshold", label="阻塞压缩阈值", type="float", default=0.95,
               help="到 0.95(95%) 时阻塞等压缩完成，防上下文溢出"),
            _f(key="model.name", label="模型名", type="str", default="gpt-5.4", required=True),
            _f(key="model.reasoning_effort", label="推理强度", type="enum", default="medium",
               enum_values=["low", "medium", "high"]),
            _f(key="model.provider.type", label="Provider 类型", type="enum", default="github",
               enum_values=["github", "openai", "azure", "anthropic"]),
            _f(key="model.provider.base_url", label="Provider Base URL", type="str"),
            _f(key="model.provider.api_key", label="Provider API Key", type="secret",
               help="直接显示/编辑 config 里的设置值（不再与 .env 联动）"),
            _f(key="agent.system_prompt", label="System Prompt", type="textarea",
               help="常驻系统提示词；操作 Kanzi 必须严格按 skill 执行等铁律在此"),
            _f(key="agent.system_prompt_mode", label="System Prompt 模式", type="enum",
               default="append", enum_values=["append", "replace"]),
            _f(key="agent.available_tools", label="可用工具", type="list", default=[]),
            _f(key="agent.excluded_tools", label="排除工具", type="list", default=[]),
            _f(key="permissions.default", label="默认权限", type="enum", default="deny",
               enum_values=["allow", "deny", "ask"]),
            _f(key="permissions.allow", label="允许操作", type="list", default=[]),
            _f(key="permissions.deny", label="拒绝操作", type="list", default=[]),
            _f(key="permissions.ask", label="询问操作", type="list", default=[]),
        ],
    ),
    GroupSpec(
        key="skills",
        title="Skills 加载",
        description="加载哪些 skill 目录（可配置单 skill 路径或 skill 父目录）+ 大小限制。",
        kind="skill_entries",
        fields=[
            _f(key="max_file_bytes", label="单个 skill 最大字节", type="int", default=131072),
            _f(key="max_total_bytes", label="全部 skill 最大字节", type="int", default=524288),
        ],
    ),
    GroupSpec(
        key="mcp_servers",
        title="MCP 服务",
        description="MCP 端点配置（Kanzi Studio / Skill / API / 文档等），每个服务含 url、headers、超时等。",
        kind="dict_of_servers",
    ),
    GroupSpec(
        key="artifacts",
        title="文件落盘 Artifacts",
        description="大输出落盘、下载、搜索限制。",
        fields=[
            _f(key="enabled", label="启用", type="bool", default=True),
            _f(key="allowed_origins", label="允许来源", type="list", default=[]),
            _f(key="timeout_seconds", label="超时(秒)", type="int", default=60),
            _f(key="max_download_bytes", label="最大下载字节", type="int", default=67108864),
            _f(key="max_tool_output_chars", label="工具输出最大字符", type="int", default=8000),
            _f(key="max_search_results", label="最大搜索结果", type="int", default=50),
            _f(key="allowed_mime_types", label="允许 MIME", type="list", default=[]),
        ],
    ),
    GroupSpec(
        key="compatibility",
        title="兼容与进度反馈",
        description="旧桥兼容、progress 反馈、上传下载限制。",
        fields=[
            _f(key="thinking_text", label="思考中文本", type="str", default="🤖 Copilot 思考中..."),
            _f(key="progress_feedback", label="进度反馈", type="bool", default=True),
            _f(key="progress_min_interval_seconds", label="进度最小间隔(秒)", type="float", default=2.0),
            _f(key="progress_max_tool_events_before_summary", label="工具汇总阈值", type="int", default=8),
            _f(key="output_type", label="输出类型", type="enum", default="claude_output",
               enum_values=["claude_output", "text"]),
            _f(key="support_file_download_marker", label="支持文件下载标记", type="bool", default=True),
            _f(key="bridge_http", label="桥 HTTP 地址", type="str"),
            _f(key="bridge_target_open_id", label="桥目标 OpenID", type="str"),
            _f(key="download_timeout_seconds", label="下载超时(秒)", type="int", default=120),
            _f(key="max_upload_bytes", label="最大上传字节", type="int", default=20971520),
            _f(key="upload_allowed_roots", label="上传允许根目录", type="list", default=[]),
        ],
    ),
    GroupSpec(
        key="messages",
        title="消息处理",
        description="输入/输出分块、队列、去重。",
        fields=[
            _f(key="max_input_chars", label="最大输入字符", type="int", default=12000),
            _f(key="max_output_chars", label="最大输出字符", type="int", default=3500),
            _f(key="queue_size", label="队列大小", type="int", default=256),
            _f(key="worker_count", label="工作线程数", type="int", default=1),
            _f(key="dedup_ttl_seconds", label="去重 TTL(秒)", type="int", default=86400),
        ],
    ),
    GroupSpec(
        key="storage",
        title="存储",
        description="SQLite 数据库路径。",
        fields=[
            _f(key="database_path", label="数据库路径", type="str", default="./data/bridge.db"),
        ],
    ),
    GroupSpec(
        key="logging",
        title="日志",
        description="日志级别、文件、轮转。",
        fields=[
            _f(key="level", label="级别", type="enum", default="INFO",
               enum_values=["DEBUG", "INFO", "WARNING", "ERROR"]),
            _f(key="file", label="日志文件", type="str", default="./logs/bridge.log"),
            _f(key="max_bytes", label="最大字节", type="int", default=10485760),
            _f(key="backup_count", label="备份数量", type="int", default=5),
        ],
    ),
    GroupSpec(
        key="task_dispatch",
        title="任务派发(主/子会话)",
        description="主会话拆任务、子会话按类型隔离执行的 skill 配置。",
        fields=[
            _f(key="enabled", label="启用", type="bool", default=True),
            _f(key="task_dir", label="任务参数目录", type="str", default="./workfile/tasks"),
            _f(key="report", label="汇报模式", type="enum", default="success_fail_only",
               enum_values=["success_fail_only", "full"]),
            _f(key="main_skills", label="主会话 skill", type="list", default=[],
               help="注入主会话的调度协议 skill（不配则用默认：kanzi-main-protocol + index + highfreq）"),
            _f(key="common_skills", label="子会话公共 skill", type="list", default=[],
               help="所有子会话共用的执行协议 skill（不配则用默认：task-execution-protocol + index + studio-mcp + project-switch + highfreq）"),
            _f(key="session_types", label="子会话类型 skill 映射", type="dict", default={},
               help="子会话类型 → 该类型注入的专属 skill 列表，如 create-node: [kanzi-node-create, ...]。每个类型自动叠加公共 skill"),
        ],
    ),
]

# 顶层顺序（决定导航顺序；web 组排最前）
GROUP_KEYS: list[str] = [g.key for g in GROUPS]


def group_by_key(key: str) -> GroupSpec | None:
    for g in GROUPS:
        if g.key == key:
            return g
    return None
