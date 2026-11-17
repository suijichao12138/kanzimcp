# -*- coding: utf-8 -*-
"""从编译机下载文件到本地。

用法:
    python get_remote.py <远端路径> <本地路径>

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

if len(sys.argv) < 3:
    raise SystemExit(__doc__)
remote, local = sys.argv[1], sys.argv[2]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PWD, timeout=20)
sftp = c.open_sftp()
sftp.get(remote, local)
c.close()
print("downloaded", remote, "->", local)
