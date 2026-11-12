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
class SessionTypeSpec:
    """子会话类型配置：专属 skill 列表 + 可选模型 id。

    兼容旧写法 `session_types: {type: [skill1, skill2]}`：
    解析时 list → skills，model 缺省。
    """
    skills: list[str] = field(default_factory=list)
    model: str | None = None

    @classmethod
    def from_config(cls, value: Any) -> "SessionTypeSpec":
        if isinstance(value, list):
            return cls(skills=[str(s) for s in value])
        if isinstance(value, dict):
            skills = value.get("skills") or []
            if not isinstance(skills, list):
                skills = [str(skills)]
            return cls(
                skills=[str(s) for s in skills],
                model=value.get("model"),
            )
        raise ValueError(f"session_types 条目必须是 list 或 dict，收到: {value!r}")


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
    # 子会话默认模型 id：子会话类型没指定 model 时用它；
    # 这个也没配 → 用 copilot.default_model。
    default_model: str | None = None
    # 子会话类型 → 该类型注入的专属 skill + 可选模型（覆盖默认 TASK_SKILLS）
    # 兼容旧写法 dict[str, list[str]]：Any 类型 + _normalize_types 运行时转换
    session_types: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # 旧写法 dict[str, list[str]] → SessionTypeSpec 转换（直接构造时生效）
        self._normalize_types()

    def _normalize_types(self) -> None:
        for k, v in list(self.session_types.items()):
            if not isinstance(v, SessionTypeSpec):
                self.session_types[k] = SessionTypeSpec.from_config(v)

    def main_skills_for(self) -> list[str]:
        """主会话 skill：config 优先，没有则用代码默认 MAIN_SKILLS。"""
        return self.main_skills or list(MAIN_SKILLS)

    def common_skills_for(self) -> list[str]:
        """所有子会话公共 skill：config 优先，没有则用代码默认 COMMON_SKILLS。"""
        return self.common_skills or list(COMMON_SKILLS)

    def skills_for(self, task_type: str) -> list[str]:
        """取某类型的专属 skill：config 优先，没有则用代码默认。"""
        self._normalize_types()
        spec = self.session_types.get(task_type)
        if spec is not None and spec.skills:
            return spec.skills
        return TASK_SKILLS.get(task_type, [])

    def model_for(self, task_type: str) -> str | None:
        """取某类型的模型 id：config 指定则返回，没有返回 None（调用方用默认模型）。"""
        self._normalize_types()
        spec = self.session_types.get(task_type)
        if spec is not None:
            return spec.model
        return None

    def sub_session_default_model(self) -> str | None:
        """子会话默认模型 id（未配返回 None → 调用方用 copilot.default_model）。"""
        return self.default_model


class TaskDispatcher:
    """管理子会话池 + 派发任务 + 读取任务文件。"""
    def __init__(self, config: TaskDispatchConfig, runtime: Any, skills_root: Path | None = None):
        self.config = config
        self.runtime = runtime
        self.skills_root = skills_root
        # 每个对话的每种类型一个子会话：{ (conversation_key, type): session_key }
        self._sessions: dict[tuple[str, str], str] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        # 全局 in-flight（2026-11-06 异步派发版）：Kanzi 单工程，同一时间只允许
        # 一个任务在子会话执行。存 conversation_key；None = 空闲。
        self._inflight: str | None = None
        # 任务状态详情（供 task_status 查询）：
        # { conversation_key: {type, started_at, status: busy/done/failed, result} }
        self._task_status: dict[str, dict[str, Any]] = {}

    # ---- 全局 in-flight 保护（一次只执行一个任务）----
    def _mark_busy(self, conv: str) -> bool:
        """尝试占用 in-flight。成功占用返回 True；已有任务在跑返回 False。"""
        if self._inflight is not None:
            return False
        self._inflight = conv
        return True

    def _release(self, conv: str) -> None:
        """释放 in-flight（仅当是自己占用的才释放，防误放别人的）。"""
        if self._inflight == conv:
            self._inflight = None

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

    # ---- 任务进度落盘（2026-11-06：主会话恢复进度不从头开始）----
    def _plan_path(self, conversation_key: str) -> Path:
        """对话的任务进度文件：workfile/plan/<conv>.json。"""
        base = Path(self.config.task_dir).parent / "plan"
        if not base.is_absolute():
            base = Path(self.runtime.config.copilot.working_directory) / base
        return base / f"{conversation_key}.json"

    def read_plan(self, conversation_key: str) -> dict | None:
        """读对话的任务进度（steps 列表 + current 进度）。不存在返回 None。"""
        try:
            return json.loads(self._plan_path(conversation_key).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def update_plan(self, conversation_key: str, task_type: str, status: str, result: str | None = None) -> None:
        """追加/更新一条任务到进度文件：status ∈ running/done/failed/cancelled。"""
        p = self._plan_path(conversation_key)
        p.parent.mkdir(parents=True, exist_ok=True)
        plan = self.read_plan(conversation_key) or {"conversation": conversation_key, "steps": []}
        steps = plan.setdefault("steps", [])
        # 找同名+同目标的进行中条目（更新）；没有则追加
        idx = next((i for i, s in enumerate(steps) if s.get("type") == task_type
                    and s.get("status") in ("running", "pending")), None)
        entry = {"type": task_type, "status": status, "updated_at": int(asyncio.get_event_loop().time())}
        if result is not None:
            entry["result"] = result[:300]
        if idx is not None:
            steps[idx].update(entry)
        else:
            steps.append(entry)
        p.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("进度落盘 [%s]: %s %s", conversation_key, task_type, status)

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

    async def _emit(self, text: str, kind: str = "progress") -> None:
        """子会话消息 → 转发到 relay（nlp_worker 注入的 callback）。

        kind:
          - "event"    : 创建/完成/失败/异常 —— 独立飞书消息（必发，不合并）
          - "progress" : 工具调用进度 —— 合并进滚动进度条（节流不刷屏）
        """
        cb = getattr(self.runtime, "_progress_callback", None)
        if cb is not None:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(text, kind)
                else:
                    cb(text, kind)
            except Exception:  # noqa: BLE001
                pass

    async def _execute(
        self,
        conversation_key: str,
        task_type: str,
        objective: str,
        constraints: list[str] | None = None,
        data_source: str | None = None,
        project: str | None = None,
        instructions: str | None = None,
    ) -> str:
        """同步执行任务到子会话，返回结果文本（后台 _run_task 调用）。

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
            await self._emit(f"🔧 创建子会话：{task_type}", kind="event")
        else:
            await self._emit(f"🔁 复用子会话：{task_type}", kind="event")

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
            # 子会话工具调用进度：合并进滚动进度条（send 内部已节流，不刷屏）
            await self._emit(f"[{task_type} 子会话] {text}", kind="progress")

        try:
            result = await self.runtime.send(skey, prompt, on_progress=_sub_progress)
            stripped = result.strip()
            if not stripped:
                # 子会话返回空(静默结束、无最终文本) = 执行失败 (2026-10-22 老隋要求)
                await self._emit(f"❌ 子会话失败：{task_type}(未返回执行结果)", kind="event")
                return f"❌ {task_type} 子会话执行失败: 未返回执行结果文本"
            # 原样透传子会话文本 → 主会话自行判断成败(代码不做前缀判断, 避免误判)
            # 同时把子会话实际返回文本发到飞书(event), 用户直接看到结果, 不依赖主会话转述
            await self._emit(f"📤 子会话回报：{task_type}\n{stripped[:500]}", kind="event")
            return stripped
        except Exception as exc:
            await self._emit(f"❌ 子会话异常：{task_type} {exc}", kind="event")
            return f"❌ {task_type} 子会话执行异常: {exc}"

    async def _run_task(
        self,
        conversation_key: str,
        task_type: str,
        objective: str,
        constraints: list[str] | None = None,
        data_source: str | None = None,
        project: str | None = None,
        instructions: str | None = None,
    ) -> None:
        """后台任务：执行子会话 → 释放 in-flight → 回报注入主会话唤醒。

        子会话完成（成功/失败/异常/取消）后，把回报文本作为消息注入主会话
        （runtime.send 主会话 key），主会话 AI 收到后自行判断下一步
        （继续派下一个 / 收尾汇报 / 续跑被取消的任务），实现主动回报闭环。
        """
        result = ""
        try:
            result = await self._execute(
                conversation_key, task_type, objective, constraints,
                data_source, project, instructions,
            )
        except asyncio.CancelledError:
            # 任务被取消（task_cancel）：标记取消，不注入回报
            result = f"🛑 {task_type} 任务已取消"
            try:
                await self._emit(f"🛑 任务已取消：{task_type}", kind="event")
            except Exception:
                pass
        except Exception as exc:
            result = f"❌ {task_type} 子会话执行异常: {exc}"
            try:
                await self._emit(f"❌ 子会话异常：{task_type} {exc}", kind="event")
            except Exception:
                pass
        finally:
            # 更新任务状态（先于释放锁，保证 task_status 能读到结果）+ 进度落盘
            if conversation_key in self._task_status:
                self._task_status[conversation_key].update(
                    status="failed" if result.startswith("❌") else "done",
                    result=result[:500],
                    finished_at=asyncio.get_event_loop().time(),
                )
            self.update_plan(
                conversation_key, task_type,
                "failed" if result.startswith("❌") else "done",
                result,
            )
            self._release(conversation_key)

        # 回报注入主会话（主动唤醒）：主会话 AI 看到回报后继续决策。
        # 注意：此时 in-flight 已释放，主会话被唤醒后若派发下一个任务不会被误拒。
        # 取消场景不注入（task_cancel 已直接回复用户）。
        if not result.startswith("🛑"):
            # 注入前发明确提示：用户立即知道主会话被唤醒在干活（2026-11-06）
            try:
                await self._emit(
                    f"🔔 子会话回报已收到，主会话正在继续处理"
                    f"（检查完成度/派发下一步）…",
                    kind="event",
                )
            except Exception:
                pass

            # 注入 send 必须传 on_progress：否则主会话处理期间的全部中间输出
            # （💬/🧠/✍️/↪️）都被 send 内部丢弃（_progress_on=False），用户看不到。
            async def _inject_progress(text: str) -> None:
                await self._emit(f"[主会话] {text}", kind="progress")

            try:
                await self.runtime.send(
                    conversation_key,
                    f"子会话回报（{task_type} 已完成）：\n{result}",
                    on_progress=_inject_progress,
                )
            except Exception as exc:
                log.warning("注入主会话回报失败 [%s]: %s", conversation_key, exc)

    async def submit(
        self,
        conversation_key: str,
        task_type: str,
        objective: str,
        constraints: list[str] | None = None,
        data_source: str | None = None,
        project: str | None = None,
        instructions: str | None = None,
    ) -> str:
        """异步派发入口（秒回，不阻塞）：占用 in-flight → 后台执行 → 立即返回。

        根治 task_dispatch 同步等待导致的外部工具 1800s 超时：handler 秒回，
        子会话在后台执行，完成后主动回报注入主会话。
        """
        if not self._valid_type(task_type):
            valid = ", ".join(sorted(self._all_types()))
            return f"❌ 未知任务类型: {task_type}。可用类型: {valid}"

        if not self._mark_busy(conversation_key):
            return (
                "⏳ 上一个任务还在执行中（Kanzi 单工程同一时间只执行一个任务）。"
                "等子会话完成回报后再派发下一个任务。"
            )

        # 记录任务状态（供 task_status 查询）+ 进度落盘
        self._task_status[conversation_key] = {
            "type": task_type,
            "objective": objective[:80],
            "started_at": asyncio.get_event_loop().time(),
            "status": "busy",
            "result": None,
        }
        self.update_plan(conversation_key, task_type, "running")

        try:
            asyncio.create_task(
                self._run_task(
                    conversation_key, task_type, objective, constraints,
                    data_source, project, instructions,
                )
            )
        except Exception as exc:  # noqa: BLE001
            self._release(conversation_key)
            return f"❌ 派发失败: {exc}"

        return (
            f"⏳ 已派发 {task_type} 任务给子会话执行（后台运行）。\n"
            "完成后我会收到子会话回报并继续。\n"
            "⚠️ 子会话执行期间可随时：\n"
            "  - 回复「暂停」→ 我调用 task_cancel 暂停当前任务（进度已落盘，可续跑）\n"
            "  - 回复「取消」→ 我调用 task_cancel 取消当前任务\n"
            "  - 描述修改需求 → 我调整任务描述单后重新派发（进度不丢）\n"
        )

    # ---- 工具 ----
    def _status_text(self, conv: str) -> str:
        """生成当前任务状态文本（供 task_status 工具返回）。"""
        st = self._task_status.get(conv)
        if st is None:
            return "🟢 空闲：当前没有任务在执行，可以派发新任务。"
        if st["status"] == "busy":
            elapsed = asyncio.get_event_loop().time() - st["started_at"]
            return (
                f"🟡 任务执行中：{st['type']}（已耗时 {elapsed:.0f}s）\n"
                f"目标：{st['objective']}\n"
                f"状态：子会话后台执行中，等待完成回报。"
            )
        return (
            f"🟢 空闲：上一个任务已完成。\n"
            f"类型：{st['type']} 结果：{'✅' if st['status'] == 'done' else '❌'} "
            f"{st.get('result', '')[:200]}"
        )

    def build_tool(self):
        """注册 task_dispatch + task_status 工具（用 SDK define_tool 包装成 Tool）。"""
        async def status_handler(params: Any, invocation: ToolInvocation) -> str:
            conv = getattr(params, "conversation_key", None) or self.runtime.key_for_session_id(
                invocation.session_id
            )
            return self._status_text(conv)

        status_tool = define_tool(
            name="task_status",
            description=(
                "查询当前对话的任务执行状态（busy 执行中 / idle 空闲）和进度。"
                "非必须轮询；主会话一般等子会话回报即可。"
            ),
            params_type=TaskDispatchParams,
            handler=status_handler,
            skip_permission=True,
            defer="never",
        )

        async def cancel_handler(params: Any, invocation: ToolInvocation) -> str:
            """暂停/取消当前任务：abort 子会话 + 释放 in-flight + 进度标记 cancelled。"""
            conv = getattr(params, "conversation_key", None) or self.runtime.key_for_session_id(
                invocation.session_id
            )
            if self._inflight != conv:
                return "🟢 当前没有任务在执行（或任务已完成），无需取消。"
            # 找到当前正在跑的 task 类型（从 _task_status）
            st = self._task_status.get(conv)
            task_type = st.get("type", "未知") if st else "未知"
            skey = self._session_key(conv, task_type)
            try:
                await self.runtime.cancel(skey)
            except Exception as exc:
                log.warning("取消子会话失败 [%s]: %s", conv, exc)
            # 释放 + 标记 cancelled + 进度落盘
            self._release(conv)
            if st is not None:
                st["status"] = "cancelled"
                st["result"] = "已取消"
            self.update_plan(conv, task_type, "cancelled", "用户取消/暂停")
            await self._emit(f"🛑 任务已取消：{task_type}（进度已保存，可后续续跑）", kind="event")
            return f"🛑 已取消任务：{task_type}。进度已落盘保存，需要时可重新派发续跑。"

        cancel_tool = define_tool(
            name="task_cancel",
            description=(
                "暂停/取消当前正在执行的子会话任务（用户要求暂停/取消时调用）。"
                "取消后进度落盘保存，可重新派发续跑。当前无任务时返回提示。"
            ),
            params_type=TaskDispatchParams,
            handler=cancel_handler,
            skip_permission=True,
            defer="never",
        )

        async def handler(params: TaskDispatchParams, invocation: ToolInvocation) -> str:
            try:
                # 用主会话 session_id 反查主会话 key（没有就用 default）
                conv = params.conversation_key or self.runtime.key_for_session_id(
                    invocation.session_id
                )
                return await self.submit(
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

        dispatch_tool = define_tool(
            name="task_dispatch",
            description=(
                "把 Kanzi 任务派发给指定类型的子会话执行（子会话上下文与主会话隔离）。"
                "主会话只传客观描述（objective/constraints/data_source/project，不含具体参数值）；"
                "子会话从数据源自行提取参数、生成命令序列并执行。"
                "异步派发：本工具立即返回（不阻塞），子会话在后台执行；"
                "子会话完成后会主动回报给主会话（注入消息），主会话收到回报后再派发下一个任务。"
                "同一时间只能有一个任务在执行：若返回『上一个任务还在执行中』，说明有任务未完成。"
                "用户要求暂停/取消时调用 task_cancel。任务进度自动落盘，主会话可随时查 task_status。"
            ),
            params_type=TaskDispatchParams,
            handler=handler,
            skip_permission=True,
            defer="never",
        )
        return [dispatch_tool, status_tool, cancel_tool]
