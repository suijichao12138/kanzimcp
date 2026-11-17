# -*- coding: utf-8 -*-
"""把本地 shell 脚本上传到编译机并在那边执行，打印输出。

用法:
    python run_remote_script.py <本地脚本.sh> [超时秒=1800]

连接信息走环境变量（必须设置，不写死）:
    KANZI_BUILD_HOST     编译机地址
    KANZI_BUILD_USER     编译机用户名
    KANZI_BUILD_PASSWORD 编译机密码
"""
import os
import sys

import paramiko

HOST = os.environ.get("KANZI_BUILD_HOST", "")
USER = os.environ.get("KANZI_BUILD_USER", "")
PWD = os.environ.get("KANZI_BUILD_PASSWORD", "")

if not HOST or not USER or not PWD:
    raise SystemExit("请设置 KANZI_BUILD_HOST / KANZI_BUILD_USER / KANZI_BUILD_PASSWORD 环境变量后重试")

if len(sys.argv) < 2:
    raise SystemExit(__doc__)
script_path = sys.argv[1]
timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 1800

body = open(script_path, "rb").read().replace(b"\r\n", b"\n")
if body.startswith(b"\xef\xbb\xbf"):
    body = body[3:]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PWD, timeout=20)
sftp = c.open_sftp()
with sftp.open("/tmp/_rr.sh", "wb") as f:
    f.write(body)
sftp.chmod("/tmp/_rr.sh", 0o755)
_, o, e = c.exec_command("bash /tmp/_rr.sh", timeout=timeout)
print(o.read().decode(errors="replace"))
err = e.read().decode(errors="replace")
if err.strip():
    print("[STDERR]", err[-4000:])
c.close()
