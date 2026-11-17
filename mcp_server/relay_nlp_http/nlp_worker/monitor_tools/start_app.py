# -*- coding: utf-8 -*-
"""停默认程序 + 起测试程序 + 判定启动成功（全部经串口中继桥，无需手动敲命令）。

前置：serial_bridge.py 已起在 --bridge-port 上。

用法（最简，只起程序）:
    python start_app.py --deploy-dir /var/log/test --app clusterHmiMin \
        --config /mnt/usr/share/theme/application_cluster_hmi.cfg

常用变体:
    # 先停掉量产程序再起测试程序
    python start_app.py --deploy-dir /var/log/test --app clusterHmiMin \
        --config /mnt/usr/share/theme/application_cluster_hmi.cfg \
        --default-app clusterHmi --stop-default

    # 需要资源加载剖析数据
    ... --env HMI_RES_PROFILING=1

    # 剖析库不在 <deploy-dir>/kzprof
    ... --lib-dir /var/log/test/prof

关键约定（缺一个就白跑，脚本已强制）:
    1) 启动前先 cd 到 --deploy-dir：trace 文件写到进程 CWD
    2) 必带 LD_LIBRARY_PATH=<lib-dir>:<deploy-dir>：否则退到系统 Release 引擎库 -> ABI 不符 SIGSEGV
    3) 必带 '> log 2>&1 &'：否则串口控制台被淹
"""
import argparse
import re
import socket
import time


class Bridge:
    def __init__(self, port, timeout=10):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        self.drain()

    def drain(self):
        self.s.settimeout(0.2)
        try:
            while self.s.recv(65536):
                pass
        except Exception:
            pass

    def run(self, cmd, wait=3.0):
        self.drain()
        self.s.sendall(cmd.encode() + b"\n")
        end = time.time() + wait
        buf = b""
        self.s.settimeout(0.4)
        while time.time() < end:
            try:
                d = self.s.recv(65536)
                if not d:
                    break
                buf += d
            except socket.timeout:
                continue
        return buf.decode(errors="replace")

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


def show(title, text, tail=None):
    print("\n" + "=" * 18 + " " + title + " " + "=" * 18)
    body = text if tail is None else text[-tail:]
    print(body.strip())


def pids_of(bridge, name):
    out = bridge.run("pidin ar | grep -i %s | grep -v grep" % name, wait=4)
    pids = []
    for line in out.splitlines():
        m = re.match(r"\s*(\d+)\s", line)
        if m and name.lower() in line.lower():
            pids.append(m.group(1))
    return pids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bridge-port", type=int, default=47001)
    ap.add_argument("--deploy-dir", required=True, help="测试程序所在目录，如 /var/log/test")
    ap.add_argument("--app", required=True, help="测试程序名，如 clusterHmiMin")
    ap.add_argument("--config", default="", help="启动参数 -config= 指向的文件；留空则不带")
    ap.add_argument("--lib-dir", default="", help="剖析引擎库目录；默认 <deploy-dir>/kzprof")
    ap.add_argument("--env", default="", help="额外环境变量，如 HMI_RES_PROFILING=1（多个用空格分隔）")
    ap.add_argument("--default-app", default="", help="默认(量产)程序名，配合 --stop-default")
    ap.add_argument("--stop-default", action="store_true", help="先停掉默认程序")
    ap.add_argument("--console-port", type=int, default=56000)
    ap.add_argument("--log-name", default="", help="运行日志文件名；默认 <app>.run.log")
    ap.add_argument("--boot-wait", type=float, default=15.0, help="启动后等待秒数，默认 15")
    a = ap.parse_args()

    deploy = a.deploy_dir.rstrip("/")
    libdir = (a.lib_dir or (deploy + "/kzprof")).rstrip("/")
    logname = a.log_name or ("%s.run.log" % a.app)
    logpath = "%s/%s" % (deploy, logname)

    b = Bridge(a.bridge_port)

    # --- 1. 停默认(量产)程序 ---
    if a.stop_default:
        if not a.default_app:
            raise SystemExit("--stop-default 需要同时给 --default-app")
        old = pids_of(b, a.default_app)
        if old:
            show("stop default", b.run("sysmgrtool stop %s" % a.default_app, wait=5), 800)
            time.sleep(2)
            old = pids_of(b, a.default_app)
        print("\n默认程序 %s 残留 PID: %s" % (a.default_app, old or "无"))
    else:
        print("\n(跳过停默认程序；如遇抢屏/抢 GPU，加 --stop-default --default-app <名字>)")

    # --- 2. 清残留测试实例 ---
    resid = pids_of(b, a.app)
    if resid:
        print("发现残留测试实例 PID=%s，先杀掉" % resid)
        for p in resid:
            b.run("kill %s" % p, wait=2)
        time.sleep(2)
        resid = pids_of(b, a.app)
        if resid:
            raise SystemExit("残留实例杀不掉（PID=%s），停止。不要同时跑两个实例。" % resid)
    print("残留测试实例: 无")

    # --- 3. chmod + 就位检查 ---
    show("chmod", b.run("chmod a+x %s/%s %s/libpluginmonitor.so" % (deploy, a.app, deploy), wait=4), 600)
    show("files", b.run("ls -l %s/%s %s/libpluginmonitor.so" % (deploy, a.app, deploy), wait=4), 1500)

    # --- 4. 启动 ---
    envpart = ("%s " % a.env.strip()) if a.env.strip() else ""
    cfgpart = ("-config=%s " % a.config) if a.config else ""
    cmd = ("cd %s && %sLD_LIBRARY_PATH=%s:%s ./%s %s> %s 2>&1 &"
           % (deploy, envpart, libdir, deploy, a.app, cfgpart, logpath))
    show("launch", b.run(cmd, wait=5), 1200)
    print("\n[启动命令] " + cmd)

    print("\n等待 %.0f 秒..." % a.boot_wait)
    time.sleep(a.boot_wait)

    # --- 5. 验收 ---
    alive = pids_of(b, a.app)
    show("pidin", b.run("pidin ar | grep -i %s | grep -v grep" % a.app, wait=4), 2500)
    show("console %d" % a.console_port,
         b.run("netstat -an | grep %d" % a.console_port, wait=4), 2000)
    logtail = b.run("tail -n 30 %s" % logpath, wait=4)
    show("run.log tail", logtail, 4000)

    b.close()

    # --- 6. 结论 ---
    print("\n" + "=" * 18 + " 结论 " + "=" * 18)
    ok = True
    if not alive:
        print("[FAIL] 进程未存活")
        ok = False
    else:
        print("[ OK ] 进程存活 PID=%s" % alive)
    if "SIGSEGV" in logtail or "core dumped" in logtail:
        print("[FAIL] 日志出现 SIGSEGV / core dumped -> 检查 --lib-dir 与 LD_LIBRARY_PATH")
        ok = False
    if "error while loading shared libraries" in logtail:
        print("[FAIL] 动态库找不到 -> --lib-dir 写错")
        ok = False
    if "Listening for connections" in logtail:
        print("[ OK ] 日志出现 Listening for connections")
    if ok:
        print("\n>>> 启动判定通过。下一步：telnet 127.0.0.1 %d 进控制台做测试。" % a.console_port)
        return 0
    print("\n>>> 启动失败，看 run.log 尾部，不要反复重试。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
