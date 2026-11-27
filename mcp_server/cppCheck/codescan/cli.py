# -*- coding: utf-8 -*-
"""命令行入口。

子命令：
  setup    检查环境并自动下载所需工具
  scan     一站式：拉源码 → 扫描 → 生成 HTML 报告（默认命令）
  report   仅根据已有结果重新生成 HTML
  doctor   诊断环境（不下载任何东西）
  init     生成一份配置文件模板
"""
from __future__ import annotations

import argparse
import collections
import os
import json
import sys
import time
import webbrowser
from pathlib import Path

from . import __version__, envcheck, engines, report, source, toolchain
from .common import Log, dirs, ensure_dirs, load_config, save_config


# ============================================================ setup

def cmd_setup(args) -> int:
    log = Log(total_steps=3)
    ensure_dirs("tools", "build", "output")

    log.phase("检查构建环境")
    status = envcheck.ensure_all(log, force=args.force,
                                 skip_optional=args.no_optional)

    log.phase("验证工具可用性")
    ok = envcheck.report_env(log, status)

    log.phase("写入工具清单")
    manifest = dirs()["tools"] / "manifest.json"
    data = {
        "version": __version__,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python": sys.version.split()[0],
        "tools": {},
    }
    for name, t in toolchain.probe_all().items():
        data["tools"][name] = {
            "ok": t.ok, "kind": t.kind, "path": str(t.target),
            "version": t.version,
        }
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    log.ok("工具清单：%s" % manifest)

    if not ok:
        log.err("必需工具缺失，无法进行扫描")
        log.info("可手工下载 cppcheck 解压到 tools/cppcheck/ 后重试")
        return 1

    log.done("环境就绪")
    return 0


# ============================================================ doctor

def cmd_doctor(args) -> int:
    log = Log()
    log.phase("环境诊断")
    envcheck.check_python(log)
    envcheck.check_pip(log)
    envcheck.check_network(log, timeout=8)

    log.info("")
    log.info("工具状态：")
    tools = toolchain.probe_all()
    allok = True
    for name, t in tools.items():
        need = "必需" if name in envcheck.REQUIRED else "可选"
        log.info("  [%s] %-14s (%s) %-6s %s"
                 % ("OK  " if t.ok else "MISS", name, need, t.kind,
                    t.version[:56]))
        if name in envcheck.REQUIRED and not t.ok:
            allok = False

    log.info("")
    log.info("配置：")
    cfg_path = dirs()["config"] / "scan_config.json"
    if cfg_path.exists():
        cfg = load_config(cfg_path)
        mode = "远程" if cfg["remote"].get("enabled") else "本地"
        log.info("  配置文件 %s" % cfg_path)
        log.info("  源码模式：%s" % mode)
        if cfg["remote"].get("enabled"):
            log.info("    %s@%s:%s"
                     % (cfg["remote"].get("user"),
                        cfg["remote"].get("host"),
                        cfg["remote"].get("source_dir")))
        else:
            log.info("    %s" % (cfg["local"].get("source_dir") or "（未设置）"))
    else:
        log.warn("  未找到配置文件：%s" % cfg_path)
        log.info("  执行 codescan init 生成模板")

    log.info("")
    log.info("结论：%s" % ("环境正常，可以扫描" if allok
                          else "缺少必需工具，请先执行 codescan setup"))
    return 0 if allok else 1


# ============================================================ init

def cmd_init(args) -> int:
    p = dirs()["config"] / "scan_config.json"
    if p.exists() and not args.force:
        print("配置文件已存在：%s" % p)
        print("如需覆盖请加 --force")
        return 1
    cfg = load_config(None)
    saved = save_config(cfg, p)
    print("已生成配置模板：%s" % saved)
    print("\n请编辑该文件，至少填写以下之一：")
    print("  远程模式：remote.enabled=true, host, user, password, source_dir")
    print("  本地模式：local.source_dir 指向源码目录")
    return 0


# ============================================================ scan

def cmd_scan(args) -> int:
    cfg_path = Path(args.config) if args.config else None
    cfg = load_config(cfg_path)

    # 命令行参数覆盖配置
    if args.src:
        cfg["remote"]["enabled"] = False
        cfg["local"]["source_dir"] = str(Path(args.src).resolve())
    if args.project_name:
        cfg["project_name"] = args.project_name
    if args.engines:
        cfg["scan"]["engines"] = [x.strip() for x in args.engines.split(",")
                                  if x.strip()]

    out_dir = Path(args.out) if args.out else dirs()["output"]
    out_dir.mkdir(parents=True, exist_ok=True)
    ensure_dirs("build")

    log = Log(total_steps=5)
    t0 = time.time()

    # ---- 1. 环境 ----
    # 只校验本次实际要用的引擎：指定 --engines custom 时不该要求 cppcheck。
    # 引擎名到工具名的映射（自定义规则是内置的，不需要外部工具）
    _ENGINE_TOOL = {
        "cppcheck": "cppcheck",
        "flawfinder": "flawfinder",
        "lizard": "lizard",
        "clang-tidy": "clang-tidy",
        "clang-format": "clang-format",
        "custom": None,
    }
    wanted = cfg["scan"].get("engines") or list(_ENGINE_TOOL)
    log.phase("检查工具环境")
    tools = toolchain.probe_all()
    need = sorted({_ENGINE_TOOL[e] for e in wanted
                   if _ENGINE_TOOL.get(e)})
    missing = [n for n in need if not tools.get(n) or not tools[n].ok]
    if missing:
        log.err("缺少必需工具：%s" % ", ".join(missing))
        log.info("请先执行：codescan setup")
        log.info("或改用已就绪的引擎：--engines custom")
        return 2
    optional_ok = [n for n in envcheck.OPTIONAL if tools[n].ok]
    log.ok("工具就绪（含可选：%s）" % (", ".join(optional_ok) or "无"))

    # ---- 2. 源码 ----
    log.phase("准备源码")
    try:
        src = source.prepare_sources(cfg, log)
    except Exception as exc:
        log.err(str(exc))
        return 3

    # ---- 2.5 为 clang-tidy 准备头文件 ----
    stub_dir = dirs()["build"] / "stub_inc"
    if "clang-tidy" in (cfg["scan"].get("engines") or []):
        from . import stubgen
        stubgen.ensure_stubs(stub_dir, log)
        if cfg["remote"].get("enabled"):
            hdr_dir = dirs()["build"] / "remote_inc"
            if not hdr_dir.exists() or args.refresh_headers:
                log.info("从远端拉取工程头文件（供 clang-tidy 解析）...")
                try:
                    source.fetch_remote_headers(cfg, log, hdr_dir, src)
                except Exception as exc:
                    log.warn("头文件拉取失败：%s" % exc)
            # 合并到桩目录，供统一引用
            if hdr_dir.exists():
                import shutil as _sh
                for p in hdr_dir.rglob("*"):
                    if p.is_file():
                        dst = stub_dir / p.relative_to(hdr_dir)
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if not dst.exists():
                            _sh.copy2(p, dst)

    # ---- 3. 扫描 ----
    log.phase("执行扫描")
    items = engines.run_all(src, out_dir, cfg, log, stub_dir=stub_dir)

    # 补充规范编号
    for x in items:
        if not x.get("spec"):
            if x["tool"] == "clang-tidy":
                x["spec"] = engines.TIDY_TO_SPEC.get(x["check"], "")
            elif x["tool"] == "cppcheck":
                x["spec"] = engines.CPPCHECK_TO_SPEC.get(x["check"], "")
            elif x["tool"] == "自定义规则":
                x["spec"] = x["check"]
            elif x["tool"] == "clang-format":
                x["spec"] = "YB-No.22"

    result_json = out_dir / "scan_result.json"
    result_json.write_text(json.dumps(items, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    log.ok("结果已保存：%s（%d 条）" % (result_json, len(items)))

    # ---- 4. 统计 ----
    log.phase("汇总统计")
    by_tool = collections.Counter(x["tool"] for x in items)
    by_sev = collections.Counter(x["sev"] for x in items)
    by_file = collections.Counter(x["file"] for x in items)
    by_spec = collections.Counter(x.get("spec","") for x in items if x.get("spec"))

    for t, n in by_tool.most_common():
        log.info("%-14s %5d" % (t, n))
    log.info("---")
    log.info("%-14s %5d" % ("合计", len(items)))

    stats = {
        "by_tool": dict(by_tool),
        "by_sev": dict(by_sev),
        "files": len(by_file),
        "top_files": by_file.most_common(15),
        "spec_hit": len(by_spec),
    }

    # ---- 5. 报告 ----
    log.phase("生成 HTML 报告")
    title = cfg["report"].get("title") or (
        "%s 静态扫描报告" % cfg.get("project_name", "未命名工程"))
    subtitle = "识别 %d 条问题 · 涉及 %d 个文件 · %d 种规则" % (
        len(items), len(by_file),
        len({x["check"] for x in items}))

    html_path = out_dir / "report.html"
    embed = _embed_flag(cfg, getattr(args, "embed_sources", "auto"))
    report.build_report(src, items, html_path, title=title,
                        subtitle=subtitle, stats=stats,
                        embed_sources=embed)
    log.ok("问题报告：%s（%s KB）"
           % (html_path, round(html_path.stat().st_size / 1024, 1)))

    # 覆盖对照表（若配置了规范文件）
    cov_html = None
    spec_file = cfg["rules"].get("spec_file") or ""
    if spec_file:
        sp = Path(spec_file)
        if not sp.is_absolute():
            sp = dirs()["root"] / sp
        if sp.exists():
            from . import spec as specmod
            rules_list = specmod.parse_spec(sp, log)
            if rules_list:
                specmod.attach_hits(rules_list, items)
                cov_html = out_dir / "coverage.html"
                report.build_coverage(rules_list, cov_html,
                                      spec_total=len(rules_list))
                log.ok("覆盖报表：%s" % cov_html)
        else:
            log.warn("规范文件不存在：%s，跳过覆盖报表" % sp)

    # 汇总 markdown
    md = out_dir / "summary.md"
    _write_summary(md, cfg, items, by_tool, by_sev, by_file, by_spec,
                   (time.time() - t0))
    log.ok("文字摘要：%s" % md)

    log.done("扫描完成")

    # 自动打开
    if cfg["report"].get("open_browser", True) and not args.no_open:
        try:
            webbrowser.open(html_path.resolve().as_uri())
            log.info("已在浏览器中打开报告")
        except Exception:
            pass

    print("\n输出目录：%s" % out_dir)
    return 0


def _embed_flag(cfg: dict, arg_val: str) -> bool:
    """解析 --embed-sources 的取值。

    auto : 内嵌，但超过阈值时 report 模块会自行放弃（默认）
    yes  : 强制内嵌
    no   : 完全不内嵌

    注意：auto 与 yes 在这里都返回 True，真正的阈值判断在
    report._read_sources() 里（累计超过 max_embed_mb 就整体不内嵌），
    避免生成几百 MB 的 HTML。
    """
    v = (arg_val or cfg.get("report", {}).get("embed_sources") or "auto").lower()
    if v in ("no", "false", "0", "never"):
        return False
    return True


def _write_summary(path: Path, cfg, items, by_tool, by_sev, by_file,
                   by_spec, cost):
    lines = []
    lines.append("# %s 静态扫描摘要\n" % cfg.get("project_name", "未命名工程"))
    lines.append("- 生成时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("- 问题总数：**%d**" % len(items))
    lines.append("- 涉及文件：%d" % len(by_file))
    lines.append("- 耗时：%.1f 秒\n" % cost)

    lines.append("## 按工具\n")
    lines.append("| 工具 | 条数 |")
    lines.append("| --- | --- |")
    for t, n in by_tool.most_common():
        lines.append("| %s | %d |" % (t, n))
    lines.append("")

    lines.append("## 按严重度\n")
    lines.append("| 级别 | 条数 |")
    lines.append("| --- | --- |")
    for s, n in by_sev.most_common():
        lines.append("| %s | %d |" % (s, n))
    lines.append("")

    lines.append("## 问题最多的文件\n")
    lines.append("| 文件 | 条数 |")
    lines.append("| --- | --- |")
    for f, n in by_file.most_common(15):
        lines.append("| `%s` | %d |" % (f, n))
    lines.append("")

    if by_spec:
        lines.append("## 命中的规范条款\n")
        lines.append("| 条款 | 条数 |")
        lines.append("| --- | --- |")
        for s, n in by_spec.most_common():
            lines.append("| %s | %d |" % (s, n))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


# ============================================================ report

def cmd_report(args) -> int:
    log = Log(total_steps=2)
    out_dir = Path(args.out) if args.out else dirs()["output"]
    res = out_dir / "scan_result.json"
    if not res.exists():
        print("未找到扫描结果：%s" % res, file=sys.stderr)
        print("请先执行 codescan scan", file=sys.stderr)
        return 1

    cfg = load_config(Path(args.config) if args.config else None)
    src = dirs()["build"] / "src"
    if args.src:
        src = Path(args.src)
    if not src.exists():
        log.err("源码目录不存在：%s" % src)
        return 1

    log.phase("读取扫描结果")
    items = json.loads(res.read_text(encoding="utf-8"))
    log.ok("%d 条" % len(items))

    log.phase("重建 HTML 报告")
    by_file = collections.Counter(x["file"] for x in items)
    title = cfg["report"].get("title") or (
        "%s 静态扫描报告" % cfg.get("project_name", "未命名工程"))
    html_path = out_dir / "report.html"
    embed = _embed_flag(cfg, getattr(args, "embed_sources", "auto"))
    report.build_report(src, items, html_path, title=title,
                        subtitle="识别 %d 条问题 · 涉及 %d 个文件"
                                 % (len(items), len(by_file)),
                        embed_sources=embed)
    log.ok("已生成：%s" % html_path)
    log.done()
    return 0


# ============================================================ 入口

def build_parser():
    p = argparse.ArgumentParser(
        prog="codescan",
        description="C/C++ 编码规范静态检查工具 v%s" % __version__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""常用命令：
  codescan init                     生成配置模板
  codescan setup                    检查环境并自动下载工具
  codescan scan                     一键扫描并生成 HTML 报告
  codescan scan --src D:\\mycode     指定源码目录直接扫描
  codescan doctor                   诊断环境（不下载）
  codescan report                   用已有结果重建 HTML
""")
    p.add_argument("-v", "--version", action="version",
                   version="%(prog)s " + __version__)
    sub = p.add_subparsers(dest="cmd")

    s1 = sub.add_parser("setup", help="检查环境并自动下载工具")
    s1.add_argument("--force", action="store_true", help="强制重新下载")
    s1.add_argument("--no-optional", action="store_true",
                    help="跳过可选工具（clang-tidy/clang-format）")
    s1.set_defaults(func=cmd_setup)

    s2 = sub.add_parser("scan", help="一键扫描并生成 HTML 报告")
    s2.add_argument("--src", help="源码目录（本地模式，覆盖配置文件）")
    s2.add_argument("--out", help="输出目录（默认 output/）")
    s2.add_argument("--config", help="配置文件路径")
    s2.add_argument("--project-name", help="工程名（用于报告标题）")
    s2.add_argument("--engines", help="指定引擎，逗号分隔："
                                      "cppcheck,flawfinder,lizard,clang-tidy,"
                                      "clang-format,custom")
    s2.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    s2.add_argument("--refresh-headers", action="store_true",
                    help="强制重新从远端拉取工程头文件")
    s2.add_argument("--embed-sources", default="auto",
                    choices=["auto", "yes", "no"],
                    help="报告是否内嵌源码上下文（auto=超阈值自动放弃）")
    s2.set_defaults(func=cmd_scan)

    s3 = sub.add_parser("report", help="用已有结果重建 HTML")
    s3.add_argument("--out", help="结果所在目录")
    s3.add_argument("--src", help="源码目录")
    s3.add_argument("--config", help="配置文件")
    s3.add_argument("--embed-sources", default="auto",
                    choices=["auto", "yes", "no"],
                    help="报告是否内嵌源码上下文")
    s3.set_defaults(func=cmd_report)

    s4 = sub.add_parser("doctor", help="诊断环境")
    s4.set_defaults(func=cmd_doctor)

    s5 = sub.add_parser("init", help="生成配置模板")
    s5.add_argument("--force", action="store_true", help="覆盖已有配置")
    s5.set_defaults(func=cmd_init)

    return p


def _fix_argv():
    """Windows 控制台下，cmd 传入的中文参数可能是 GBK 编码，
    Python 已按 locale 解码，通常正确；但若出现替换字符则尝试修复。"""
    import sys as _s
    fixed = []
    for a in _s.argv:
        if "\ufffd" in a:
            try:
                a = a.encode("utf-8", "surrogateescape").decode("gbk", "replace")
            except Exception:
                pass
        fixed.append(a)
    return fixed


def main(argv=None) -> int:
    # 统一标准输出为 UTF-8，避免 Windows 控制台中文乱码
    try:
        import io
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                          errors="replace", line_buffering=True)
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8",
                                          errors="replace", line_buffering=True)
    except Exception:
        pass

    if argv is None:
        argv = _fix_argv()[1:]
    p = build_parser()
    args = p.parse_args(argv)
    if not getattr(args, "cmd", None):
        # 无子命令时默认 scan（最常用）
        args = p.parse_args(list(argv or []) + ["scan"])
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130
    except Exception as exc:
        print("\n执行失败：%s" % exc, file=sys.stderr)
        if os.environ.get("CODESCAN_DEBUG"):
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
