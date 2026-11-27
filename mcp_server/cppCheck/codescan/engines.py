# -*- coding: utf-8 -*-
"""扫描引擎调度：把五个工具统一成同一结果格式。

统一结果字段：
    file   相对路径（posix 分隔）
    line   行号
    col    列号
    sev    严重度（error/warning/style/performance/portability/note）
    tool   工具名
    check  规则 ID
    msg    说明
    cwe    CWE 编号（可空）
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .common import dirs, run
from . import envcheck, toolchain

# clang-tidy 检查项 -> 规范编号映射（用于报告里显示"对应条款"）
TIDY_TO_SPEC = {
    "bugprone-switch-missing-default-case": "YB-No.143",
    "bugprone-branch-clone": "YB-No.151",
    "cppcoreguidelines-avoid-goto": "YB-No.149",
    "readability-braces-around-statements": "YB-No.138",
    "cppcoreguidelines-virtual-class-destructor": "YB-No.110",
    "cppcoreguidelines-special-member-functions": "YB-No.112",
    "bugprone-derived-method-shadowing-base-method": "YB-No.121",
    "bugprone-signed-bitwise": "YB-No.156",
    "cppcoreguidelines-pro-bounds-avoid-unchecked-container-access": "YB-No.182",
    "cppcoreguidelines-pro-bounds-constant-array-index": "YB-No.182",
    "cppcoreguidelines-avoid-c-arrays": "YB-No.87",
    "modernize-avoid-c-arrays": "YB-No.87",
    "cppcoreguidelines-init-variables": "YB-No.75",
    "cppcoreguidelines-pro-type-member-init": "YB-No.75",
    "bugprone-unused-local-non-trivial-variable": "YB-No.81",
    "clang-analyzer-deadcode.DeadStores": "YB-No.152",
    "performance-unnecessary-value-param": "YB-No.169",
    "modernize-deprecated-headers": "YB-No.172",
    "modernize-use-nullptr": "BT-4.7-2",
    "google-build-using-namespace": "YB-No.125",
    "cppcoreguidelines-owning-memory": "YB-No.162",
    "cppcoreguidelines-no-malloc": "YB-No.162",
    "cppcoreguidelines-pro-type-cstyle-cast": "YB-No.77",
    "readability-non-const-parameter": "BT-4.5-2",
    "readability-make-member-function-const": "YB-No.120",
    "readability-container-size-empty": "YB-No.174",
    "readability-duplicate-include": "YB-No.20",
    "bugprone-not-null-terminated-result": "YB-No.88",
    "cppcoreguidelines-avoid-non-const-global-variables": "YB-No.84",
    "cppcoreguidelines-macro-usage": "YB-No.130",
    "cppcoreguidelines-pro-type-union-access": "YB-No.161",
    "readability-avoid-unconditional-preprocessor-if": "BT-4.3-1",
    "clang-analyzer-core.NullDereference": "YB-No.157",
    "clang-analyzer-unix.Malloc": "YB-No.158",
    "clang-analyzer-cplusplus.NewDelete": "YB-No.158",
    "clang-analyzer-cplusplus.NewDeleteLeaks": "YB-No.158",
}

# cppcheck rule id -> 规范编号
CPPCHECK_TO_SPEC = {
    "wrongPrintfScanfArgNum": "YB-No.74",
    "invalidPrintfArgType_sint": "YB-No.77",
    "invalidPrintfArgType_s": "YB-No.77",
    "invalidPrintfArgType_uint": "YB-No.77",
    "missingReturn": "YB-No.145",
    "containerOutOfBounds": "YB-No.182",
    "arrayIndexOutOfBounds": "YB-No.182",
    "bufferAccessOutOfBounds": "YB-No.183",
    "terminateStrncpy": "YB-No.183",
    "uninitMemberVar": "YB-No.75",
    "uninitMemberVarNoCtor": "YB-No.75",
    "uninitvar": "YB-No.75",
    "uninitStructMember": "YB-No.75",
    "unusedVariable": "YB-No.81",
    "unreadVariable": "YB-No.82",
    "unusedFunction": "YB-No.147",
    "variableScope": "YB-No.83",
    "cstyleCast": "YB-No.77",
    "passedByValue": "YB-No.169",
    "useInitializationList": "YB-No.108",
    "functionConst": "YB-No.120",
    "constParameterPointer": "YB-No.120",
    "constParameterCallback": "YB-No.120",
    "constParameterReference": "YB-No.120",
    "constVariablePointer": "YB-No.120",
    "constVariableReference": "YB-No.120",
    "useStlAlgorithm": "YB-No.179",
    "functionStatic": "BT-4.4-5",
    "uselessAssignmentArg": "YB-No.152",
    "constStatement": "YB-No.152",
    "funcArgNamesDifferent": "YB-No.73",
    "returnReference": "YB-No.117",
    "memleak": "YB-No.158",
    "unusedAllocatedMemory": "YB-No.158",
    "deallocuse": "YB-No.159",
    "missingOverride": "BT-4.4-6",
    "virtualCallInConstructor": "YB-No.111",
    "unreachableCode": "YB-No.150",
    "operatorEqVarError": "YB-No.113",
}

# 默认排除的噪声规则（环境缺失 / 跨 TU 误报）
CPPCHECK_NOISE = {"missingIncludeSystem", "unusedStructMember",
                  "normalCheckLevelMaxBranches", "checkersReport",
                  "unmatchedSuppression", "toomanyconfigs"}


def _mk(file, line, sev, tool, check, msg, col=0, cwe="", spec=""):
    return dict(file=file, line=int(line), col=int(col), sev=sev,
                tool=tool, check=check, msg=msg.strip(), cwe=cwe, spec=spec)


# ============================================================ cppcheck

def run_cppcheck(src: Path, out_dir: Path, cfg: dict, log) -> list:
    tool = toolchain.resolve("cppcheck")
    if not toolchain.probe(tool).ok:
        log.warn("cppcheck 未就绪，跳过")
        return []

    files = [p for p in src.rglob("*")
             if p.is_file() and p.suffix.lower() in
             (".c", ".cpp", ".cc", ".cxx")]
    if not files:
        return []

    inc = []
    incs = cfg["scan"].get("include_dirs") or []
    inc += ["-I", str(src)]
    for sub in ("common", "main", "pps", "src", "include", "inc"):
        p = src / sub
        if p.is_dir():
            inc += ["-I", str(p)]
    for d in incs:
        p = Path(d)
        if not p.is_absolute():
            p = src / d
        if p.is_dir():
            inc += ["-I", str(p)]

    tmpl = "{file}|{line}|{column}|{severity}|{id}|{message}|{cwe}"
    base = ["--template=" + tmpl,
            "--std=" + cfg["scan"].get("std", "c++14"),
            "--language=c++", "--inline-suppr", "--quiet",
            "--suppress=missingInclude",
            "--suppress=unmatchedSuppression",
            "--suppress=unusedFunction",
            "--suppress=checkersReport"] + inc
    for s in (cfg["scan"].get("suppress") or []):
        base.append("--suppress=" + s)

    runs = [
        ("常规", ["--enable=warning,style,performance,portability"] + base),
        ("穷尽", ["--enable=all", "--inconclusive"] + base),
    ]

    seen = {}
    for label, args in runs:
        log.info("cppcheck %s检查..." % label)
        rc, blob = tool.run(*(args + [str(f) for f in files]), timeout=1800)
        n = 0
        for line in blob.splitlines():
            if "|" not in line:
                continue
            p = line.split("|")
            if len(p) < 7:
                continue
            f, ln, col, sev, cid, msg = p[0], p[1], p[2], p[3], p[4], p[5]
            if cid in CPPCHECK_NOISE:
                continue
            try:
                rel = Path(f).resolve().relative_to(src.resolve()).as_posix()
            except ValueError:
                rel = Path(f).name
            key = (rel, ln, cid, msg)
            if key in seen:
                continue
            seen[key] = _mk(rel, ln, sev, "cppcheck", cid, msg, col,
                            "|".join(p[6:]).strip())
            n += 1
        log.info("  新增 %d 条" % n)

    res = list(seen.values())
    log.ok("cppcheck 完成：%d 条" % len(res))
    return res


# ============================================================ flawfinder

def run_flawfinder(src: Path, out_dir: Path, cfg: dict, log) -> list:
    tool = toolchain.resolve("flawfinder")
    if not toolchain.probe(tool).ok:
        log.warn("flawfinder 未就绪，跳过")
        return []

    log.info("flawfinder 安全检查...")
    rc, out = tool.run("--minlevel=1", "--quiet", "--dataonly", "--csv",
                       str(src), timeout=900)
    import csv
    import io
    rows = []
    try:
        for x in csv.DictReader(io.StringIO(out)):
            f = x["File"].replace("\\", "/")
            try:
                rel = Path(f).resolve().relative_to(src.resolve()).as_posix()
            except ValueError:
                rel = Path(f).name
            rows.append(_mk(rel, x["Line"],
                            "L%s" % x["Level"], "flawfinder",
                            "%s %s" % (x["RuleId"], x["Name"]),
                            x["Warning"], 0, x["CWEs"]))
    except Exception as exc:
        log.warn("flawfinder 结果解析失败：%s" % exc)
    log.ok("flawfinder 完成：%d 条" % len(rows))
    return rows


# ============================================================ lizard

def run_lizard(src: Path, out_dir: Path, cfg: dict, log) -> list:
    tool = toolchain.resolve("lizard")
    if not toolchain.probe(tool).ok:
        log.warn("lizard 未就绪，跳过")
        return []

    log.info("lizard 复杂度分析...")
    rc, out = tool.run(str(src), "-l", "cpp", "--csv", timeout=900)
    import csv
    import io
    rows = []
    skipped = 0
    ccn_max = 10
    len_max = 100
    src_res = src.resolve()
    for r in csv.reader(io.StringIO(out)):
        if len(r) < 11:
            continue
        try:
            nloc, ccn, token, param, length = (int(r[0]), int(r[1]),
                                               int(r[2]), int(r[3]), int(r[4]))
        except ValueError:
            continue
        if ccn <= ccn_max and length <= len_max:
            continue
        f = r[6].replace("\\", "/")
        # 只接受上传目录内的文件。
        # lizard 有时会扫到编译器内置头（__clang_cuda_*.h、smmintrin.h、
        # vecintrin.h 等）或工具自身目录，那些不是被测代码，必须丢弃。
        try:
            rel = Path(f).resolve().relative_to(src_res).as_posix()
        except ValueError:
            skipped += 1
            continue
        bad = []
        if ccn > ccn_max:
            bad.append("CCN=%d" % ccn)
        if length > len_max:
            bad.append("长度=%d行" % length)
        rows.append(_mk(rel, r[9], "warning" if ccn > 15 else "style",
                        "lizard", "复杂度超标",
                        "%s — %s" % (r[7], "，".join(bad))))
    if skipped:
        log.info("  已忽略 %d 个非本工程文件（编译器内置头/工具自身代码）" % skipped)
    log.ok("lizard 完成：%d 个函数超标" % len(rows))
    return rows


# ============================================================ clang-tidy

TIDY_DISABLE = [
    "-modernize-use-trailing-return-type",
    "-readability-identifier-length",
    "-readability-magic-numbers",
    "-cppcoreguidelines-avoid-magic-numbers",
    "-google-readability-todo",
    "-readability-uppercase-literal-suffix",
    "-modernize-use-using",
    "-hicpp-no-array-decay",
    "-cppcoreguidelines-pro-bounds-array-to-pointer-decay",
    "-cppcoreguidelines-pro-bounds-pointer-arithmetic",
    "-readability-function-cognitive-complexity",
    "-cppcoreguidelines-pro-type-reinterpret-cast",
    "-cppcoreguidelines-pro-type-vararg",
    "-hicpp-vararg",
    "-cert-dcl50-cpp",
    "-bugprone-easily-swappable-parameters",
    "-modernize-use-nodiscard",
    "-modernize-use-auto",
    "-readability-convert-member-functions-to-static",
    "-readability-simplify-boolean-expr",
    "-readability-implicit-bool-conversion",
    "-modernize-redundant-void-arg",
    "-readability-else-after-return",
    "-readability-redundant-control-flow",
    "-readability-redundant-nested-if",
    "-modernize-use-equals-default",
    "-cppcoreguidelines-avoid-do-while",
    "-cert-err33-c",
    "-cppcoreguidelines-use-enum-class",
    "-performance-enum-size",
    "-google-global-names-in-headers",
    "-readability-trailing-comma",
    "-cppcoreguidelines-macro-to-enum",
    "-bugprone-reserved-identifier",
    "-readability-redundant-string-init",
    "-modernize-use-default-member-init",
    "-performance-inefficient-string-concatenation",
    "-readability-isolate-declaration",
    "-bugprone-narrowing-conversions",
    "-cppcoreguidelines-narrowing-conversions",
    "-readability-avoid-nested-conditional-operator",
    "-modernize-loop-convert",
    "-readability-qualified-auto",
]


def run_clang_tidy(src: Path, out_dir: Path, cfg: dict, log,
                   extra_include=None) -> list:
    tool = toolchain.resolve("clang-tidy")
    if not toolchain.probe(tool).ok:
        log.warn("clang-tidy 未就绪，跳过")
        return []

    files = [p for p in src.rglob("*")
             if p.is_file() and p.suffix.lower() in (".cpp", ".cc", ".cxx")]
    if not files:
        return []

    checks = ",".join(["-*", "bugprone-*", "clang-analyzer-*",
                       "cppcoreguidelines-*", "readability-*",
                       "modernize-*", "performance-*", "cert-*",
                       "hicpp-*", "google-*"] + TIDY_DISABLE)

    inc = ["-I.", "-I" + str(src)]
    for sub in ("common", "main", "pps", "src", "include", "inc"):
        p = src / sub
        if p.is_dir():
            inc.append("-I" + str(p))
    for d in (cfg["scan"].get("include_dirs") or []):
        p = Path(d)
        if not p.is_absolute():
            p = src / d
        if p.is_dir():
            inc.append("-I" + str(p))
    # 头文件桩必须用 -idirafter：优先级低于系统头，
    # 否则桩里的 sys/types.h 会遮蔽 Windows SDK 的 sys/stat.h 导致解析失败
    if extra_include and Path(extra_include).is_dir():
        inc += ["-idirafter", str(extra_include)]

    args = ["--", "-std=" + cfg["scan"].get("std", "c++14")] + inc + \
           ["-Wno-everything"]

    rows = []
    err_files = 0
    pat = re.compile(r"^(.*?):(\d+):(\d+):\s+(warning|error):\s+(.*?)\s+\[([\w\-.]+)\]\s*\r?$", re.M)
    for idx, f in enumerate(files, 1):
        log.info("clang-tidy %d/%d %s" % (idx, len(files),
                                          f.relative_to(src).as_posix()))
        rc, blob = tool.run(str(f), "--checks=" + checks, "--quiet", *args,
                            timeout=1200)
        if "clang-diagnostic-error" in blob:
            err_files += 1
        hit = 0
        # 注意：clang-tidy 的告警常出现在头文件里（宏、声明等），
        # 头文件同属本工程，必须保留，不能只收 .cpp 的结果。
        for m in pat.finditer(blob):
            path, ln, col, sev, msg, chk = m.groups()
            if chk == "clang-diagnostic-error":
                continue
            try:
                rel = Path(path).resolve().relative_to(src.resolve()).as_posix()
            except ValueError:
                continue          # 确实不属于本工程（如系统头/桩）
            rows.append(_mk(rel, ln, sev, "clang-tidy", chk, msg, col))
            hit += 1
        if hit:
            log.info("  -> %d" % hit)

    if err_files:
        log.warn("%d 个文件存在无法解析的头文件依赖，已跳过其分析"
                 % err_files)
    log.ok("clang-tidy 完成：%d 条" % len(rows))
    return rows


# ============================================================ clang-format

def run_clang_format(src: Path, out_dir: Path, cfg: dict, log,
                     style_file=None) -> list:
    tool = toolchain.resolve("clang-format")
    if not toolchain.probe(tool).ok:
        log.warn("clang-format 未就绪，跳过格式检查")
        return []

    if style_file is None:
        style_file = dirs()["config"] / ".clang-format"
    if not Path(style_file).exists():
        log.warn("未找到 .clang-format 配置，跳过")
        return []

    log.info("clang-format 格式检查...")
    files = [p for p in src.rglob("*")
             if p.is_file() and p.suffix.lower() in
             (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx")]

    rows = []
    for idx, f in enumerate(files, 1):
        rc, blob = tool.run("-style=file:" + str(Path(style_file).resolve()),
                            "-n", str(f), timeout=180)
        bad = set()
        for m in re.finditer(r":(\d+):\d+:\s+warning:", blob):
            bad.add(int(m.group(1)))
        if not bad:
            continue
        rel = f.relative_to(src).as_posix()
        # 按文件汇总一行（避免上千条噪声），同时记录前 5 个具体行
        sample = sorted(bad)[:5]
        rows.append(_mk(rel, sample[0], "style", "clang-format",
                        "格式不符",
                        "该文件 %d 行不符合 .clang-format（行宽/缩进/空格等），"
                        "示例行：%s" % (len(bad),
                                        ", ".join(map(str, sample)))))
        if idx % 10 == 0:
            log.info("  已检查 %d/%d" % (idx, len(files)))
    log.ok("clang-format 完成：%d 个文件有格式差异" % len(rows))
    return rows


# ============================================================ 自定义规则

def run_custom(src: Path, out_dir: Path, cfg: dict, log) -> list:
    from . import rules
    log.info("自定义规则检查（命名/注释/文件结构等）...")
    rows = rules.scan(src, log)
    out = []
    for x in rows:
        out.append(_mk(x["file"], x["line"],
                       "error" if x["sev"] == "A" else "warning",
                       "自定义规则", x["rule"], x["msg"]))
    log.ok("自定义规则完成：%d 条" % len(out))
    return out


# ============================================================ 统一入口

ENGINES = {
    "cppcheck": run_cppcheck,
    "flawfinder": run_flawfinder,
    "lizard": run_lizard,
    "clang-tidy": run_clang_tidy,
    "clang-format": run_clang_format,
    "custom": run_custom,
}


def run_all(src: Path, out_dir: Path, cfg: dict, log, stub_dir=None) -> list:
    """按配置执行全部引擎，返回合并后的结果。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = cfg["scan"].get("engines") or list(ENGINES)
    if cfg["scan"].get("clang_format_check") and "clang-format" not in wanted:
        wanted = list(wanted) + ["clang-format"]

    all_rows = []
    for name in wanted:
        fn = ENGINES.get(name)
        if not fn:
            log.warn("未知引擎：%s，跳过" % name)
            continue
        try:
            if name == "clang-tidy":
                rows = fn(src, out_dir, cfg, log, extra_include=stub_dir)
            else:
                rows = fn(src, out_dir, cfg, log)
            all_rows.extend(rows)
            # 每引擎单独落盘，便于排查
            with open(out_dir / ("raw_%s.json" % name.replace("-", "_")),
                      "w", encoding="utf-8", newline="\n") as f:
                json.dump(rows, f, ensure_ascii=False, indent=1)
        except Exception as exc:
            log.err("%s 执行失败：%s" % (name, exc))

    # 全局去重
    seen = set()
    uniq = []
    for x in all_rows:
        k = (x["file"], x["line"], x["tool"], x["check"], x["msg"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(x)
    uniq.sort(key=lambda d: (d["file"], d["line"]))
    return uniq
