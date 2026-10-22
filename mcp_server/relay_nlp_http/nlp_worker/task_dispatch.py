"""Task dispatcher: 主会话派发 Kanzi 创建/修改任务到按类型隔离的子会话。

设计（2026-10-21 老隋要求）：
- 主会话读需求/步骤、生成任务参数写入 workfile/tasks/<类型>/<任务id>.json（参数不进主会话上下文）
- 主会话调 task_dispatch(type, task_file) 派发 —— 主上下文只有类型+路径
- nlp_worker 按类型维护子会话池（每个类型一个独立 SDK session，独立上下文）
- 子会话读任务文件、调 kz_*（参数全在子会话），完成后回报 ✅/❌+原因
- skill 注入：子会话创建时注入「通用支撑 + 该类型专属」的 skill 子集
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from copilot import ToolInvocation, define_tool
from pydantic import BaseModel, Field

log = logging.getLogger("nlp-worker.task")

# 子会话类型 → 该类型加载的专属 skill（相对 skills 根目录；通用支撑另行注入）
TASK_SKILLS: dict[str, list[str]] = {
    "create-node": [
        "kanzi-node-create",
        "kanzi-layout",
        "kanzi-textblock",
        "kanzi-transform",
        "kanzi-prefab",
    ],
    "create-state-machine": ["kanzi-state-manager", "kanzi-trigger"],
    "create-property": ["kanzi-proptype", "kanzi-prop-set"],
    "create-resource": ["kanzi-resource-create", "kanzi-resource-set", "kanzi-asset-create"],
    "localization": ["kanzi-localization"],
    "texture": ["kanzi-asset-create"],
    "animation": ["kanzi-animation"],
    "binding": ["kanzi-binding"],
    "alias": ["kanzi-alias"],
    "shader": ["kanzi-shader", "kanzi-material-brush"],
    "save-export": ["kanzi-save-export"],
}

# 所有子会话共用的通用支撑 skill（导航 + 总入口 + 工程切换 + 高频属性 + 子会话执行协议）
COMMON_SKILLS = [
    "kanzi-task-execution-protocol",  # 子会话执行协议（必装）
    "kanzi-refresh",                  # 创建后刷新工程树/截图前刷 Preview（执行必用）
    "kanzi-skills-index",
    "kanzi-studio-mcp",
    "kanzi-project-switch",
    "kanzi-properties-highfreq",
]

# 主会话专用 skill（只注入主会话；与子会话协议/类型 skill 严格隔离，
# 防止主会话被诱导自己执行 Kanzi 操作）
MAIN_SKILLS = [
    "kanzi-main-protocol",      # 主会话调度协议（必装）
    "kanzi-skills-index",
    "kanzi-properties-highfreq",
]

# 默认任务参数目录（相对 working_directory；config 可覆盖）
DEFAULT_TASK_DIR = "workfile/tasks"


# task_dispatch 工具的参数模型（必须模块级 —— SDK define_tool 用 get_type_hints
# 解析 handler 注解，局部类会导致 NameError）
class TaskDispatchParams(BaseModel):
    type: str = Field(description=f"任务类型: {', '.join(sorted(TASK_SKILLS))}")
    objective: str = Field(description="任务目标描述（不含具体参数值）")
    constraints: list[str] = Field(default_factory=list, description="执行约束列表（命名规则/图片映射等，不含参数值）")
    data_source: str | None = Field(default=None, description="数据源路径（xlsx/文本/kanzi 资源路径），子会话从这提取具体参数")
    project: str | None = Field(default=None, description="涉及工程名")
    conversation_key: str = Field(default="default", description="当前对话 key（一般省略）")
    instructions: str | None = Field(default=None, description="附加执行要求（可选）")


@dataclass
class TaskDispatchConfig:
    enabled: bool = True
    task_dir: str = DEFAULT_TASK_DIR
    # 汇报模式：success_fail_only = 只报成功/失败原因（不回过程）
    report: str = "success_fail_only"
    # 主会话注入的 skill（config 配；不配则用代码默认 MAIN_SKILLS）
    main_skills: list[str] = field(default_factory=list)
    # 所有子会话共用的 skill（config 配；不配则用代码默认 COMMON_SKILLS）
    common_skills: list[str] = field(default_factory=list)
    # 子会话类型 → 该类型注入的专属 skill（覆盖默认 TASK_SKILLS）
    session_types: dict[str, list[str]] = field(default_factory=dict)

    def main_skills_for(self) -> list[str]:
        """主会话 skill：config 优先，没有则用代码默认 MAIN_SKILLS。"""
        return self.main_skills or list(MAIN_SKILLS)

    def common_skills_for(self) -> list[str]:
        """所有子会话公共 skill：config 优先，没有则用代码默认 COMMON_SKILLS。"""
        return self.common_skills or list(COMMON_SKILLS)

    def skills_for(self, task_type: str) -> list[str]:
        """取某类型的专属 skill：config 优先，没有则用代码默认。"""
        if task_type in self.session_types:
            return self.session_types[task_type]
        return TASK_SKILLS.get(task_type, [])


class TaskDispatcher:
    """管理子会话池 + 派发任务 + 读取任务文件。"""
    def __init__(self, config: TaskDispatchConfig, runtime: Any, skills_root: Path | None = None):
        self.config = config
        self.runtime = runtime
        self.skills_root = skills_root
        # 每个对话的每种类型一个子会话：{ (conversation_key, type): session_key }
        self._sessions: dict[tuple[str, str], str] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    # ---- 类型 ----------------
    def _all_types(self) -> set[str]:
        return set(TASK_SKILLS) | set(self.config.session_types)

    def _valid_type(self, task_type: str) -> bool:
        return task_type in self._all_types()

    # ---- 任务文件 ----
    def task_dir(self, conversation_key: str) -> Path:
        base = Path(self.config.task_dir)
        if not base.is_absolute():
            base = Path(self.runtime.config.copilot.working_directory) / base
        return base / conversation_key

    def ensure_task_dir(self, conversation_key: str) -> Path:
        d = self.task_dir(conversation_key)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_task(self, conversation_key: str, task_type: str, payload: dict) -> Path:
        d = self.ensure_task_dir(conversation_key) / task_type
        d.mkdir(parents=True, exist_ok=True)
        # 任务文件名：自增序号 + 时间戳
        seq = len(list(d.glob("*.json"))) + 1
        path = d / f"task-{seq:03d}-{os.getpid()}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path

    def read_task(self, path_str: str) -> dict | None:
        try:
            return json.loads(Path(path_str).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("读取任务文件失败 %s: %s", path_str, exc)
            return None

    # ---- 子会话 ----
    def _session_key(self, conversation_key: str, task_type: str) -> str:
        return f"task:{task_type}:{conversation_key}"

    async def get_sub_session(self, conversation_key: str, task_type: str):
        """拿（或建）该对话+类型的子会话。返回 (session_key, is_new)。"""
        skey = self._session_key(conversation_key, task_type)
        lock = self._locks.setdefault(skey, asyncio.Lock())
        async with lock:
            # runtime.sessions 里有没有现成的
            existing = self.runtime.sessions.get(skey)
            if existing is not None:
                return skey, False
            # 尝试恢复持久化的
            try:
                mapping = self.runtime.store.get(skey)
                if mapping:
                    await self.runtime._resume(skey, mapping.session_id)
                    return skey, False
            except Exception:
                pass
            # 新建（注入该类型 skill 由 runtime 侧处理，见 copilot_runtime）
            await self.runtime._create(skey)
            return skey, True

    async def _emit(self, text: str) -> None:
        """子会话进度/创建/完成消息 → 转发到 relay（nlp_worker 注入的 callback）。"""
        cb = getattr(self.runtime, "_progress_callback", None)
        if cb is not None:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(text)
                else:
                    cb(text)
            except Exception:  # noqa: BLE001
                pass

    async def dispatch(
        self,
        conversation_key: str,
        task_type: str,
        objective: str,
        constraints: list[str] | None = None,
        data_source: str | None = None,
        project: str | None = None,
        instructions: str | None = None,
    ) -> str:
        """派发任务到子会话执行，返回结果文本。

        主会话只传 objective/constraints/data_source/project（描述单，无参数值）。
        子会话从数据源自行提取具体参数并执行。
        """
        if not self._valid_type(task_type):
            valid = ", ".join(sorted(self._all_types()))
            return f"❌ 未知任务类型: {task_type}。可用类型: {valid}"

        created = await self.get_sub_session(conversation_key, task_type)
        skey = created[0] if isinstance(created, tuple) else created
        new_session = created[1] if isinstance(created, tuple) else False

        # 子会话创建/复用消息（必发）
        if new_session:
            await self._emit(f"🔧 创建子会话：{task_type}")
        else:
            await self._emit(f"🔁 复用子会话：{task_type}")

        # 构造给子会话的 prompt：读描述单 → 读数据源取参数 → 生成命令序列 → 分组执行
        spec_lines = [f"任务类型: {task_type}", f"目标: {objective}"]
        if project:
            spec_lines.append(f"工程: {project}")
        if constraints:
            spec_lines.append("约束:")
            spec_lines += [f"  - {c}" for c in constraints]
        if data_source:
            spec_lines.append(f"数据源: {data_source}")
        if instructions:
            spec_lines.append(f"附加要求: {instructions}")
        spec_text = "\n".join(spec_lines)

        prompt = (
            f"你是一个 Kanzi {task_type} 子会话（上下文与主会话隔离）。\n"
            f"收到任务描述单：\n{spec_text}\n\n"
            "执行方式：\n"
            "0. **必须严格遵守已注入你 system prompt 的 kanzi-task-execution-protocol（执行协议），不得违反其中任何铁律。**\n"
            "1. 按目标/约束从数据源提取具体参数（名称/ID/值/路径），参数只在本会话产生，不向主会话要。\n"
            "2. 先输出你的命令序列计划（步骤号/目标/工具/方法参数/预期/验证点），大输出落盘+grep，然后严格按计划执行。\n"
            "3. 按同工程+同类+可验证边界分组，用 kz_* 工具逐组执行。\n"
            "4. 完成后只回报：✅ 成功（新建对象数量+清单路径）或 ❌ 失败（哪步、原因）。\n"
            "5. 不要复述完整参数/返回值/命令序列。\n"
        )
        async def _sub_progress(text: str) -> None:
            # 子会话进度转发（send 内部已按 progress_min_interval 节流，不刷屏）
            await self._emit(f"[{task_type} 子会话] {text}")

        try:
            result = await self.runtime.send(skey, prompt, on_progress=_sub_progress)
            stripped = result.strip() or "✅ 完成"
            if stripped.startswith("✅") or stripped.startswith("✔"):
                await self._emit(f"✅ 子会话完成：{task_type}")
            else:
                await self._emit(f"❌ 子会话失败：{task_type}")
            return stripped
        except Exception as exc:
            await self._emit(f"❌ 子会话异常：{task_type} {exc}")
            return f"❌ 子会话执行失败: {exc}"

    # ---- 工具 ----
    def build_tool(self):
        """注册 task_dispatch 工具（用 SDK define_tool 包装成 Tool）。"""
        async def handler(params: TaskDispatchParams, invocation: ToolInvocation) -> str:
            try:
                # 用主会话 session_id 反查主会话 key（没有就用 default）
                conv = params.conversation_key or self.runtime.key_for_session_id(
                    invocation.session_id
                )
                return await self.dispatch(
                    conv,
                    params.type,
                    params.objective,
                    params.constraints,
                    params.data_source,
                    params.project,
                    params.instructions,
                )
            except Exception as exc:
                return f"❌ 派发失败: {exc}"

        return define_tool(
            name="task_dispatch",
            description=(
                "把 Kanzi 任务派发给指定类型的子会话执行（子会话上下文与主会话隔离）。"
                "主会话只传客观描述（objective/constraints/data_source/project，不含具体参数值）；"
                "子会话从数据源自行提取参数、生成命令序列并执行，完成后回报成功/失败原因。"
                "注意：执行步骤必须顺序派发，一次只派发一个子任务，等上一个完成后才派下一个。"
            ),
            params_type=TaskDispatchParams,
            handler=handler,
            skip_permission=True,
            defer="never",
        )
