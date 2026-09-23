#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tasks.py — 异步长任务管理（升级 / 部署的进度查询）

长任务在后台线程跑，前端轮询 /api/task/<id> 拿进度。
"""
import threading
import time
import uuid

# {task_id: {...}}
_TASKS: dict = {}
_LOCK = threading.Lock()
_KEEP = 50          # 最多保留最近 50 条任务记录


class Task:
    def __init__(self, kind: str, title: str):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.title = title
        self.status = "pending"          # pending / running / success / failed
        self.step = ""
        self.percent = 0
        self.detail = ""
        self.log: list[str] = []
        self.created = time.time()
        self.finished = 0.0
        self._lock = threading.Lock()

    def update(self, step: str, msg: str = "", percent: int = None):
        with self._lock:
            if step:
                self.step = step
            if msg:
                self.detail = msg
                self.log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
                if len(self.log) > 200:
                    del self.log[:-200]
            if percent is not None:
                self.percent = max(0, min(100, int(percent)))

    def done(self, ok: bool, detail: str = ""):
        with self._lock:
            self.status = "success" if ok else "failed"
            self.percent = 100
            if detail:
                self.detail = detail
                self.log.append(f"[{time.strftime('%H:%M:%S')}] {detail}")
            self.finished = time.time()

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "id": self.id, "kind": self.kind, "title": self.title,
                "status": self.status, "step": self.step,
                "percent": self.percent, "detail": self.detail,
                "log": list(self.log[-50:]),
                "created": self.created, "finished": self.finished,
                "running": self.status in ("pending", "running"),
            }


def _gc():
    """清理老任务，避免内存无限增长。"""
    with _LOCK:
        if len(_TASKS) <= _KEEP:
            return
        items = sorted(_TASKS.items(), key=lambda kv: kv[1].created)
        for tid, _ in items[: len(_TASKS) - _KEEP]:
            _TASKS.pop(tid, None)


def start(kind: str, title: str, fn) -> Task:
    """起一个后台任务。fn(task) 是任务体，内部应调 task.update()/done()。"""
    task = Task(kind, title)
    with _LOCK:
        _TASKS[task.id] = task
    _gc()

    def runner():
        task.status = "running"
        try:
            fn(task)
            if task.status == "running":
                task.done(True)
        except Exception as e:                               # noqa: BLE001
            task.done(False, f"异常: {e}")

    threading.Thread(target=runner, daemon=True,
                     name=f"task-{kind}-{task.id}").start()
    return task


def get(task_id: str) -> dict | None:
    with _LOCK:
        t = _TASKS.get(task_id)
    return t.to_dict() if t else None


def latest(limit: int = 10) -> list:
    with _LOCK:
        items = sorted(_TASKS.values(), key=lambda t: t.created, reverse=True)
    return [t.to_dict() for t in items[:limit]]


def any_running() -> bool:
    """是否有长任务在跑（升级/重启期间禁止并发操作）。"""
    with _LOCK:
        return any(t.status in ("pending", "running") for t in _TASKS.values())
