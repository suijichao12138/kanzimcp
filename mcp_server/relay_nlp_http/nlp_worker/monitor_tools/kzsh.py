# -*- coding: utf-8 -*-
"""通过本机 TCP 桥向目标机串口 shell 发送命令并收集回显。

用法: python kzsh.py [--port 47001] [--wait 3] "cmd1" "cmd2" ...
特殊: 命令以 '@cr' 开头表示发送裸回车；'@raw:' 前缀发送原样文本（不加回车）。
输出: 每条命令打印 --- CMD --- 与实际回显（去掉回显行）。
"""
import argparse
import socket
import sys
import time


def read_until_quiet(s, first=0.6, idle=0.8, maxt=25.0):
    s.settimeout(0.15)
    buf = b""
    t0 = time.time()
    last = time.time()
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
        if not buf and time.time() - t0 > first + idle:
            break
        time.sleep(0.05)
    return buf.decode(errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=47001)
    ap.add_argument("--wait", type=float, default=3.0)
    ap.add_argument("cmds", nargs="*")
    a = ap.parse_args()

    s = socket.create_connection(("127.0.0.1", a.port), timeout=5)
    # 清掉残留
    s.settimeout(0.2)
    try:
        while s.recv(65536):
            pass
    except Exception:
        pass

    for cmd in a.cmds:
        if cmd == "@cr":
            s.sendall(b"\r")
            time.sleep(a.wait)
            out = read_until_quiet(s, idle=0.5, maxt=a.wait)
        elif cmd.startswith("@raw:"):
            s.sendall(cmd[5:].encode())
            time.sleep(0.3)
            out = read_until_quiet(s, idle=0.5, maxt=a.wait)
        else:
            s.sendall(cmd.encode() + b"\n")
            time.sleep(a.wait)
            out = read_until_quiet(s, idle=0.8, maxt=max(a.wait, 10))
        print("=" * 20 + " CMD: " + cmd + " " + "=" * 20)
        print(out)
    s.close()


if __name__ == "__main__":
    main()
