#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skills_api.py — skill 独立仓库管理（给新增 skill MCP 服务使用）

与 nlp_worker 的 skill 完全隔离：deployer 网页上传/下载/删除的 skill
统一维护在 <install>/data/skills/ 下，仅供 skill MCP 服务读取。
- 支持上传单个 SKILL.md，或整个 skill 目录（zip）
- 下载支持单文件或打包 zip
- 删除走回收站（trash）优先，无 trash 时移到 _backup/skills_trash/
"""
import io
import json
import shutil
import zipfile
from pathlib import Path

# 允许的顶层文件（zip 解压白名单，防 zip 炸弹/路径穿越）
_ALLOWED_TOP = {"SKILL.md"}
_ALLOWED_SUFFIX = {".md", ".json", ".yaml", ".yml", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".txt", ".mjs", ".js", ".py", ".bat", ".cmd", ".css", ".html"}
_MAX_FILES = 200
_MAX_TOTAL_BYTES = 20 * 1024 * 1024          # zip 解压后总大小上限 20MB
_MAX_SINGLE_FILE = 5 * 1024 * 1024           # 单文件上限 5MB


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


# ══════════════════════ 工具 ══════════════════════

def _skills_dir(ctx) -> Path:
    """skill 仓库根目录：<install>/data/skills/（已在 paths 里注册并 ensure_all）"""
    d = ctx.paths.skills
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(name: str) -> str | None:
    """skill 名只允许字母数字下划线连字符，禁止路径穿越。"""
    if not name or name in (".", ".."):
        return None
    if any(c in name for c in "/\\:?*\"<>|"):
        return None
    if name.startswith("."):
        return None
    return name


def _read_frontmatter_desc(text: str, fallback: str = "") -> str:
    """从 SKILL.md frontmatter 里取 description。"""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end]
            for line in fm.splitlines():
                if line.startswith("description:"):
                    return line[len("description:"):].strip().strip('"\'')
    return fallback


def _scan_skills(ctx) -> list[dict]:
    """扫描 skills 目录，返回 skill 清单。"""
    root = _skills_dir(ctx)
    out = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            size = skill_md.stat().st_size
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except Exception:                                    # noqa: BLE001
            size, text = 0, ""
        desc = _read_frontmatter_desc(text, "")
        files = [p.relative_to(child).as_posix() for p in sorted(child.rglob("*")) if p.is_file()]
        out.append({
            "name": child.name,
            "description": desc,
            "size": size,
            "files": files,
            "file_count": len(files),
        })
    return out


# ══════════════════════ API ══════════════════════

def skills_list(ctx) -> tuple:
    """GET /api/skills — skill 清单（含每个 skill 的文件列表）。"""
    return _ok({"skills": _scan_skills(ctx), "dir": str(_skills_dir(ctx))})


def _extract_zip_to(root: Path, data: bytes, skill_name: str) -> tuple[Path, str | None]:
    """把 zip 解压到 root/skill_name/，做路径穿越与大小防护。返回 (目录, 错误)。"""
    target = root / skill_name
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return target, "不是有效的 zip 文件"

    infos = zf.infolist()
    if len(infos) > _MAX_FILES:
        return target, f"zip 内文件数超过上限（{_MAX_FILES}）"
    total = 0
    for info in infos:
        total += info.file_size
        if total > _MAX_TOTAL_BYTES:
            return target, f"zip 解压后总大小超过上限（{_MAX_TOTAL_BYTES//1024//1024}MB）"
        if info.file_size > _MAX_SINGLE_FILE:
            return target, f"单文件超过上限（{_MAX_SINGLE_FILE//1024//1024}MB）: {info.filename}"
        # 路径穿越防护
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or ".." in name.split("/"):
            return target, f"非法路径: {info.filename}"
    # 确保目标目录不存在，先删旧（trash）
    if target.exists():
        _trash_dir(target)

    names = [i.filename.replace("\\", "/") for i in infos]
    # 顶层必须是 skill_name/... 或直接文件；把顶层目录归一化到 target
    for info in infos:
        name = info.filename.replace("\\", "/")
        parts = name.split("/")
        # 去掉顶层目录（可能是 skill_name 或任意目录名）
        if len(parts) > 1 and parts[0] in ("", "."):
            parts = parts[1:]
        if len(parts) > 1:
            parts = parts[1:]            # 剥掉第一层目录
        rel = "/".join(parts)
        if not rel or rel.endswith("/"):
            continue
        out_path = target / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(out_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
    return target, None


def _trash_dir(path: Path):
    """删除目录：优先回收站式移动（deployer/_backup/skills_trash/），失败才直接删。"""
    import time
    try:
        base = path.parent.parent / "_backup" / "skills_trash"
        base.mkdir(parents=True, exist_ok=True)
        dest = base / f"{path.name}.{time.strftime('%Y%m%d_%H%M%S')}"
        path.rename(dest)
    except Exception:                                        # noqa: BLE001
        shutil.rmtree(path, ignore_errors=True)


def skills_upload(ctx, body: dict) -> tuple:
    """POST /api/skills/upload — 上传 skill。

    body 两种格式：
      1. {"mode": "single", "name": "xxx", "content": "<SKILL.md 文本>"}
      2. {"mode": "zip", "name": "xxx", "data_b64": "<zip base64>"}
    """
    mode = (body or {}).get("mode", "single")
    name = _safe_name((body or {}).get("name", ""))
    if not name:
        return _err("skill 名非法（只允许字母数字下划线连字符）")
    root = _skills_dir(ctx)

    if mode == "single":
        content = (body or {}).get("content", "")
        if not content.strip():
            return _err("SKILL.md 内容为空")
        if len(content.encode("utf-8")) > _MAX_SINGLE_FILE:
            return _err(f"文件超过上限（{_MAX_SINGLE_FILE//1024//1024}MB）")
        target = root / name
        if target.exists():
            _trash_dir(target)
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text(content, encoding="utf-8")
        return _ok({"name": name, "saved": True, "files": ["SKILL.md"]})

    if mode == "zip":
        import base64
        data_b64 = (body or {}).get("data_b64", "")
        try:
            data = base64.b64decode(data_b64)
        except Exception:                                    # noqa: BLE001
            return _err("base64 解码失败")
        if len(data) > _MAX_TOTAL_BYTES:
            return _err(f"zip 超过上限（{_MAX_TOTAL_BYTES//1024//1024}MB）")
        target, err = _extract_zip_to(root, data, name)
        if err:
            return _err(err)
        skill_md = target / "SKILL.md"
        if not skill_md.exists():
            _trash_dir(target)
            return _err("zip 里没有 SKILL.md（skill 必须包含 SKILL.md）")
        return _ok({"name": name, "saved": True,
                    "files": [p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()]})

    return _err(f"未知上传模式: {mode}")


def skills_download(ctx, name: str, as_zip: bool = False) -> tuple:
    """GET /api/skills/download?name=xxx[&zip=1] — 下载 skill。

    返回 dict 由 server.py 转成文件响应（bytes + filename）。
    """
    name = _safe_name(name or "")
    if not name:
        return _err("skill 名非法")
    target = _skills_dir(ctx) / name
    skill_md = target / "SKILL.md"
    if not target.is_dir() or not skill_md.exists():
        return _err(f"skill 不存在: {name}", 404)

    if as_zip:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(target.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(target).as_posix())
        return _ok({"file_bytes_b64": __import__("base64").b64encode(buf.getvalue()).decode(),
                    "filename": f"{name}.zip", "mime": "application/zip"})

    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception as e:                                   # noqa: BLE001
        return _err(f"读取失败: {e}", 500)
    return _ok({"content": text, "filename": f"{name}/SKILL.md", "mime": "text/markdown"})


def skills_delete(ctx, name: str) -> tuple:
    """POST /api/skills/delete — 删除 skill（回收站优先）。"""
    name = _safe_name(name or "")
    if not name:
        return _err("skill 名非法")
    target = _skills_dir(ctx) / name
    if not target.is_dir() or not (target / "SKILL.md").exists():
        return _err(f"skill 不存在: {name}", 404)
    _trash_dir(target)
    return _ok({"name": name, "deleted": True})


def skills_edit(ctx, name: str, body: dict) -> tuple:
    """POST /api/skills/edit — 编辑 SKILL.md 文本（可选，便于网页内直接改）。"""
    name = _safe_name(name or "")
    if not name:
        return _err("skill 名非法")
    target = _skills_dir(ctx) / name
    skill_md = target / "SKILL.md"
    if not target.is_dir() or not skill_md.exists():
        return _err(f"skill 不存在: {name}", 404)
    content = (body or {}).get("content", "")
    if not content.strip():
        return _err("SKILL.md 内容为空")
    skill_md.write_text(content, encoding="utf-8")
    return _ok({"name": name, "saved": True})


def skills_get(ctx, name: str) -> tuple:
    """GET /api/skills/get?name=xxx — 取 SKILL.md 文本（网页编辑用）。"""
    name = _safe_name(name or "")
    if not name:
        return _err("skill 名非法")
    target = _skills_dir(ctx) / name
    skill_md = target / "SKILL.md"
    if not target.is_dir() or not skill_md.exists():
        return _err(f"skill 不存在: {name}", 404)
    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception as e:                                   # noqa: BLE001
        return _err(f"读取失败: {e}", 500)
    return _ok({"name": name, "content": text})
