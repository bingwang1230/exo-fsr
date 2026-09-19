#!/usr/bin/env python3
"""FSR 标定服务 —— V1 接线下单片标定用（读串口 + 实时曲线 + 稳态读数接口）。

一个进程替代 plot_fsr_web.py + http.server：
  /          实时曲线页（JS 300ms 拉图 + 稳态中位数大字显示）
  /curve.png 最新波形（250ms 重画）
  /snap?s=3  最近 s 秒稳态统计 JSON：median/mean/min/max/n（标定取数用）
  /data.csv  本次会话完整数据转储（host 时间, 设备 ms, ADC）

用法：python3 calib_server.py [串口]（默认 /dev/cu.usbserial-110）
      打开 http://<MBP-IP>:8324/
依赖：pyserial matplotlib（exo-fsr/.venv 已装）
"""

import collections
import json
import os
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import serial

plt.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbserial-110"
HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
os.makedirs(WEB, exist_ok=True)

WINDOW = 500  # 波形窗口 ~5 秒
xs = collections.deque(maxlen=WINDOW)
ys = collections.deque(maxlen=WINDOW)
history = []  # 全量 (host_ts, dev_ms, adc)，标定会话转储用

ser = serial.Serial(PORT, 115200, timeout=1)


def reader():
    n = 0
    while True:
        raw = ser.readline().decode(errors="ignore").strip()
        try:
            ms, val = raw.split(",")
            adc = int(val)
            dev_ms = int(ms)
            xs.append(n)
            ys.append(adc)
            history.append((time.time(), dev_ms, adc))
            n += 1
        except ValueError:
            pass


threading.Thread(target=reader, daemon=True).start()


def snap(seconds=3):
    """最近 seconds 秒（按设备时钟）样本的稳态统计。"""
    if not history:
        return {"n": 0}
    last_ms = history[-1][1]
    vals = [adc for _, ms, adc in history if last_ms - ms <= seconds * 1000]
    if not vals:
        return {"n": 0}
    return {
        "window_s": seconds,
        "n": len(vals),
        "median": statistics.median(vals),
        "mean": round(statistics.mean(vals), 1),
        "min": min(vals),
        "max": max(vals),
    }


INDEX = """<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>FSR 标定台</title></head>
<body style='margin:0;background:#111;color:#eee;font-family:sans-serif'>
<h3 style='margin:12px 16px'>FSR 标定台 · 稳态读数（3 秒中位数）</h3>
<div id='big' style='font-size:64px;margin:8px 16px;font-weight:700'>--</div>
<div id='stat' style='margin:0 16px;font-size:18px;color:#8f8'> </div>
<img id='c' src='curve.png' style='width:96vw'>
<script>
setInterval(function(){
  var i=document.getElementById('c');
  i.src='curve.png?t='+Date.now();
  fetch('snap?s=3').then(r=>r.json()).then(j=>{
    if(j.n>0){
      document.getElementById('big').textContent=j.median;
      document.getElementById('stat').textContent=
        'n='+j.n+'  mean='+j.mean+'  min='+j.min+'  max='+j.max;
    }
  });
},500);
</script>
</body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            body = INDEX.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif u.path == "/snap":
            q = parse_qs(u.query)
            s = float(q.get("s", ["3"])[0])
            body = json.dumps(snap(s)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif u.path == "/data.csv":
            lines = ["host_ts,dev_ms,adc"] + [
                f"{t:.3f},{m},{a}" for t, m, a in history
            ]
            body = "\n".join(lines).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
        elif u.path == "/curve.png":
            try:
                body = open(os.path.join(WEB, "curve.png"), "rb").read()
            except FileNotFoundError:
                body = b""
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
        else:
            self.send_response(404)
            return
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def render_loop():
    fig, ax = plt.subplots(figsize=(10, 5), facecolor="#222")
    while True:
        time.sleep(0.25)
        ax.clear()
        ax.plot(list(xs), list(ys), lw=1.5, color="#ff5252")
        ax.set_facecolor("#222")
        ax.tick_params(colors="#ccc")
        for s in ax.spines.values():
            s.set_color("#555")
        ax.set_xlabel("样本（~100Hz）", color="#ccc")
        ax.set_ylabel("ADC 原始值（0–4095，越大压力越大）", color="#ccc")
        ax.set_ylim(0, 4095)
        ax.set_title(f"窗口 ≈ 5 秒 · {PORT} · 会话起点 " +
                     datetime.now(timezone.utc).astimezone().strftime("%H:%M:%S"), color="#eee")
        if xs:
            ax.set_xlim(max(0, xs[-1] - WINDOW), xs[-1] + 10)
        fig.savefig(os.path.join(WEB, "curve.png"), facecolor="#222", dpi=90)


threading.Thread(target=render_loop, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 8324), H).serve_forever()
