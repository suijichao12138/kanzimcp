# -*- coding: utf-8 -*-
"""头文件桩：让 clang-tidy 在 Windows 上能解析 Linux/POSIX 代码。

clang-tidy 不需要真实编译，但需要把头文件找齐才能做语义分析。
本模块生成最小声明桩，只声明源码用到的符号，不实现任何逻辑。
"""
from __future__ import annotations

from pathlib import Path

STUBS = {
"unistd.h": """#pragma once
#include <stddef.h>
#include <stdint.h>
typedef unsigned int useconds_t;
typedef int pid_t;
#ifdef __cplusplus
extern "C" {
#endif
unsigned int sleep(unsigned int seconds);
int usleep(useconds_t usec);
int access(const char* path, int mode);
pid_t getpid(void);
int close(int fd);
unsigned int alarm(unsigned int seconds);
#ifdef __cplusplus
}
#endif
#define F_OK 0
#define R_OK 4
#define W_OK 2
#define X_OK 1
""",

"pthread.h": """#pragma once
#include <stddef.h>
typedef unsigned long pthread_t;
typedef union { char __size[56]; long __align; } pthread_attr_t;
typedef union { char __size[40]; long __align; } pthread_mutex_t;
typedef union { char __size[48]; long __align; } pthread_cond_t;
#ifdef __cplusplus
extern "C" {
#endif
int pthread_create(pthread_t*, const pthread_attr_t*, void*(*)(void*), void*);
int pthread_join(pthread_t, void**);
int pthread_detach(pthread_t);
int pthread_cancel(pthread_t);
pthread_t pthread_self(void);
int pthread_setname_np(pthread_t, const char*);
#ifdef __cplusplus
}
#endif
""",

"sys/types.h": """#pragma once
/* 只放 typedef，不 include 其他系统头，避免与 Windows SDK 冲突 */
typedef long ssize_t;
typedef int pid_t;
typedef unsigned int mode_t;
typedef long off_t;
typedef unsigned int uid_t;
typedef unsigned int gid_t;
typedef unsigned long dev_t;
typedef unsigned long ino_t;
typedef long time_t;
""",

"memory.h": """#pragma once
#include <string.h>
""",

"screen/screen.h": """#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct screen_window screen_window_t;
typedef struct screen_context screen_context_t;
typedef struct screen_buffer screen_buffer_t;
int screen_set_window_property_cv(screen_window_t, int, int, const char*);
int screen_set_window_property_iv(screen_window_t, int, const int*);
int screen_get_window_property_iv(screen_window_t, int, int*);
#ifdef __cplusplus
}
#endif
#define SCREEN_PROPERTY_ID_STRING   1
#define SCREEN_PROPERTY_ALPHA_MODE  2
#define SCREEN_PRE_MULTIPLIED_ALPHA 1
""",

"kanzi/core.ui/font/kzu_bitmap_font.h": """#pragma once
""",
}

MARKER = ".stub-version"
VERSION = "3"


def ensure_stubs(dest: Path, log=None) -> int:
    """生成/刷新头文件桩，返回写入数量。"""
    dest = Path(dest)
    mark = dest / MARKER
    if mark.exists() and mark.read_text(encoding="utf-8").strip() == VERSION:
        return 0

    n = 0
    for name, body in STUBS.items():
        p = dest / name.replace("/", "\\")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body.lstrip("\n"), encoding="utf-8", newline="\n")
        n += 1
    mark.parent.mkdir(parents=True, exist_ok=True)
    mark.write_text(VERSION, encoding="utf-8")

    if log:
        log.info("已生成 %d 个 POSIX 头文件桩 -> %s" % (n, dest))
    return n
