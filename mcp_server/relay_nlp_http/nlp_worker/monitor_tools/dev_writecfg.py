# -*- coding: utf-8 -*-
"""把本地 cfg 文件逐行经串口 shell 写入目标机（echo 追加法）。"""
import socket
import sys
import time


def read_quiet(s, idle=0.6, maxt=6.0):
    s.settimeout(0.15)
    buf = b""
    last = time.time()
    t0 = time.time()
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
        if buf and time.time() - last > idle:
            break
        time.sleep(0.05)
    return buf.decode(errors="replace")


def main():
    local = sys.argv[1]
    remote = sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 47001
    lines = [l.rstrip("\r\n") for l in open(local, encoding="utf-8") if l.strip()]
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.settimeout(0.2)
    try:
        while s.recv(65536):
            pass
    except Exception:
        pass
    first = True
    for ln in lines:
        redir = ">" if first else ">>"
        first = False
        cmd = "echo '%s' %s %s" % (ln, redir, remote)
        s.sendall(cmd.encode() + b"\n")
        time.sleep(0.5)
        read_quiet(s)
    s.sendall(("cat %s" % remote).encode() + b"\n")
    time.sleep(1.0)
    print(read_quiet(s, idle=1.0, maxt=8))
    s.close()


if __name__ == "__main__":
    main()
