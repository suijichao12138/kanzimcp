#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_api.py — 静态代码检查（工程管理 + 检查 + 报告）

数据布局（在 deployer 安装目录下）：
    data/projects/<proj_id>/
        meta.json      工程名 / 状态 / 时间 / 统计
        upload.zip     原始上传包
        src/           解压后的源码
        out/           报告（report.html / coverage.html / summary.md）
    data/tools/cppCheck.exe    全局共享的检查工具（部署产物）

设计要点：
  1. 检查工具是**外部** exe，本模块只负责调用；源码在仓库 mcp_server/cppCheck/，
     由 deployer 的 artifacts 机制（cppcheck_tool）编译成 dist/cppCheck.exe
  2. 必须先部署工具才能检查（部署环境不保证有 Python）
  3. 报告用 inline 方式下发，浏览器直接渲染，不触发下载
  4. 删除走回收站（_backup/projects_trash/），可找回
"""
import io
import json
import re
import shutil
import subprocess
import threading
import time
import uuid
import zipfile
from pathlib import Path

from . import tasks

# ── 安全限制 ──
_MAX_ZIP_BYTES = 200 * 1024 * 1024        # 上传的 zip 上限
_MAX_UNZIP_BYTES = 500 * 1024 * 1024      # 解压后上限（防 zip 炸弹）
_MAX_FILES = 20000                        # 文件数上限
_ALLOWED_SUFFIX = {".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx"}
_TOOL_NAME = "cppCheck.exe"
_SCAN_TIMEOUT_S = 60 * 60          # 单次检查整体超时（1 小时），到点强杀
_CREATE_LOCK = threading.Lock()     # 新建工程时串行化「查重 + 建目录」

# 报告文件名白名单（防路径穿越）
_REPORT_FILES = {
    "report.html": "text/html; charset=utf-8",
    "coverage.html": "text/html; charset=utf-8",
    "summary.md": "text/markdown; charset=utf-8",
    "scan_result.json": "application/json; charset=utf-8",
}


def _ok(data=None, **kw):
    body = {"ok": True}
    if data is not None:
        body["data"] = data
    body.update(kw)
    return 200, body


def _err(msg: str, code: int = 400, extra: dict | None = None):
    body = {"ok": False, "error": msg}
    if extra:
        body.update(extra)
    return code, body


# ══════════════════════ 路径与元数据 ══════════════════════

def _projects_root(ctx) -> Path:
    d = ctx.paths.projects
    d.mkdir(parents=True, exist_ok=True)
    return d


def _proj_dir(ctx, proj_id: str) -> Path:
    p = _projects_root(ctx) / proj_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _meta_path(d: Path) -> Path:
    return d / "meta.json"


def _load_meta(d: Path) -> dict:
    p = _meta_path(d)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                    # noqa: BLE001
        return {}


def _save_meta(d: Path, meta: dict) -> None:
    meta["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _meta_path(d).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_id(proj_id: str) -> str | None:
    """工程 id 只允许字母数字下划线连字符（防路径穿越）。"""
    if not proj_id or proj_id in (".", ".."):
        return None
    if not re.match(r"^[A-Za-z0-9_-]{1,64}$", proj_id):
        return None
    return proj_id


def _safe_name(name: str) -> str | None:
    """工程名：允许中英文数字空格下划线连字符，≤50 字符。"""
    name = (name or "").strip()
    if not name or len(name) > 50:
        return None
    if re.search(r'[/\\:*?"<>|\x00-\x1f]', name):
        return None
    return name


def _tool_path(ctx) -> Path:
    return Path(ctx.paths.scan_tools) / _TOOL_NAME


def _kill_tree(proc) -> None:
    """强杀进程及其子进程。

    cppCheck.exe 会拉起 clang-tidy 等子进程，只 kill 父进程会留下
    孤儿进程继续吃 CPU，所以 Windows 下用 taskkill /T。
    """
    import os as _os
    import signal as _sig
    try:
        if _os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=30)
        else:
            _os.killpg(_os.getpgid(proc.pid), _sig.SIGKILL)
    except Exception:                                # noqa: BLE001
        try:
            proc.kill()
        except Exception:                            # noqa: BLE001
            pass


def _dir_size(p: Path) -> int:
    total = 0
    if not p.exists():
        return 0
    for f in p.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def _trash_dir(ctx, path: Path):
    """删除目录：优先移到 _backup/projects_trash/，失败才直接删。"""
    try:
        base = Path(ctx.paths.backup) / "projects_trash"
        base.mkdir(parents=True, exist_ok=True)
        dest = base / f"{path.name}.{time.strftime('%Y%m%d_%H%M%S')}"
        path.rename(dest)
    except Exception:                                    # noqa: BLE001
        shutil.rmtree(path, ignore_errors=True)


# ══════════════════════ 列表 ══════════════════════

def list_all(ctx) -> tuple:
    """GET /api/projects — 工程列表。"""
    root = _projects_root(ctx)
    out = []
    try:
        children = sorted(root.iterdir(), key=lambda p: p.name, reverse=True)
    except OSError:
        children = []
    for child in children:
        if not child.is_dir():
            continue
        meta = _load_meta(child)
        if not meta:
            continue
        out_file = child / "out" / "report.html"
        src_dir = child / "src"
        try:
            has_code = src_dir.exists() and any(src_dir.iterdir())
        except OSError:
            has_code = False
        out.append({
            "id": child.name,
            "name": meta.get("name", child.name),
            "status": meta.get("status", "empty"),
            "has_code": has_code,
            "has_report": out_file.exists(),
            "total": meta.get("total", 0),
            "by_tool": meta.get("by_tool", {}),
            "code_size": _dir_size(child / "src"),
            "created_at": meta.get("created_at", ""),
            "updated_at": meta.get("updated_at", ""),
            "error": meta.get("error", ""),
        })
    tool = _tool_path(ctx)
    return _ok({
        "projects": out,
        "tool": {
            "ready": tool.exists(),
            "path": str(tool),
            "size": tool.stat().st_size if tool.exists() else 0,
        },
    })


def detail(ctx, proj_id: str) -> tuple:
    """GET /api/project/detail — 单工程详情。"""
    pid = _safe_id(proj_id)
    if not pid:
        return _err("工程 id 非法")
    d = _projects_root(ctx) / pid
    if not d.is_dir():
        return _err("工程不存在", 404)
    meta = _load_meta(d)
    reports = []
    out_dir = d / "out"
    for name in _REPORT_FILES:
        if (out_dir / name).exists():
            reports.append({
                "name": name,
                "size": (out_dir / name).stat().st_size,
                "inline": name.endswith(".html"),
            })
    meta["reports"] = reports
    meta["code_size"] = _dir_size(d / "src")
    return _ok(meta)


# ══════════════════════ 新建 / 上传 / 删除 ══════════════════════

def create(ctx, body: dict) -> tuple:
    """POST /api/project/create — 新建工程。body: {name}"""
    name = _safe_name((body or {}).get("name", ""))
    if not name:
        return _err("工程名非法（1-50 字符，不含 / \\ : * ? \" < > |）")
    root = _projects_root(ctx)

    # 重名检查 + 创建必须串行：并发两次同名请求会同时通过检查，
    # 结果出现两个同名工程。用一个模块级锁把「查重 + 建目录」圈起来。
    with _CREATE_LOCK:
        try:
            children = [c for c in root.iterdir() if c.is_dir()]
        except OSError:
            children = []
        for child in children:
            m = _load_meta(child)
            if m.get("name") == name:
                return _err("已存在同名工程：%s" % name)
        pid = "proj_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        d = root / pid
        d.mkdir(parents=True, exist_ok=True)
    _save_meta(d, {
        "id": pid,
        "name": name,
        "status": "empty",          # empty / uploaded / scanning / done / failed
        "total": 0,
        "by_tool": {},
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    return _ok({"id": pid, "name": name})


def _extract_zip(dest: Path, data: bytes) -> str | None:
    """安全解压到 dest，返回错误信息或 None。"""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return "不是有效的 zip 文件"

    infos = zf.infolist()
    if len(infos) > _MAX_FILES:
        return "zip 内文件数超过上限（%d）" % _MAX_FILES

    total = 0
    for info in infos:
        total += info.file_size
        if total > _MAX_UNZIP_BYTES:
            return "解压后总大小超过上限（%dMB）" % (_MAX_UNZIP_BYTES // 1024 // 1024)
        nm = info.filename.replace("\\", "/")
        if nm.startswith("/") or ".." in nm.split("/"):
            return "压缩包含非法路径：%s" % info.filename
        if re.match(r"^[A-Za-z]:", nm):
            return "压缩包含绝对路径：%s" % info.filename
        # 跳过符号链接（只取文件类型位，不能用 0o120000 直接与，
        # 那样会连普通文件一起命中并全部跳过）
        if ((info.external_attr >> 16) & 0o170000) == 0o120000:
            continue

    dest.mkdir(parents=True, exist_ok=True)

    # 剥顶层目录前先判断：只有"所有源码文件的第一个路径段完全相同"
    # 才说明用户打的是「整个目录」，此时剥掉这一层是合理的。
    # 若 zip 根目录直接就是源码（a.cpp / src/b.cpp），无条件剥会丢掉
    # 真实目录名，把 src/a.cpp 变成 a.cpp，甚至让两个同名文件互相覆盖。
    first_parts = set()
    for info in infos:
        nm = info.filename.replace("\\", "/")
        if nm.endswith("/"):
            continue
        if Path(nm).suffix.lower() not in _ALLOWED_SUFFIX:
            continue
        segs = [x for x in nm.split("/") if x not in ("", ".")]
        if len(segs) < 2:
            first_parts = None           # 有文件直接在根，不剥
            break
        first_parts.add(segs[0])
    strip_top = bool(first_parts) and len(first_parts) == 1

    copied = 0
    for info in infos:
        nm = info.filename.replace("\\", "/")
        if nm.endswith("/"):
            continue
        if Path(nm).suffix.lower() not in _ALLOWED_SUFFIX:
            continue                    # 只保留源码，其余丢弃
        parts = [p for p in nm.split("/") if p not in ("", ".")]
        if strip_top and len(parts) > 1:
            parts = parts[1:]
        rel = "/".join(parts)
        if not rel:
            continue
        out_path = dest / rel
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            copied += 1
        except Exception:                                # noqa: BLE001
            continue
    if copied == 0:
        return "压缩包里没有找到源码文件（.c/.cpp/.h）"
    return None


def upload(ctx, body: dict) -> tuple:
    """POST /api/project/upload — 上传代码。body: {id, data_b64}"""
    import base64

    pid = _safe_id((body or {}).get("id", ""))
    if not pid:
        return _err("工程 id 非法")
    d = _projects_root(ctx) / pid
    if not d.is_dir():
        return _err("工程不存在", 404)

    b64 = (body or {}).get("data_b64", "")
    if not b64:
        return _err("缺少文件内容")
    try:
        data = base64.b64decode(b64)
    except Exception:                                    # noqa: BLE001
        return _err("base64 解码失败")
    if len(data) > _MAX_ZIP_BYTES:
        return _err("压缩包超过上限（%dMB）" % (_MAX_ZIP_BYTES // 1024 // 1024))

    # 先解压到临时目录，成功后再替换旧代码。
    # 之前是「先删旧代码再解压」，解压失败（zip 损坏 / 没有源码）时
    # 旧代码已经被删掉，用户拿到一个空工程，只能重新上传。
    src_dir = d / "src"
    tmp_dir = d / ("src.__uploading__%s" % uuid.uuid4().hex[:8])
    err = _extract_zip(tmp_dir, data)
    if err:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return _err(err)

    if src_dir.exists():
        shutil.rmtree(src_dir, ignore_errors=True)
    try:
        tmp_dir.rename(src_dir)
    except OSError:
        # Windows 上偶发占用导致 rename 失败，退回复制
        shutil.copytree(tmp_dir, src_dir)
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # 保留原始包，便于排查
    try:
        (d / "upload.zip").write_bytes(data)
    except Exception:                                    # noqa: BLE001
        pass

    files = sum(1 for _ in src_dir.rglob("*") if _.is_file())
    meta = _load_meta(d)
    meta.update({"status": "uploaded", "code_files": files, "error": ""})
    _save_meta(d, meta)
    return _ok({"id": pid, "files": files, "code_size": _dir_size(src_dir)})


def delete(ctx, proj_id: str) -> tuple:
    """POST /api/project/delete — 删除工程（代码 + 报告）。"""
    pid = _safe_id(proj_id or "")
    if not pid:
        return _err("工程 id 非法")
    d = _projects_root(ctx) / pid
    if not d.is_dir():
        return _err("工程不存在", 404)
    # 正在检查的不允许删
    meta = _load_meta(d)
    if meta.get("status") == "scanning":
        return _err("该工程正在检查中，请等结束再删除")
    _trash_dir(ctx, d)
    return _ok({"id": pid, "deleted": True})


# ══════════════════════ 部署工具 ══════════════════════

def start_deploy(ctx, body: dict) -> tuple:
    """POST /api/project/deploy — 部署检查工具（编译 cppCheck.exe）。

    复用 deployer 现有的 artifacts 机制（配置里的 cppcheck_tool），
    编译完成后把产物复制到 data/tools/ 供检查使用。
    """
    from . import api as _api
    try:
        code, out = _api.artifact_build(ctx, {"name": "cppcheck_tool"})
        if code == 200 and out.get("ok"):
            # 起一个轻量任务等待编译结束并把 exe 复制过来
            _watch_build_and_copy(ctx, (out.get("data") or {}).get("id", ""))
        return code, out
    except Exception as e:                               # noqa: BLE001
        return _err("启动部署失败: %s" % e, 500)


def _watch_build_and_copy(ctx, task_id: str) -> None:
    """等待编译任务结束，把编译产物复制到 data/tools/。

    产物路径从 artifacts 配置里推导（cwd + output），不写死目录，
    否则一旦 config.py 里改了 cwd/output，这里会静默失效，
    用户只看到「检查工具未部署」而没有任何线索。
    """
    if not task_id:
        return

    def _log(msg: str) -> None:
        """失败时写进 logs/scan.log，避免静默失败。"""
        try:
            import time as _t
            lp = Path(ctx.paths.logs) / "scan.log"
            lp.parent.mkdir(parents=True, exist_ok=True)
            with open(lp, "a", encoding="utf-8") as f:
                f.write("[%s] %s\n" % (_t.strftime("%Y-%m-%d %H:%M:%S"), msg))
        except Exception:                              # noqa: BLE001
            pass

    def _loop():
        src_base = Path(ctx.paths.root) / "src"
        for _ in range(1200):                            # 最多等 20 分钟
            t = tasks.get(task_id)
            if t and not t["running"]:
                if t["status"] != "success":
                    return
                break
            time.sleep(1)
        else:
            _log("等待编译超时（20 分钟），工具未复制")
            return

        # 从 artifacts 配置推导产物路径：<src>/<cwd>/<output>
        cand = None
        try:
            from . import api as _api
            spec = (_api.artifacts_config(ctx) or {}).get("cppcheck_tool") or {}
            cwd = (spec.get("cwd") or "").strip("/\\")
            out = (spec.get("output") or "").strip("/\\")
            if out:
                cand = src_base / cwd / out if cwd else src_base / out
        except Exception as exc:                       # noqa: BLE001
            _log("读取 artifacts 配置失败：%s" % exc)

        # 兜底：配置缺失时按旧约定找
        if cand is None or not cand.exists():
            guess = src_base / "mcp_server" / "cppCheck" / "dist" / _TOOL_NAME
            if guess.exists():
                cand = guess

        if cand is None or not cand.exists():
            _log("编译成功但未找到产物：%s" % cand)
            return
        dst = _tool_path(ctx)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cand, dst)
            _log("工具已复制到 %s（%s）" % (dst, cand))
        except Exception as exc:                       # noqa: BLE001
            _log("复制工具失败：%s" % exc)

    import threading
    threading.Thread(target=_loop, daemon=True, name="scan-tool-copy").start()


# ══════════════════════ 执行检查 ══════════════════════

def start_scan(ctx, body: dict) -> tuple:
    """POST /api/project/scan — 检查 / 重新检查。body: {id}"""
    pid = _safe_id((body or {}).get("id", ""))
    if not pid:
        return _err("工程 id 非法")
    d = _projects_root(ctx) / pid
    if not d.is_dir():
        return _err("工程不存在", 404)
    if not (d / "src").exists():
        return _err("请先上传代码")

    tool = _tool_path(ctx)
    if not tool.exists():
        return _err("检查工具尚未部署，请先在「部署 / 升级」页点「部署静态检查工具」",
                    409)

    meta = _load_meta(d)
    if meta.get("status") == "scanning":
        return _err("该工程正在检查中，请稍候", 409)

    out_dir = d / "out"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)

    cmd = [str(tool), "scan",
           "--src", str(d / "src"),
           "--out", str(out_dir),
           "--project-name", meta.get("name", pid),
           "--no-open",
           "--embed-sources", "auto"]

    meta["status"] = "scanning"
    meta["error"] = ""
    _save_meta(d, meta)

    def job(task):
        task.update("scan", "启动检查工具…", 5)
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            lines = []
            # 整体超时看门狗：工具内部单文件有超时，但文件多 / 进程卡死时
            # 外层没有兜底会让工程永远停在 scanning（连删除都会被拒绝）。
            import threading as _th
            deadline = time.time() + _SCAN_TIMEOUT_S
            timed_out = {"v": False}

            def _kill_on_timeout():
                while proc.poll() is None:
                    if time.time() > deadline:
                        timed_out["v"] = True
                        _kill_tree(proc)
                        return
                    time.sleep(2)

            _th.Thread(target=_kill_on_timeout, daemon=True,
                       name="scan-timeout").start()

            for line in proc.stdout:                     # type: ignore[union-attr]
                line = line.rstrip()
                if not line:
                    continue
                lines.append(line)
                if len(lines) > 300:
                    lines.pop(0)
                task.update("", line)
                # 从输出里粗略推进度
                m = re.search(r"\[(\d)/(\d)\]", line)
                if m:
                    task.update("", "", int(5 + 90 * int(m.group(1)) / int(m.group(2))))
            proc.wait()
            if timed_out["v"]:
                meta["status"] = "failed"
                meta["error"] = "检查超时（超过 %d 分钟），已终止" % (_SCAN_TIMEOUT_S // 60)
                _save_meta(d, meta)
                task.done(False, meta["error"])
                return
        except Exception as e:                          # noqa: BLE001
            meta["status"] = "failed"
            meta["error"] = "启动失败: %s" % e
            _save_meta(d, meta)
            task.done(False, "启动失败: %s" % e)
            return

        report = out_dir / "report.html"
        if proc.returncode == 0 and report.exists():
            stat = _summarize(out_dir)
            meta.update({"status": "done", "error": "",
                         "total": stat.get("total", 0),
                         "by_tool": stat.get("by_tool", {})})
            _save_meta(d, meta)
            task.done(True, "检查完成，共 %d 条问题" % stat.get("total", 0))
        else:
            meta["status"] = "failed"
            meta["error"] = "工具返回 %s" % proc.returncode
            _save_meta(d, meta)
            task.done(False, "检查失败（返回码 %s）" % proc.returncode)

    t = tasks.start("scan", "代码检查: %s" % meta.get("name", pid), job)
    return _ok({"task_id": t.id, "id": pid})


def _summarize(out_dir: Path) -> dict:
    """从 scan_result.json 汇总问题数与工具分布。"""
    p = out_dir / "scan_result.json"
    if not p.exists():
        return {}
    try:
        items = json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                    # noqa: BLE001
        return {}
    by_tool = {}
    for x in items:
        t = x.get("tool", "")
        by_tool[t] = by_tool.get(t, 0) + 1
    return {"total": len(items), "by_tool": by_tool}


# ══════════════════════ 报告 ══════════════════════

def report_path(ctx, proj_id: str, name: str) -> tuple:
    """GET /api/project/report — 返回报告文件路径（由 server 内联下发）。

    只允许白名单文件名，防止路径穿越读任意文件。
    """
    pid = _safe_id(proj_id or "")
    if not pid:
        return _err("工程 id 非法")
    if name not in _REPORT_FILES:
        return _err("不支持的报告类型: %s" % name)
    d = _projects_root(ctx) / pid
    if not d.is_dir():
        return _err("工程不存在", 404)
    p = d / "out" / name
    if not p.exists():
        return _err("报告不存在，请先执行检查", 404)
    return _ok({"path": str(p), "name": name,
                "ctype": _REPORT_FILES[name]})
