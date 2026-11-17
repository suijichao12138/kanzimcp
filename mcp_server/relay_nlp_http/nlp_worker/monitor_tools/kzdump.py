# -*- coding: utf-8 -*-
"""发送一条命令并把原始回显落盘（长超时，适合 cat/grep 大输出）。

用法: python kzdump.py <输出文件> <maxt秒> "cmd"
"""
import socket
import sys
import time

PORT = 47001
out_path = sys.argv[1]
maxt = float(sys.argv[2])
cmd = sys.argv[3]

s = socket.create_connection(("127.0.0.1", PORT), timeout=5)
s.settimeout(0.2)
try:
    while s.recv(65536):
        pass
except Exception:
    pass

s.sendall(cmd.encode() + b"\n")

buf = b""
t0 = time.time()
last = time.time()
quiet_to = 4.0
s.settimeout(0.1)
while time.time() - t0 < maxt:
    try:
        d = s.recv(65536)
        if d:
            buf += d
            last = time.time()
            continue
    except socket.timeout:
        pass
    except Exception:
        break
    if buf and time.time() - last > quiet_to:
        break
    time.sleep(0.02)
s.close()

with open(out_path, "wb") as f:
    f.write(buf)
print("bytes=%d elapsed=%.1fs -> %s" % (len(buf), time.time() - t0, out_path))
