# cppCheck 规范覆盖率补全 + AI 语义审查方案

> 版本：v1.0　日期：2026-11-27　状态：**方案设计稿（不含任何代码改动）**
>
> 适用对象：`mcp_server/cppCheck/`（博泰 C/C++ 编码规范静态检查工具）
> 规范依据：《博泰 C++/C 编码规范检查手册（合并版）》224 条
> （仪表组规范 Ver0.5 共 192 条，编号前缀 YB-；博泰规范 V1.0 共 32 条，编号前缀 BT-）

---

## 1. 背景与现状

### 1.1 当前能力

工具由五个引擎 + 一个自研规则模块组成：

| 引擎 | 版本 | 负责范围 |
|---|---|---|
| cppcheck | 2.22.0 | 缺陷检测、内存、可移植性 |
| clang-tidy | LLVM 23.1.4 | 语言规范、C++ Core Guidelines |
| clang-format | 23.1.5 | 代码格式 |
| flawfinder | 2.0.20 | 安全（CWE） |
| lizard | 1.26.1 | 复杂度度量 |
| 自研规则 `rules.py` | — | 41 条硬编码规则 |

### 1.2 覆盖率现状（`data/spec_coverage.json`，224 条）

| 等级 | 含义 | 条数 | 占比 |
|---|---|---|---|
| A | 完全可自动检查 | 83 | 37.1% |
| B | 部分自动（工具能查，但报告给不出具体条款号） | 17 | 7.6% |
| C | 需人工评审（当前无工具覆盖） | 124 | 55.4% |

**条款编号与手册完全一致**：手册 224 条标题 ↔ `spec_coverage.json` 224 条记录，双向差集为 0，无需补录或删减。

### 1.3 已知数据问题

`spec_coverage.json` 的 `level` 字段（必须/建议）与手册 `**级别**` 原文**不匹配**：

- 工具现有统计：必须 206 / 建议 18
- 按手册原文解析：建议条款明显更多（仅 BT 段标注 `[建议]` 的就有 10 条，另有 YB 中明确写"建议"措辞的若干条）

**处置**：以手册原文为准修正 `level` 字段。手册是权威依据，工具统计不得偏离原文。
此项属于数据修正，不涉及引擎逻辑，建议作为第一步先行完成。

---

## 2. 目标

把 C 级 124 条按"最合适的检测手段"全部归位，做到：

1. **能用确定手段覆盖的，绝不交给 AI**（可复现、零成本、速度快）
2. **AI 只兜底最后无法用规则表达的部分**
3. AI 结果**永远单独成栏**，标注【AI 判定需人工复核】，不计入正式问题数
4. **部署环境无 AI 也不影响工具可用性**（静默降级）

---

## 3. 缺口分类结果（124 条全部归位）

按补全手段分为三类，无一条遗漏、无一条重复：

| 手段 | 条数 | 占比 | 说明 |
|---|---|---|---|
| **T —— 工具补配** | 39 | 31.5% | 现成引擎已支持，只需补映射/配置 |
| **S —— 脚本规则** | 51 | 41.1% | 纯结构化分析，正则/AST/统计即可 |
| **A —— AI 语义审查** | 34 | 27.4% | 设计意图、命名语义、主观判断 |
| 合计 | 124 | 100% | |

### 3.1 覆盖率提升预估

| 阶段 | 覆盖条数 | 覆盖率 |
|---|---|---|
| 现状（A+B） | 100 | 44.6% |
| + T 类（工具补配） | 139 | 62.1% |
| + S 类（脚本规则） | 190 | 84.8% |
| + A 类（AI 语义审查） | 224 | **100%**（其中 34 条标注需人工复核） |

---

## 4. T 类：工具补配（39 条）

**原则**：不写新检测逻辑，只把现有引擎的能力接到规范条款上。

### 4.1 clang-tidy 扩映射（约 24 条）

现状：`engines.py` 的 `TIDY_TO_SPEC` 只映射了 36 条 clang-tidy check。

需补充的映射（条款 → clang-tidy check）：

| 条款 | 类型 | 规范要求 | clang-tidy check |
|---|---|---|---|
| YB-No.12 | 1 | 不用原始类型 char/int，用 int8_t 等 | `google-runtime-int`, `cppcoreguidelines-use-enum-class`(辅助) |
| YB-No.188 | 16 | 同上（可移植性视角） | `google-runtime-int` |
| YB-No.79 | 6 | 不返回局部变量的引用/指针 | `clang-analyzer-core.StackAddressEscape` |
| YB-No.116 | 8 | 不返回内部数据的指针/引用 | `cppcoreguidelines-pro-type-const-cast`(辅助) + 自研补充 |
| YB-No.155 | 11 | 不返回引用参数的地址 | `clang-analyzer-core.ReturnOfPointerToLocal` |
| YB-No.154 | 11 | 局部对象地址不外泄 | `clang-analyzer-core.StackAddressEscape` |
| YB-No.104 | 8 | 数据成员必须私有 | `cppcoreguidelines-non-private-member-variables-in-classes` |
| YB-No.107 | 8 | 初始化列表顺序与声明一致 | `-Wreorder-ctor`（`clang-diagnostic-reorder-ctor`） |
| YB-No.114 | 8 | operator= 返回 *this 引用 | `cppcoreguidelines-c-copy-assignment-signature` |
| YB-No.118 | 8 | 避免指针/数字区分重载 | `clang-diagnostic-overloaded-virtual`(部分) + 脚本补充 |
| YB-No.140 | 10 | 浮点不用 == / != 比较 | `bugprone-float-equal`（新版）或 `cert-flp37-c` |
| YB-No.132 | 10 | 布尔表达式内不赋值 | `clang-diagnostic-parentheses` + `bugprone-assignment-in-if-condition` |
| YB-No.144 | 11 | 所有函数都有 return | `clang-diagnostic-return-type` |
| YB-No.146 | 11 | 检查非 void 返回值 | `bugprone-unused-return-value` |
| YB-No.153 | 11 | if...else if 必须以 else 结束 | `bugprone-switch-missing-default-case`(类比) + 脚本补充 |
| YB-No.163 | 12 | new[] 配 delete[] | `clang-analyzer-cplusplus.NewDeleteLeaks`, `-Wmismatched-new-delete` |
| YB-No.165 | 12 | 析构函数删指针成员并置空 | `clang-analyzer-cplusplus.NewDelete` + 脚本补充 |
| YB-No.181 | 15 | 析构函数不抛异常 | `bugprone-exception-escape` |
| YB-No.63 | 7 | 禁用递归 | `clang-diagnostic-recursion`(无) → **改用脚本，见 5.x** |
| YB-No.106 | 8 | 静态成员用 :: 访问 | `clang-diagnostic-static-access`（或脚本） |
| YB-No.122 | 8 | 不重定义继承的缺省参数 | `clang-diagnostic-overriding-method`(部分) + 脚本 |
| YB-No.78 | 6 | 强转不去除 const/volatile | `cppcoreguidelines-pro-type-const-cast` |
| YB-No.92 | 9 | 指针减法限于同一数组 | `clang-analyzer-security.ArrayBound`(部分) |
| BT-4.7-7 | 12 | 解引用前判空 | `clang-analyzer-core.NullDereference` |

**注意**：clang-tidy 的 check 名随版本变化，落地前必须以本地 23.1.4 版本 `--list-checks` 实测为准，不可照抄。

### 4.2 clang-format 配置补齐（约 7 条）

在 `config/.clang-format` 中增加/调整：

| 条款 | 规范要求 | 配置项 |
|---|---|---|
| YB-No.27 | 函数内按逻辑分段留空行 | `SeparateDefinitionBlocks: Always`（仅函数间）需配合脚本 |
| YB-No.28 | 宏/全局变量/声明之间留空行 | `EmptyLineBeforeAccessModifier` + 脚本补充 |
| YB-No.35 | 问号表达式前后有空格 | `SpacesAroundTernaryOperators`（新版） |
| YB-No.141 | case 独占一行 | `IndentCaseLabels: true` + 脚本补充 |
| YB-No.28 | 声明间空行 | `MaxEmptyLinesToKeep`, `KeepEmptyLinesAtTheStartOfBlocks` |
| YB-No.22（已有） | 行宽 80 | `ColumnLimit: 80`（已配置） |
| YB-No.40（已有） | Tab 缩进 | `UseTab: Always`（已配置） |

### 4.3 cppcheck 补充（约 5 条）

| 条款 | 规范要求 | cppcheck 能力 |
|---|---|---|
| YB-No.76 | 不超过一定大小的局部变量 | 无法直接查，**改用脚本（栈上数组大小检查）** |
| YB-No.94 | 结构体成员按大小排列 | `--enable=style` 下 `structMemberShadows` 不覆盖 → **改用脚本** |
| YB-No.166/167 | 循环内不定义对象/不重复调用 | `--enable=performance` 部分覆盖 |
| YB-No.176 | vector 使用 reserve | `--enable=performance` 无 → **脚本** |
| YB-No.173/178/180 | STL 用法 | `--enable=style` 部分覆盖 |

### 4.4 flawfinder 补充（约 3 条）

| 条款 | 规范要求 | flawfinder 能力 |
|---|---|---|
| BT-4.7-7 | 指针解引用前判空 | CWE-476 NULL Pointer Dereference |
| YB-No.76 | 栈缓冲区过大 | CWE-121/122 部分覆盖 |
| YB-No.163 | new[]/delete[] 配对 | 无 → clang-tidy 覆盖 |

### 4.5 T 类结论

- **约 39 条可通过配置补齐，无需新写检测代码**
- 主要工作量在：核对 clang-tidy 23.1.4 实际 check 名、补充 `TIDY_TO_SPEC` 映射、调整 `.clang-format`
- 预计 1~2 天

---

## 5. S 类：脚本规则（51 条）

**原则**：不需要语义理解，纯结构化分析。可作为 `rules.py` 的新规则，或新建 `rules_extra.py` 分模块管理。

### 5.1 按实现难度分三档

#### S1 档：纯正则，当天可完成（约 22 条）

| 条款 | 类型 | 规范要求 | 实现思路 |
|---|---|---|---|
| YB-No.14 | 2 | 文件不超过 2000 行 | 统计行数 |
| YB-No.50 | 14 | 函数不超过 100 行 | lizard 已有数据，补映射 |
| BT-4.4-3 | 7 | 函数不超过 200 行 | 同上 |
| BT-4.4-4 | 7 | 参数不超过 5 个 | 解析函数签名逗号数 |
| YB-No.60 | 7 | 参数不超过 7 个 | 同上 |
| YB-No.137 | 11 | 嵌套不超过 4 级 | lizard 有 CCN/嵌套度 |
| YB-No.51 | 14 | 继承深度不超过 4 | 正则 `class X : ... public Y` 构建继承图 |
| YB-No.52 | 14 | 类耦合不超过 5 | 统计类内引用的其他类数量 |
| YB-No.89 | 9 | 多维数组初始化用花括号匹配 | 正则匹配 `= {` 后的结构 |
| YB-No.90 | 9 | 数组初始化不多写逗号 | 已有 YB-No.98 同类实现可参考 |
| YB-No.134 | 10 | 数值范围从左到右递增 | 正则提取 `a < x && x < b` 比较 |
| YB-No.135 | 10 | 常数写左边 `5 == x` | 正则 `\b\w+\s*==\s*\d` |
| YB-No.128 | 3 | 宏参数要括起来 | 解析 `#define F(x) body`，检查 x 是否被括号包裹 |
| YB-No.129 | 3 | 宏参数不得变化 | 检查宏体内是否出现 `x++`、`--x` 等 |
| YB-No.139 | 10 | &&/|| 两侧加括号 | 正则匹配无括号的复合条件 |
| YB-No.133 | 10 | 条件语句括号不超过 2 层 | 统计 `if (...)` 内嵌套括号深度 |
| YB-No.136 | 10 | 复杂运算加括号 | 检测混合运算符表达式无括号 |
| YB-No.17 | 2 | 头文件各区段结构 | 检查 `#ifndef/#define/#include/typedef/class/#endif` 顺序 |
| YB-No.192 | 16 | 调试开关定义位置 | 检查 `#define DEBUG*` 是否在文件前部 |
| YB-No.48 | 5 | 预编译宏要有注释 | 检查 `#if/#ifdef` 行尾或上一行有无注释 |
| YB-No.102 | 8 | 类成员分两段（函数在前、变量在后） | 解析类的访问区段顺序 |
| YB-No.3 | 1 | 标识符不以大小写/下划线区分 | 同文件内标识符归一化后查重 |

#### S2 档：需要轻量解析，2~3 天（约 19 条）

| 条款 | 类型 | 规范要求 | 实现思路 |
|---|---|---|---|
| YB-No.5 | 1 | typedef 类型名唯一 | 全工程收集 typedef，查重 |
| YB-No.6 | 1 | 类/联合/枚举名唯一 | 全工程收集，查重 |
| YB-No.7 | 1 | 静态变量/函数名不重复 | 按作用域收集静态符号 |
| YB-No.8 | 1 | 标识符不跨类别复用 | 建立"名称 → 类别"表，冲突报告 |
| BT-4.6-3 | 1 | 类/结构/枚举名唯一；局部与全局不重名 | 同上，加作用域链 |
| YB-No.9 | 1 | 一个数据类型只定义一次（ODR） | 全工程同名 struct/class 对比定义体 |
| YB-No.124 | 1 | 全局命名空间只有 main/namespace/extern "C" | 解析顶层声明 |
| YB-No.126 | 1 | 头文件不得有匿名命名空间 | 正则 `namespace\s*\{` 在 .h 文件 |
| BT-4.2-1 | 2 | 每个 .cpp 有对应 .h | 文件配对检查 |
| BT-4.2-4 | 2 | include 顺序：自身头 → 标准库 → 自定义 | 解析 #include 块顺序 |
| BT-4.1-1 | 1 | C++ 标准 ≥ C++14 | 检查 `--std` 配置或 `__cplusplus` |
| YB-No.62 | 7 | 不用宏函数，用 inline | 检测 `#define F(...)` 含完整语句体 |
| YB-No.64 | 7 | 显式声明返回类型 | 正则匹配隐式 int 函数（老式 C 风格） |
| YB-No.65 | 7 | 无返回值用 void | 配合上一条 |
| YB-No.66 | 7 | 函数声明必须含形参名 | 检查 `void f(int);` 形式 |
| YB-No.69 | 7 | 非虚函数无未使用参数 | 参数名在函数体内是否出现 |
| YB-No.70 | 7 | 虚函数重写无未使用参数 | 同上（需识别虚函数） |
| YB-No.72 | 7 | 源文件内不重复声明外部函数 | 对比本文件声明与已 include 的头 |
| YB-No.101 | 8 | 成员函数不定义在类内 | 解析类体内是否有函数体 |

#### S3 档：需要跨文件/跨函数分析，3~4 天（约 10 条）

| 条款 | 类型 | 规范要求 | 实现思路 |
|---|---|---|---|
| YB-No.99 | 8 | 类声明与实现分离（.h / .cpp） | 检测 .h 中的内联实现 |
| YB-No.94 | 9 | 结构体成员按大小升序排列 | 需要类型大小表（含 typedef 展开） |
| BT-4.3-3 | 6 | 无未使用变量/无未使用自定义结构 | 全工程引用分析 |
| BT-4.5-1 | 6 | 未被修改的变量加 const | 变量赋值次数统计 |
| BT-4.5-3 | 6 | 变量先定义后使用 | 作用域声明序检查 |
| BT-4.7-1 | 6 | 跨文件全局变量用头文件引用 | extern 声明位置检查 |
| YB-No.85 | 6 | 全局变量只通过 get/set 访问 | 全局变量直接读写检测 |
| YB-No.187 | 15 | 超时用单调时钟 | 检测 `clock_gettime(CLOCK_MONOTONIC)` 使用 |
| YB-No.189 | 16 | 注意类/结构体对齐 | 计算对齐、检查 `#pragma pack` |
| YB-No.63 | 7 | 禁用递归 | 构建调用图，检测环 |

### 5.2 S 类结论

- **51 条全部可实现，无需 AI**
- S1 档 22 条当天可完成，S2 档约 19 条 2~3 天，S3 档约 10 条 3~4 天
- 建议新建 `codescan/rules_extra.py` 承载，与现有 `rules.py` 分离，避免单文件膨胀
- 每条规则必须**带条款编号**输出，直接写进报告

---

## 6. A 类：AI 语义审查（34 条）

**原则**：只审确定手段无法表达的语义/设计意图/主观判断事项。

### 6.1 AI 审查范围（34 条清单）

#### 命名语义类（6 条）

| 条款 | 类型 | 规范要求 | 为何必须 AI |
|---|---|---|---|
| YB-No.1 | 1 | 缩略语应保留可读性 | 需判断缩写是否可理解 |
| YB-No.11 | 1 | 布尔用正谓词（IS_AVAILABLE 而非 IS_NOT_AVAILABLE） | 需理解语义正负 |
| YB-No.13 | 1 | 模块命名反映功能 | 需理解模块职责 |
| BT-4.6-1 | 1 | 小驼峰 / 成员 m 前缀 / 指针 p 前缀 | 需识别单词边界（部分可脚本，语义部分给 AI） |
| YB-No.55 | 7 | 函数名首字母大写、不以大小写区分 | 同上 |
| YB-No.103 | 8 | 成员函数名每单词首字母大写 | 同上 |

#### 函数命名与说明类（6 条）

| 条款 | 类型 | 规范要求 |
|---|---|---|
| YB-No.56 | 7 | 动宾形式命名（OpenDevice / CheckFileState） |
| YB-No.57 | 7 | 函数名描述返回值 |
| YB-No.58 | 7 | 对仗命名（add/remove、open/close） |
| YB-No.59 | 7 | 函数应有说明（注释块完整） |
| YB-No.67 | 7 | 参数按输入/修改/输出顺序，并标注 |
| YB-No.68 | 7 | 同类参数顺序一致 |

#### 注释质量类（4 条）

| 条款 | 类型 | 规范要求 |
|---|---|---|
| YB-No.42 | 5 | 单行注释在上方或行尾；多行注释在上方 |
| YB-No.43 | 5 | 注释解释目的与功能，不重复代码 |
| YB-No.46 | 5 | 难懂的分支条件加注释 |
| YB-No.47 | 5 | 难懂的循环说明出口条件 |

#### 设计意图类（10 条）

| 条款 | 类型 | 规范要求 |
|---|---|---|
| YB-No.53 | 7 | 构建函数的 5 个理由（降复杂度、引入抽象、隐藏细节等） |
| YB-No.80 | 6 | 变量只承担一个用途 |
| YB-No.61 | 7 | 结构体参数用指针传递 |
| YB-No.109 | 8 | 全局静态对象使用前已初始化 |
| YB-No.115 | 8 | 派生类赋值函数重赋基类成员 |
| YB-No.119 | 8 | 尽量推迟变量定义 |
| YB-No.123 | 8 | 慎用友元 |
| YB-No.170 | 13 | 避免类模板有潜在冲突方法 |
| YB-No.171 | 13 | 模板仅在行为与类型无关时使用 |
| BT-4.3-2 | 6 | 少用全局变量、少暴露 public 方法 |

#### 控制流语义类（8 条）

| 条款 | 类型 | 规范要求 |
|---|---|---|
| YB-No.148 | 11 | 建议一个函数一个 return |
| BT-4.4-1 | 7 | 有返回值函数需判断返回值；void 函数应有副作用；函数至少被调用一次 |
| BT-4.4-2 | 7 | 不存在死循环 |
| BT-4.4-7 | 7 | 调用可能出错的函数后立即判断 |
| BT-4.7-6 | 11 | switch 逻辑复杂时用状态机 |
| YB-No.184 | 15 | 等待外部消息要有超时 |
| YB-No.185 | 15 | 状态变量使用前后都要初始化 |
| YB-No.186 | 15 | 等待条件变量要有超时，超时设为正常耗时 2 倍 |

### 6.2 技术选型：GitHub Copilot SDK（强制要求）

**必须使用 Copilot SDK，不得依赖云端 AI API。** 原因：部署环境为内网，不能保证有外网 AI 服务。

#### 依据：本机已有成熟实现

`/root/.openclaw/workspace/copilot-worker/nlp_worker_sdk_runtime/copilot_runtime.py`（1802 行，运行中）：

```python
from copilot import CopilotClient, RuntimeConnection, define_tool

options = {
    "working_directory": ...,
    "github_token": cfg.github_token,      # 可为 None
    "use_logged_in_user": True,            # 用本机 Copilot CLI 已登录账号
    "base_directory": ...,
    "log_level": "warning",
}
client = CopilotClient(**options)
await client.start()
session = await client.create_session(...)
await session.send(prompt)                 # 通过 session.on() 收事件
```

依赖（`requirements.txt`）：

```
github-copilot-sdk>=1.0.11,<1.1
httpx>=0.28,<1
pydantic>=2.11,<3
python-dotenv>=1.1,<2
PyYAML>=6.0.2,<7
websockets>=15,<16
```

#### 部署要求

| 项 | 要求 |
|---|---|
| Python 包 | `github-copilot-sdk>=1.0.11,<1.1`（其余依赖已在或可补） |
| 本机 CLI | 安装 GitHub Copilot CLI 并完成登录（`login_copilot.cmd`） |
| 认证 | `use_logged_in_user: true`，无需把 token 写进配置 |
| 打包 | PyInstaller 需带 Copilot runtime（参照 `bundled_runtime_path()`） |

#### 可用性探测（关键）

**不得等跑到一半才发现没登录。** 检查开始时先做一次轻量探测：

```
CopilotClient(...).start() → list_models()
```

- 成功 → 继续 AI 审查
- 失败 → 跳过 AI，报告标注原因，**不阻塞静态检查结果**

---

## 7. 交互设计

### 7.1 工程标题行新增勾选框

```
┌──────────────────────────────────────────────────┐
│ ☑ 工程A            [检查] [重新检查] [删除]       │
│ ☑ 工程B            [检查] [重新检查] [删除]       │
│ ☐ 工程C            [检查] [重新检查] [删除]       │
└──────────────────────────────────────────────────┘
```

| 项 | 设计 |
|---|---|
| 位置 | 每个工程标题行最左侧 |
| 默认状态 | **勾选** |
| 含义 | 使用 AI 进行语义、设计意图或主观判断的检查 |
| 持久化 | 存入 `data/projects/<工程名>/meta.json` 的 `ai_check` 字段 |
| 触发时机 | 仅在点「检查」或「重新检查」时读取，不实时触发 |

**不新增按钮**，复用现有「检查 / 重新检查」。

### 7.2 执行流

```
点「检查」或「重新检查」
  │
  ├─ 读取该工程 meta.ai_check（默认 true）
  │
  ├─【第一层】静态检查：cppcheck / clang-tidy / clang-format / flawfinder / lizard / 自研规则
  │     └─ 输出：T + S 类条款的确定性结果
  │
  ├─ if ai_check == true:
  │     ├─ 探测 Copilot SDK 可用性
  │     │    ├─ 不可用 → 记录「AI 不可用：<原因>」，跳过
  │     │    └─ 可用   → 继续
  │     ├─ 筛选 A 类 34 条条款
  │     ├─ 按函数边界切分代码单元
  │     ├─ 分批调用 Copilot SDK（并发上限 2~3）
  │     └─ 解析结构化 JSON 结果
  │
  └─【第二层】合并报告
        ├─ 静态问题：正式栏
        └─ AI 建议：单独栏 + 【AI 判定需人工复核】标注
```

### 7.3 报告呈现

```markdown
## 检查概览
静态问题：23 条
AI 建议：7 条【需人工复核】
规范覆盖率：212 / 224（94.6%）

## 静态检查问题（可复现）
| 文件:行号 | 条款 | 级别 | 描述 |
|---|---|---|---|
| UI_Main.cpp:42 | YB-No.22 | 必须 | 行宽 95 > 80 列 |

## AI 语义审查建议【AI 判定需人工复核】
| 文件:行号 | 条款 | 级别 | AI 判断 | 置信度 |
|---|---|---|---|---|
| UI_Main.cpp:88 | YB-No.80 | 必须 | 变量 used 同时承担循环计数与数组索引两种用途 | 中 |
| UI_Main.cpp:120 | YB-No.43 | 必须 | 注释仅重复函数名，未说明目的 | 高 |
```

**硬性规则**：

1. AI 结果**单独成栏**，绝不混入正式问题列表
2. 每条 AI 结果必须带 **`【AI 判定需人工复核】`** 标记
3. AI 结果**不计入**正式问题数统计
4. AI 不可用时，报告加一行说明，其余内容正常输出

---

## 8. AI 审查的工程化设计

### 8.1 代码切分策略

| 策略 | 做法 |
|---|---|
| 只审有实现代码的文件 | 跳过空文件、纯声明头文件 |
| 按函数切段 | 每个函数（含上方注释块）为一个审查单元，通常 20~80 行 |
| 条款与单元配对 | 不是每段代码查所有条款；命名类只审签名与首几行，注释类只审注释块 |
| 批量提交 | 一次 prompt 送 5~10 个函数 + 对应条款，控制 token |
| 并发限制 | 最多 2~3 个并发 session |

### 8.2 Session 管理

- **每个批次新建 session，用完销毁**
- **禁止复用 session** —— 前一批代码会污染后一批判断

### 8.3 输出格式

必须返回可解析 JSON，不接受自由文本：

```json
{
  "findings": [
    {
      "line": 88,
      "clause": "YB-No.80",
      "hit": true,
      "reason": "变量同时用于循环计数与数组索引",
      "confidence": "中"
    }
  ]
}
```

解析失败时重试 1 次；仍失败则丢弃并记日志，不写入报告。

### 8.4 成本与时长预估

以 5000 行中等工程为例：

| 项 | 估算 |
|---|---|
| 函数单元数 | 约 100 个 |
| 批次数量 | 10~15 批 |
| 时长 | 15~30 分钟 |
| 并发数 | 2~3 |

---

## 9. 代码改造清单（本次不实施，仅列范围）

| 文件 | 改动内容 |
|---|---|
| `data/spec_coverage.json` | 修正 `level` 字段以匹配手册原文；T/S 类条款的 `grade` 由 C 改为 A；A 类保持 C 并加标记 |
| `codescan/engines.py` | 扩充 `TIDY_TO_SPEC` 映射；lizard 数据补映射；cppcheck/flawfinder 参数调整 |
| `config/.clang-format` | 补充格式类条款对应配置 |
| `codescan/rules_extra.py` | **新建**，承载 S 类 51 条脚本规则 |
| `codescan/ai_review.py` | **新建**，Copilot SDK 封装、prompt 模板、结果解析、可用性探测 |
| `codescan/report.py` | 报告新增「AI 语义审查建议」分栏与统计 |
| `codescan/cli.py` | `scan` 新增 `--ai` / `--no-ai` 参数 |
| `deployer/web/scan_api.py` | 工程 meta 增 `ai_check` 字段；检查时透传；AI 结果合并 |
| `deployer/web/static/app.js` | 工程标题行加勾选框；提交时带上 `ai_check` |
| `cppCheck.spec` | `hiddenimports` 增 `copilot`；打包 Copilot runtime |

---

## 10. 实施建议顺序

| 阶段 | 内容 | 预计工期 | 覆盖率 |
|---|---|---|---|
| **第 0 步** | 修正 `spec_coverage.json` 的 `level` 字段 | 0.5 天 | 不变（数据准确性） |
| **第 1 期** | T 类：工具补配 39 条 | 1~2 天 | 44.6% → 62.1% |
| **第 2 期** | S1 档脚本 22 条 | 1 天 | 62.1% → 71.9% |
| **第 3 期** | S2 + S3 档脚本 29 条 | 4~6 天 | 71.9% → 84.8% |
| **第 4 期** | A 类：AI 审查框架 + 34 条 | 2~3 天 | 84.8% → 100%（34 条标注复核） |
| **第 5 期** | deployer 网页勾选框 + 报告分栏 | 1~2 天 | 产品化 |

**建议先做 0、1、2 期**：全部确定性改造，无 AI 不确定性风险，做完覆盖率已达 71.9%。

---

## 11. 风险与注意事项

| 风险 | 影响 | 应对 |
|---|---|---|
| clang-tidy check 名随版本变化 | 映射写错导致静默失效 | 落地前用 23.1.4 `--list-checks` 实测核对 |
| AI 审查结果不稳定 | 同一代码两次结果不同 | 单独分栏 + 标注复核 + 不计入正式统计 |
| Copilot SDK 未登录 | AI 部分不可用 | 启动探测 + 静默降级 + 报告注明原因 |
| AI 审查耗时过长 | 用户体验差 | 并发控制 + 分批 + 进度显示 |
| 脚本规则误报 | 干扰真实问题 | 每条规则先在真实代码库回归验证 |
| 单文件规则膨胀 | `rules.py` 难维护 | S 类规则独立到 `rules_extra.py` |

---

## 12. 待确认事项

1. **勾选框状态存储位置** —— 建议 `data/projects/<工程名>/meta.json` 的 `ai_check`
2. **AI 审查失败是否影响整体检查** —— 建议不影响，静态结果照常输出
3. **AI 不可用提示方式** —— 建议报告内一行说明，不弹错误框
4. **AI 结果是否计入问题总数** —— 建议不计入，单独统计

---

*本文档仅为方案设计，不含代码改动。经确认后方可进入实施阶段。*
