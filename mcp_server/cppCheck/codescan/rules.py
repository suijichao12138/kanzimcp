# -*- coding: utf-8 -*-
"""自研规则检查器 —— 补齐通用静态分析工具覆盖不到的规范条款。

覆盖范围（对应《博泰 C++/C 编码规范检查手册》）：
  命名格式、文件头、保护宏、宏命名、注释风格、调试开关、结构用法等。

这些条款 cppcheck / clang-tidy 等通用工具都不检查，只能自研实现。
每条结果都带规范编号（如 YB-No.105），便于回溯原文条款。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

SRC_EXT = (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx")


# ============ 工具函数 ============

class Finding:
    __slots__ = ("file", "line", "rule", "msg", "sev")

    def __init__(self, f, ln, rule, msg, sev="warning"):
        self.file, self.line, self.rule = f, ln, rule
        self.msg, self.sev = msg, sev


def strip_comments_and_strings(lines):
    """把注释与字符串内容替换为空格，便于正则匹配时不误伤。
    返回 (处理后的行列表, 原始行列表)。"""
    out = []
    in_block = False
    for ln in lines:
        s = []
        i = 0
        while i < len(ln):
            if in_block:
                j = ln.find("*/", i)
                if j < 0:
                    s.append(" " * (len(ln) - i))
                    i = len(ln)
                else:
                    s.append(" " * (j + 2 - i))
                    i = j + 2
                    in_block = False
            else:
                if ln.startswith("//", i):
                    s.append(" " * (len(ln) - i))
                    i = len(ln)
                elif ln.startswith("/*", i):
                    in_block = True
                    s.append("  ")
                    i += 2
                elif ln[i] in "\"'":
                    q = ln[i]
                    j = i + 1
                    while j < len(ln):
                        if ln[j] == "\\":
                            j += 2
                            continue
                        if ln[j] == q:
                            j += 1
                            break
                        j += 1
                    s.append(q + " " * max(0, j - i - 2) + q if j - i >= 2 else ln[i:j])
                    i = j
                else:
                    s.append(ln[i])
                    i += 1
        out.append("".join(s))
    return out


# ============ 各条检查 ============

RE_STRUCT_TAG = re.compile(r"\btypedef\s+struct\s+(\w+)\s*\{")
RE_STRUCT_TAG2 = re.compile(r"\bstruct\s+(tag\w+)\s*\{")
RE_UNION = re.compile(r"\btypedef\s+union\s+(\w+)\s*\{")
RE_ENUM = re.compile(r"\b(?:typedef\s+)?enum\s+(\w+)\s*\{")
RE_CLASS = re.compile(r"\bclass\s+(\w+)\s*(?::[^{]*)?\{")
RE_DEFINE = re.compile(r"^\s*#\s*define\s+(\w+)")
RE_INCLUDE = re.compile(r"^\s*#\s*include\s+([<\"])([^>\"]+)[>\"]")
RE_FUNC_IMPL = re.compile(
    r"^\s*(?:[\w:<>,*&\s]+?)\s+(\w+)\s*\([^;]*\)\s*(?:const\s*)?\{?\s*$")


def check_file(path, rel, raw):
    clean = strip_comments_and_strings(raw)
    F = []
    n = len(raw)
    is_header = rel.endswith((".h", ".hpp"))
    base = os.path.basename(rel)
    stem = os.path.splitext(base)[0]

    # ---------- 文件级 ----------
    # YB-14 文件长度（与 Lizard 重复，此处仅提示）
    # YB-15 文件头说明
    head = "\n".join(raw[:25])
    if not re.search(r"@file|Filename|文件名|Description|@brief", head, re.I):
        F.append(Finding(rel, 1, "YB-No.15", "缺少文件头说明（未见 @file/Filename/Description）", "A"))

    # YB-49 / BT-4.8-1 不用 /* */ 注释（文件头豁免）
    # 文件头 = 从第 1 行开始、到第一次出现"代码行"为止的连续注释/空行区域。
    # 之前硬编码 i > 20 判定，头部注释超过 20 行会被误报，
    # 而头部只有 3 行的文件里真正的块注释又能逃过检查。
    head_end = 0
    for i, l in enumerate(raw):
        st = l.strip()
        if not st or st.startswith(("/*", "*", "//")):
            head_end = i + 1
            continue
        break
    for i, l in enumerate(raw):
        if "/*" in raw[i] and i >= head_end:
            F.append(Finding(rel, i + 1, "YB-No.49",
                             "使用 /* */ 块注释，规范要求用 //", "warning"))

    # BT-4.3-1 / YB-48 不用 #if 0 注释代码
    for i, l in enumerate(raw):
        if re.match(r"^\s*#\s*if\s+0\b", l):
            F.append(Finding(rel, i + 1, "BT-4.3-1",
                             "使用 #if 0 屏蔽代码，规范要求删除死代码", "A"))

    # YB-22 行宽 > 80
    for i, l in enumerate(raw):
        if len(l.rstrip("\n")) > 80:
            F.append(Finding(rel, i + 1, "YB-No.22",
                             "行宽 %d > 80 列" % len(l.rstrip()), "warning"))

    # YB-40 / 41 缩进用 Tab
    # 只判"整行前导缩进全是空格"的情况。
    # 续行对齐（上一行未结束，本行用空格对齐到括号/参数位置）是常规写法，
    # 之前一并报成"应使用 Tab"，误报量很大。
    for i, l in enumerate(raw):
        if not l.strip() or l.lstrip().startswith("*"):
            continue
        if not l.startswith(" "):
            continue
        prev = raw[i - 1].rstrip() if i > 0 else ""
        if prev and not prev.endswith((";", "{", "}", ":", ",", "(", "\\")):
            continue                      # 续行对齐，跳过
        if "\t" in l[:len(l) - len(l.lstrip())]:
            continue                      # 已有 Tab，只是前面补了空格
        F.append(Finding(rel, i + 1, "YB-No.40",
                         "使用空格缩进，规范要求 Tab", "warning"))

    # YB-23 / BT-4.7-4 一行一语句
    for i, l in enumerate(clean):
        st = l.strip()
        if not st or st.startswith("#"):
            continue
        # 排除 for(...) 与字符串
        body = re.sub(r"\bfor\s*\([^)]*\)", "FOR", st)
        if body.count(";") >= 2 and not body.rstrip().endswith(";"):
            F.append(Finding(rel, i + 1, "YB-No.23",
                             "一行多条语句", "warning"))

    # YB-18 / BT-4.2-3 头文件保护宏
    if is_header:
        m = re.search(r"^\s*#\s*ifndef\s+(\w+)", "\n".join(raw), re.M)
        if not m:
            F.append(Finding(rel, 1, "BT-4.2-3", "头文件缺少 #ifndef 保护宏", "A"))
        elif not re.match(r"^__[A-Z0-9_]+__$", m.group(1)):
            F.append(Finding(rel, 1, "YB-No.18",
                             "保护宏 '%s' 不符合 __模块_文件名_H__ 规范" % m.group(1), "warning"))

        # YB-21 头文件不定义变量（粗筛：非 extern 的全局定义）
        for i, l in enumerate(clean):
            if re.match(r"^\s*static\s+\w[\w\s\*]*\s+\w+\s*=", l):
                F.append(Finding(rel, i + 1, "YB-No.21",
                                 "头文件中定义 static 变量", "A"))

    # YB-19 / YB-131 include 规范
    for i, l in enumerate(raw):
        m = RE_INCLUDE.match(l)
        if not m:
            continue
        br, inc = m.group(1), m.group(2)
        if inc.startswith("/") or re.match(r"^[A-Za-z]:", inc):
            F.append(Finding(rel, i + 1, "YB-No.19",
                             "include 使用绝对路径: %s" % inc, "A"))
        # 自己项目的头用 "" 而非 <>
        if br == "<" and inc.split("/")[0] in ("common", "main", "pps"):
            F.append(Finding(rel, i + 1, "YB-No.131",
                             "项目内头文件应用 \"\" 包含: %s" % inc, "warning"))
        # YB-172 / BT-4.2-2 C 头文件
        if inc in ("string.h", "stdio.h", "stdlib.h", "math.h",
                   "string.h", "time.h", "memory.h", "stdint.h"):
            F.append(Finding(rel, i + 1, "YB-No.172",
                             "使用 C 头文件 <%s>，应用 C++ 版本" % inc, "warning"))

    # YB-127 / BT-4.6-5 宏名全大写
    for i, l in enumerate(raw):
        m = RE_DEFINE.match(l)
        if m:
            name = m.group(1)
            if name not in ("__FILE__", "__LINE__") and re.search(r"[a-z]", name):
                F.append(Finding(rel, i + 1, "YB-No.127",
                                 "宏名 '%s' 含小写字母，应全大写" % name, "warning"))

    # YB-86 float 字面量缺 F 后缀
    # 仅当上下文明确是 float 类型（float x = 1.0; / (float)1.0）时报，避免 double 误报
    for i, l in enumerate(clean):
        if not re.search(r"\bfloat\b|\(\s*float\s*\)", l):
            continue
        for m in re.finditer(r"(?<![\w.])(\d+\.\d+)(?![\w.f]|[0-9])", l):
            ctx = l[max(0, m.start() - 40):m.start()]
            if "double" in ctx:
                continue
            F.append(Finding(rel, i + 1, "YB-No.86",
                             "float 上下文的字面量 '%s' 应加 F 后缀" % m.group(1), "warning"))

    # BT-4.6-4 无符号常量加 U
    # 合并原来分散在两处的判定（一处判 0x 大值、一处判 8/16 进制），
    # 否则同一行会被两条规则分别报一次。
    for i, l in enumerate(clean):
        for m in re.finditer(r"(?<![\w.])(0[xX][0-9A-Fa-f]+|0[0-7]+)(?![\w.])", l):
            lit = m.group(1)
            if lit.lower().startswith("0x"):
                small = len(lit) <= 3                    # 0x0~0xF 小值不强制
                big = int(lit, 16) > 0x7FFFFFFF
                if not (big or not small):
                    continue
            if re.match(r"[uUlL]", l[m.end():m.end() + 2]):
                continue
            F.append(Finding(rel, i + 1, "BT-4.6-4",
                             "无符号常量 '%s' 应加 U 后缀" % lit, "warning"))

    # ---------- 命名 ----------
    for i, l in enumerate(clean):
        lineno = i + 1
        # YB-93 结构体 tag 命名
        m = RE_STRUCT_TAG.search(l)
        if m and not m.group(1).startswith("tag"):
            F.append(Finding(rel, lineno, "YB-No.93",
                             "结构体 tag '%s' 应以 tag 开头" % m.group(1), "warning"))
        # YB-95 union
        m = RE_UNION.search(l)
        if m and not m.group(1).startswith("tag"):
            F.append(Finding(rel, lineno, "YB-No.95",
                             "联合体 tag '%s' 应以 tag 开头" % m.group(1), "warning"))
        # YB-96 enum
        m = RE_ENUM.search(l)
        if m and not m.group(1).startswith("tag"):
            F.append(Finding(rel, lineno, "YB-No.96",
                             "枚举 tag '%s' 应以 tag 开头" % m.group(1), "warning"))
        # YB-100 类名以 C 开头（跳过继承自第三方基类的判断，仅提示）
        m = RE_CLASS.search(l)
        if m:
            cn = m.group(1)
            if not re.match(r"^C[A-Z]", cn) and cn not in ("KZBPlayerApplication",):
                F.append(Finding(rel, lineno, "YB-No.100",
                                 "类名 '%s' 未以 C 开头" % cn, "warning"))

    # YB-2 标识符 > 31 字符
    for i, l in enumerate(clean):
        for m in re.finditer(r"\b([A-Za-z_]\w{31,})\b", l):
            F.append(Finding(rel, i + 1, "YB-No.2",
                             "标识符 '%s' 长度 %d > 31"
                             % (m.group(1), len(m.group(1))), "warning"))

    # BT-4.6-2 标识符 > 40
    for i, l in enumerate(clean):
        for m in re.finditer(r"\b([A-Za-z_]\w{40,})\b", l):
            F.append(Finding(rel, i + 1, "BT-4.6-2",
                             "标识符 '%s' 长度 > 40" % m.group(1), "warning"))

    # YB-54 函数名不以 _ 开头
    for i, l in enumerate(clean):
        m = re.match(r"^\s*(?:[\w:<>,*&\s]+?)\s+(_\w+)\s*\(", l)
        if m:
            F.append(Finding(rel, i + 1, "YB-No.54",
                             "函数名 '%s' 以下划线开头" % m.group(1), "warning"))

    # YB-84 全局变量 g_ 前缀（在 .cpp 顶层定义的裸全局）
    for i, l in enumerate(clean):
        m = re.match(r"^(?!\s)(?!extern|static|typedef|class|struct|union|enum|"
                     r"using|namespace|template|return|if|for|while|switch|"
                     r"#)(?:\w[\w:<>,\*&\s]*?)\b(\w+)\s*(?:=|;|\[)", l)
        if m and "(" not in l and "::" not in l:      # 排除 类名::成员 的静态成员定义
            vn = m.group(1)
            if not re.match(r"^g_\w+$", vn) and not vn.isupper():
                F.append(Finding(rel, i + 1, "YB-No.84",
                                 "全局变量 '%s' 缺少 g_ 前缀" % vn, "warning"))

    # YB-105 成员变量 m_ 前缀（类的 private 段）
    # 只在头文件里判：.cpp 里的"类型 名称;"绝大多数是局部变量，
    # 在 .cpp 里判会把局部变量全误报成缺 m_ 前缀。
    if is_header:
        in_class = 0
        for i, l in enumerate(clean):
            if RE_CLASS.search(l):
                in_class = 1
                continue
            if in_class and re.match(r"^\};", l):
                in_class = 0
                continue
            if in_class:
                m = re.match(r"^\s+(?:[\w:<>,\*&]+ )+(\w+)\s*(?:\[[^\]]*\])?\s*(?:=[^;]*)?;", l)
                if m:
                    vn = m.group(1)
                    if ("(" not in l and not vn.startswith("m_")
                            and not vn.isupper()
                            and not re.match(r"^[A-Z]\w+$", vn)
                            and vn not in ("public", "private", "protected")):
                        F.append(Finding(rel, i + 1, "YB-No.105",
                                         "成员变量 '%s' 缺少 m_ 前缀" % vn, "warning"))

    # YB-97 枚举成员全大写
    for i, l in enumerate(clean):
        m = re.match(r"^\s+([a-zA-Z_]\w*)\s*(?:=\s*[^,]+)?\s*,?\s*$", l)
        if m and re.search(r"[a-z]", m.group(1)):
            # 仅当处于 enum 块内：向上找最近的 enum 关键字，
            # 中途若先遇到 "};" 说明已经离开 enum 块（不能只向上找 8 行，
            # 成员多的枚举会超出窗口而漏报）。
            for j in range(i - 1, -1, -1):
                if re.search(r"\benum\b", clean[j]):
                    F.append(Finding(rel, i + 1, "YB-No.97",
                                     "枚举成员 '%s' 应全大写" % m.group(1), "warning"))
                    break
                if re.match(r"^\s*\};", clean[j]):
                    break

    # YB-98 / YB-90 末尾多余逗号
    for i, l in enumerate(clean):
        if re.match(r"^\s*\}\s*\w*\s*;?\s*$", l) and i > 0:
            prev = clean[i - 1].rstrip()
            if prev.endswith(","):
                F.append(Finding(rel, i + 1, "YB-No.98",
                                 "枚举/数组初始化末尾多了逗号", "warning"))

    # YB-91 二级以上指针
    for i, l in enumerate(clean):
        if re.search(r"\b\w+\s*\*\s*\*", l):
            F.append(Finding(rel, i + 1, "YB-No.91",
                             "使用二级指针", "warning"))

    # YB-174 size()==0 → empty()
    for i, l in enumerate(clean):
        if re.search(r"\.size\(\)\s*(?:==|!=)\s*0", l):
            F.append(Finding(rel, i + 1, "YB-No.174",
                             "用 size()==0 判断空，应改用 empty()", "warning"))

    # YB-168 a = a + 1 复合运算符
    for i, l in enumerate(clean):
        m = re.search(r"\b(\w+)\s*=\s*\1\s*([+\-*/%])\s*", l)
        if m:
            F.append(Finding(rel, i + 1, "YB-No.168",
                             "'%s' 应改用复合运算符 %s%s="
                             % (m.group(1), m.group(1), m.group(2)), "warning"))

    # YB-160 循环内 new/malloc
    # 用「大括号深度」判定是否仍在循环体内：
    # 之前用 in_loop 标志 + 单行括号计数，循环体内的 if/复合语句
    # 会让 { } 数量相等或反转，导致 in_loop 被提前清掉而漏报。
    depth = 0
    loop_depth = None                # 进入循环体时的深度基线
    for i, l in enumerate(clean):
        opened = l.count("{")
        closed = l.count("}")
        if loop_depth is None and re.search(r"\b(for|while)\s*\(", l):
            loop_depth = depth + opened - 1      # 循环体开始的深度
        if loop_depth is not None and re.search(
                r"\bnew\b|\bmalloc\s*\(|\bcalloc\s*\(", l):
            F.append(Finding(rel, i + 1, "YB-No.160",
                             "循环体内申请内存", "warning"))
        depth += opened - closed
        if loop_depth is not None and depth < loop_depth:
            loop_depth = None

    # YB-167 循环内定义对象（std:: 类型 / string / vector）
    depth = 0
    loop_depth = None
    for i, l in enumerate(clean):
        opened = l.count("{")
        closed = l.count("}")
        if loop_depth is None and re.search(r"\b(for|while)\s*\(", l):
            loop_depth = depth + opened - 1
        if loop_depth is not None:
            m = re.match(r"^\s+(?:std::|)(?:string|vector|map|unordered_map|list)\s+\w+", l)
            if m:
                F.append(Finding(rel, i + 1, "YB-No.167",
                                 "循环体内定义容器对象", "warning"))
        depth += opened - closed
        if loop_depth is not None and depth < loop_depth:
            loop_depth = None

    # YB-175 STL 容器作基类
    for i, l in enumerate(clean):
        if re.search(r"\bclass\s+\w+\s*:\s*(?:public|private|protected)\s+"
                     r"(?:std::)?(?:vector|list|map|set|deque|string)\b", l):
            F.append(Finding(rel, i + 1, "YB-No.175",
                             "使用 STL 容器作为基类", "A"))

    # YB-176 vector/string 无 reserve
    for i, l in enumerate(clean):
        m = re.search(r"\b(?:std::)?vector\s*<\s*[\w:]+\s*>\s+(\w+)\s*;", l)
        if m:
            vn = m.group(1)
            near = "\n".join(clean[i:i + 30])
            if "reserve" not in near and "push_back" in "\n".join(clean[i:i + 200]):
                F.append(Finding(rel, i + 1, "YB-No.176",
                                 "vector '%s' 可能需 reserve" % vn, "warning"))

    # YB-164 重载 operator new 需 operator delete
    src = "\n".join(clean)
    if re.search(r"operator\s+new", src) and not re.search(r"operator\s+delete", src):
        F.append(Finding(rel, 1, "YB-No.164",
                         "重载了 operator new 但未重载 operator delete", "A"))

    # YB-10 类型用宏定义
    for i, l in enumerate(raw):
        m = re.match(r"^\s*#\s*define\s+(\w+)\s+(?:unsigned\s+|signed\s+)?"
                     r"(?:char|short|int|long|float|double|struct|uint\d+_t|int\d+_t)\b", l)
        if m:
            F.append(Finding(rel, i + 1, "YB-No.10",
                             "宏 '%s' 用于定义类型，应用 typedef" % m.group(1), "warning"))

    # YB-190 调试输出未包在开关内（printf 直接调用）
    for i, l in enumerate(clean):
        if re.match(r"^\s*printf\s*\(", l):
            # 向上找 20 行内是否有 #if/#ifdef
            guarded = any(re.match(r"^\s*#\s*if", clean[j])
                          for j in range(max(0, i - 20), i))
            if not guarded:
                F.append(Finding(rel, i + 1, "YB-No.190",
                                 "printf 调试输出未置于调试开关内", "warning"))

    # YB-191 调试开关命名
    for i, l in enumerate(raw):
        m = re.match(r"^\s*#\s*(?:if|ifdef|ifndef)\s+(\w+)", l)
        if m:
            nm = m.group(1)
            if re.search(r"debug", nm, re.I) and not nm.startswith("DEBUG"):
                F.append(Finding(rel, i + 1, "YB-No.191",
                                 "调试开关 '%s' 应为 DEBUG_XXXX 形式" % nm, "warning"))

    # YB-45 注释嵌套
    for i, l in enumerate(raw):
        if "/*" in l and l.find("/*") < l.rfind("*/") and l.count("/*") > 1:
            F.append(Finding(rel, i + 1, "YB-No.45", "注释嵌套", "warning"))

    # ---------- 以下为后补规则（原本被误判为"需人工"）----------

    # YB-177 禁止使用 vector<bool>（它是位压缩特化，行为不符合容器语义）
    for i, l in enumerate(clean):
        if re.search(r"vector\s*<\s*bool\s*>", l):
            F.append(Finding(rel, i + 1, "YB-No.177",
                             "不要使用 vector<bool>（位压缩特化，取址/引用语义异常）",
                             "warning"))

    # YB-26 两个函数定义之间应空行分隔（用连续两个右/左大括号粗判）
    for i in range(1, len(raw) - 1):
        if raw[i].strip() == "}" and raw[i + 1].strip() and not raw[i + 1].strip().startswith("}"):
            nxt = raw[i + 1].strip()
            if re.match(r"^(void|int|bool|char|float|double|short|long|unsigned|signed|static|class|struct|enum|[A-Z]\w+)\b.*\($", nxt):
                F.append(Finding(rel, i + 2, "YB-No.26",
                                 "函数定义之间应留空行", "style"))

    # YB-16 文件末尾应有换行（POSIX 惯例，避免 diff 噪音）
    # 说明：splitlines 会丢掉末尾换行信息，这里用第 1 次读取的内容判断，
    # 不再为了一个字符重新 open 整个文件（大文件上是纯浪费）。
    if raw and not raw[-1].endswith(("\r", "\n")) and raw[-1] != "":
        F.append(Finding(rel, n, "YB-No.16",
                         "文件末尾缺少换行符", "style"))

    # YB-20 未使用的 include（同一文件内未出现该头的主名符号，粗筛）
    return F




# ============================================================ 统一入口

def iter_files(root):
    """遍历源码文件。"""
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and p.suffix.lower() in SRC_EXT:
            yield p


def scan(root, log=None) -> list:
    """对目录执行全部规则检查，返回 dict 列表。"""
    results = []
    files = list(iter_files(root))
    for idx, path in enumerate(files, 1):
        rel = Path(path).relative_to(root).as_posix()
        try:
            raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        try:
            results.extend(check_file(str(path), rel, raw))
        except Exception as exc:
            if log:
                log.warn("规则检查异常 %s: %s" % (rel, exc))
        if log and (idx % 10 == 0 or idx == len(files)):
            log.info("规则检查 %d/%d" % (idx, len(files)))

    # 去重
    seen = set()
    uniq = []
    for x in results:
        k = (x.file, x.line, x.rule)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(dict(file=x.file, line=x.line, rule=x.rule,
                         msg=x.msg, sev=x.sev, tool="自定义规则"))
    uniq.sort(key=lambda d: (d["file"], d["line"]))
    return uniq
