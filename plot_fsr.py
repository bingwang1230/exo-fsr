#!/usr/bin/env python3
"""FSR V1 实时曲线 —— 读 ESP32 串口（"毫秒,原始值"），matplotlib 实时画波形。

用法：python3 plot_fsr.py /dev/cu.usbserial-XXXX
依赖：pip install pyserial matplotlib
判据：手指按压 FSR，曲线实时起伏、松手回落 = 链路全通（V1 完成）。
"""

import sys
import collections

import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbserial-0001"
WINDOW = 500  # 曲线窗口：500 点 ≈ 5 秒 @100Hz

ser = serial.Serial(PORT, 115200, timeout=1)
xs = collections.deque(maxlen=WINDOW)
ys = collections.deque(maxlen=WINDOW)

fig, ax = plt.subplots(figsize=(10, 5))
(line,) = ax.plot([], [], lw=1.5, color="#d93025")
ax.set_xlabel("样本（~100Hz）")
ax.set_ylabel("ADC 原始值（0-4095，越大压力越大）")
ax.set_title(f"FSR 实时曲线 —— {PORT}")
ax.set_ylim(0, 4095)


def update(_):
    while True:
        raw = ser.readline().decode(errors="ignore").strip()
        if not raw:
            break
        try:
            _, val = raw.split(",")
            ys.append(int(val))
            xs.append(xs[-1] + 1 if xs else 0)
        except ValueError:
            pass  # 半行/噪声，丢掉
    line.set_data(xs, ys)
    if xs:
        ax.set_xlim(max(0, xs[-1] - WINDOW), xs[-1] + 10)
    return (line,)


ani = animation.FuncAnimation(fig, update, interval=50, blit=True, cache_frame_data=False)
plt.show()
