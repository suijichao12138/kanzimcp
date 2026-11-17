# -*- coding: utf-8 -*-
"""把「串口 shell 里的 monitor telnet 会话」包装成一个干净的 Monitor RemoteConsole TCP 端点，
给官方 monitor-web-ui 用（仪表没有网线时用这条链路）。

    web-ui  ──TCP──>  本脚本 :<listen>  ──串口──>  仪表 shell ──telnet──> 127.0.0.1:56000

用法:
    python monitor_tools\\webui_bridge.py --com COM3 --baud 115200 --listen 47002

起好后另开一个窗口:
    monitor_tools\\monitor-web-ui\\monitor-web-ui-win64.exe --monitor-host 127.0.0.1 --monitor-port 47002

说明:
    * 串口 shell 的 tty 会把输入回显，官方 bridge.py 会把回显当成响应首行导致 JSON 解析失败，
      本脚本负责丢掉回显行，只转发真正的响应，并用空行作为结束标记（与 RemoteConsole 协议一致）。
    * telnet 会话断了（应用重启/串口复位）会自动重连，重连失败就把错误文本返回给调用方。
"""
import argparse
import socket
import sys
import time

import serial

PROMPT_HINTS = (b"# ", b"$ ", b"telnet> ")


class SerialLink(object):
    def __init__(self, com, baud):
        self.ser = serial.Serial(com, baud, timeout=0.05)
        self.buf = b""

    def write(self, data):
        self.ser.write(data)
        self.ser.flush()

    def _pump(self):
        try:
            data = self.ser.read(4096)
        except Exception:
            return b""
        if data:
            self.buf += data
        return data

    def read_until(self, markers, timeout):
        """读到出现任一 marker（bytes）或超时；返回 (data, hit)。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for m in markers:
                if m in self.buf:
                    i = self.buf.index(m) + len(m)
                    out, self.buf = self.buf[:i], self.buf[i:]
                    return out, True
            self._pump()
        out, self.buf = self.buf, b""
        return out, False

    def drain(self, seconds=0.35):
        deadline = time.time() + seconds
        while time.time() < deadline:
            self._pump()
        out, self.buf = self.buf, b""
        return out

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


class Bridge(object):
    def __init__(self, link, console_port, cmd_timeout):
        self.link = link
        self.console_port = console_port
        self.cmd_timeout = cmd_timeout
        self.in_telnet = False

    def ensure_shell(self, timeout=6.0):
        """确保停在 shell 提示符（不是 telnet 里）。"""
        self.link.write(b"\r")
        data, hit = self.link.read_until(PROMPT_HINTS, timeout)
        return hit

    def open_session(self, timeout=15.0):
        self.in_telnet = False
        if not self.ensure_shell():
            return False
        self.link.write(("telnet 127.0.0.1 %d\n" % self.console_port).encode())
        data, hit = self.link.read_until((b"Connected to", b"Connection refused", b"not found"), timeout)
        text = data.decode(errors="replace")
        if b"Connected to" in data:
            self.in_telnet = True
            self.link.drain(0.4)
            return True
        sys.stderr.write("[bridge] telnet failed: %s\n" % text.strip()[-200:])
        return False

    def send(self, cmd):
        """发一条命令，返回去掉回显的响应行列表；失败返回 None。"""
        if not self.in_telnet:
            if not self.open_session():
                return None
        self.link.drain(0.15)
        self.link.write(cmd.encode() + b"\n")
        raw, hit = self.link.read_until((b"\r\n\r\n", b"\n\n"), self.cmd_timeout)
        if not hit:
            # 没等到结束空行：可能是会话断了 / 响应被回显冲散
            if not self.link.buf and b"telnet>" in raw:
                self.in_telnet = False
            if not raw.strip():
                self.in_telnet = False
                return None
        lines = raw.replace(b"\r\n", b"\n").split(b"\n")
        out = []
        for line in lines:
            s = line.decode(errors="replace")
            stripped = s.strip()
            if not stripped:
                continue
            if stripped == cmd.strip():          # 串口 tty 的输入回显
                continue
            if stripped in ("#", "$"):           # shell 提示符
                continue
            if stripped.endswith("Escape character is '^]'."):
                continue
            out.append(s)
        return out


def serve(args):
    link = SerialLink(args.com, args.baud)
    bridge = Bridge(link, args.console_port, args.cmd_timeout)
    if not bridge.open_session():
        sys.stderr.write("[bridge] cannot enter monitor console on %s\n" % args.com)
        link.close()
        return 1

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", args.listen))
    srv.listen(4)
    print("[bridge] %s@%d -> monitor console %d -> 127.0.0.1:%d" %
          (args.com, args.baud, args.console_port, args.listen), flush=True)
    print("[bridge] run: monitor-web-ui-win64.exe --monitor-host 127.0.0.1 --monitor-port %d" % args.listen,
          flush=True)

    try:
        while True:
            conn, addr = srv.accept()
            print("[bridge] client connected %s" % (addr,), flush=True)
            conn.settimeout(None)
            pending = b""
            try:
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    pending += chunk
                    while b"\n" in pending:
                        line, pending = pending.split(b"\n", 1)
                        cmd = line.decode(errors="replace").strip()
                        if not cmd:
                            continue
                        t0 = time.time()
                        resp = bridge.send(cmd)
                        if resp is None:
                            conn.sendall(b'{"error": "Not connected to Monitor"}\r\n\r\n')
                            if not bridge.open_session():
                                print("[bridge] monitor console lost, keep retrying on next command", flush=True)
                                break
                            continue
                        payload = b"\r\n".join(x.encode() for x in resp) + b"\r\n\r\n"
                        conn.sendall(payload)
                        print("[bridge] %s -> %d line(s), %.2fs" %
                              (cmd, len(resp), time.time() - t0), flush=True)
            except Exception as e:
                print("[bridge] client error: %s" % e, flush=True)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
                print("[bridge] client disconnected", flush=True)
    except KeyboardInterrupt:
        print("[bridge] shutting down, leaving monitor console...", flush=True)
        try:
            link.write(b"\x1d")
            time.sleep(0.8)
            link.write(b"quit\n")
            time.sleep(0.5)
            link.drain(0.3)
        except Exception:
            pass
    finally:
        link.close()
        srv.close()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--com", default="COM3")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--listen", type=int, default=47002)
    ap.add_argument("--console-port", type=int, default=56000)
    ap.add_argument("--cmd-timeout", type=float, default=60.0)
    args = ap.parse_args()
    return serve(args)


if __name__ == "__main__":
    sys.exit(main())
