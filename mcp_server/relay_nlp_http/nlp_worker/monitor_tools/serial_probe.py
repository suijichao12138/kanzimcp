# -*- coding: utf-8 -*-
"""枚举本机串口并逐个探测，找出真正连着目标板（QNX shell）的那个。

用法:
    python serial_probe.py                       # 枚举全部口，按 115200 -> 921600 -> 460800 试
    python serial_probe.py --baud 921600,115200  # 自定义波特率顺序
    python serial_probe.py --ports COM5,COM7     # 只试指定口
    python serial_probe.py --send "echo $OS"     # 命中后再发一条命令验证

判据（看回显特征）:
    含 '# ' / 'sh ' / 'QNX' / 登录提示  -> 命中目标板
    PermissionError(13)                -> 口被 Tera Term / PuTTY 占用，关掉再来
    无回显                             -> 换下一个波特率 / 下一个口
"""
import argparse
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    raise SystemExit("缺少 pyserial：pip install pyserial")

MARKERS = ("# ", "sh ", "QNX", "login:", "Password:", "$ ")


def enumerate_ports():
    ports = list(list_ports.comports())
    if not ports:
        print("!! 没有枚举到任何串口。检查：驱动是否安装 / 线是不是充电线 / 设备管理器")
        return []
    print("== 本机串口 ==")
    for p in ports:
        print("  %-8s | %-40s | %s" % (p.device, p.description, p.hwid))
    return [p.device for p in ports]


def probe(port, baud, send_cmd=None):
    """返回 (命中?, 说明, 回显文本)"""
    try:
        s = serial.Serial(port, baud, timeout=0.3)
    except Exception as e:
        msg = str(e)
        if "PermissionError" in msg or "拒绝访问" in msg or "Access is denied" in msg or "being used" in msg:
            return False, "被占用 — 关掉 Tera Term/PuTTY 等占用该口的工具再试", ""
        if "Cannot configure port" in msg or "参数错误" in msg:
            return False, "该口不支持波特率 %d" % baud, ""
        return False, "打开失败: %s" % msg, ""

    buf = b""
    try:
        s.reset_input_buffer()
        # 先静听，可能有启动输出
        time.sleep(0.6)
        buf += s.read(4096)
        s.write(b"\r\r\n")
        s.flush()
        time.sleep(1.2)
        buf += s.read(8192)
        if send_cmd:
            s.write(send_cmd.encode() + b"\n")
            s.flush()
            time.sleep(1.2)
            buf += s.read(8192)
    finally:
        s.close()

    text = buf.decode(errors="replace")
    for m in MARKERS:
        if m in text:
            return True, "命中标记 %r" % m, text
    if text.strip():
        return False, "有回显但无 shell 标记（可能是别的设备或波特率不对）", text
    return False, "无回显", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ports", default="", help="逗号分隔，如 COM5,COM7；默认枚举全部")
    ap.add_argument("--baud", default="115200,921600,460800", help="逗号分隔的波特率尝试顺序")
    ap.add_argument("--send", default=None, help="命中后再发一条命令，如 \"echo alive\"")
    a = ap.parse_args()

    if a.ports.strip():
        ports = [x.strip() for x in a.ports.split(",") if x.strip()]
        print("== 指定串口 ==\n  " + ", ".join(ports))
    else:
        ports = enumerate_ports()
        if not ports:
            return 1

    bauds = [int(x) for x in a.baud.split(",") if x.strip()]

    for port in ports:
        for baud in bauds:
            ok, why, text = probe(port, baud, a.send)
            tag = "HIT " if ok else "----"
            print("\n[%s] %s @ %d : %s" % (tag, port, baud, why))
            if text.strip():
                print("  echo: %r" % text[:300])
            if ok:
                print("\n>>> 目标串口 = %s  波特率 = %d" % (port, baud))
                return 0
            if "被占用" in why:
                break  # 换个波特率没用，直接下一个口
    print("\n>>> 没有任何口命中。排查顺序：换线 -> 确认板子上电 -> 确认波特率 -> 问用户")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
