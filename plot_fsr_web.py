#!/usr/bin/env python3
"""FSR 实时曲线 · 浏览器版 —— 读串口画 PNG，浏览器自动刷新看波形。

用法：python3 plot_fsr_web.py [串口]（默认 /dev/cu.usbserial-110）
看图：浏览器打开 http://localhost:8324/
依赖：pyserial matplotlib（本 venv 已装）
"""

import collections
import os
import threading
import time

import matplotlib

matplotlib.use("Agg")  # 无窗口后端，避开 macOS GUI 各种坑
import matplotlib.pyplot as plt
import serial

plt.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

PORT = sys.argv[1] if (sys := __import__("sys")).argv[1:] else "/dev/cu.usbserial-110"
HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
os.makedirs(WEB, exist_ok=True)

WINDOW = 500  # 500 点 ≈ 5 秒
xs = collections.deque(maxlen=WINDOW)
ys = collections.deque(maxlen=WINDOW)

ser = serial.Serial(PORT, 115200, timeout=1)


def reader():
    """后台线程：不停读串口，攒数据。"""
    n = 0
    while True:
        raw = ser.readline().decode(errors="ignore").strip()
        try:
            _, val = raw.split(",")
            ys.append(int(val))
            xs.append(n)
            n += 1
        except ValueError:
            pass


threading.Thread(target=reader, daemon=True).start()

# 页面：JS 快速拉图（300ms）+ 防缓存（避免 meta refresh 整页刷新 + 图片缓存的 1.5–2s 感知延迟）
with open(os.path.join(WEB, "index.html"), "w") as f:
    f.write(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>FSR 实时曲线</title></head>"
        "<body style='margin:0;background:#111;color:#eee;font-family:sans-serif'>"
        "<h3 style='margin:12px 16px'>FSR 实时曲线 · 按压传感器看起伏</h3>"
        "<img id='c' src='curve.png' style='width:96vw'>"
        "<script>"
        "setInterval(function(){"
        "  var i=document.getElementById('c');"
        "  i.src='curve.png?t='+Date.now();"
        "},300);"
        "</script>"
        "</body></html>"
    )

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
    ax.set_ylabel("ADC 原始值（0-4095，越大压力越大）", color="#ccc")
    ax.set_ylim(0, 4095)
    ax.set_title(f"窗口 ≈ 5 秒 · {PORT}", color="#eee")
    if xs:
        ax.set_xlim(max(0, xs[-1] - WINDOW), xs[-1] + 10)
    fig.savefig(os.path.join(WEB, "curve.png"), facecolor="#222", dpi=90)
