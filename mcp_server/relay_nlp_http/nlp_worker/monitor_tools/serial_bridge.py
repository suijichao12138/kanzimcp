# -*- coding: utf-8 -*-
"""COM3 <-> 127.0.0.1:47001 双向桥（长驻），方便多次调用复用同一串口会话。"""
import socket, sys, threading, time

import serial

COM = sys.argv[1] if len(sys.argv) > 1 else "COM3"
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 47001
LOG = sys.argv[4] if len(sys.argv) > 4 else "serial_raw.log"

ser = serial.Serial(COM, BAUD, timeout=0.05)
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", PORT))
srv.listen(4)
logf = open(LOG, "ab", buffering=0)
print("bridge: %s@%d <-> 127.0.0.1:%d" % (COM, BAUD, PORT), flush=True)


def pump_serial():
    while True:
        try:
            data = ser.read(4096)
        except Exception as e:
            print("serial read err:", e, flush=True)
            return
        if data:
            logf.write(data)
            with lock:
                for c in clients:
                    try:
                        c.sendall(data)
                    except Exception:
                        pass


lock = threading.Lock()
clients = []
threading.Thread(target=pump_serial, daemon=True).start()

while True:
    conn, addr = srv.accept()
    with lock:
        clients.append(conn)
    print("client connected", addr, flush=True)

    def handle(c=conn):
        while True:
            try:
                data = c.recv(4096)
            except Exception:
                break
            if not data:
                break
            ser.write(data)
            ser.flush()
        with lock:
            if c in clients:
                clients.remove(c)
        try:
            c.close()
        except Exception:
            pass
        print("client disconnected", flush=True)

    threading.Thread(target=handle, daemon=True).start()
