# FSR V2 固件 v2（USB 串口 + BLE 双模）—— GPIO34 分压采样，100Hz
# 电路不变：3.3V —[FSR402]—●(GPIO34)—[330Ω]—GND（V2 正式拓扑，2026-10-02 预检通过）
# 有线模式（不变）：USB 115200，每行 "毫秒数,原始值"（0-4095，12 位 ADC）
# 无线模式：BLE GATT notify，同格式行；服务 = Nordic UART Service（NUS）TX，
#   广播名 "exo-fsr"，手机 nRF Connect / 上位机 bleak 均可直连。
#   吞吐：100Hz × ~13B ≈ 1.3KB/s（BLE 连接态余量充足，AI 依协议惯例设定，待实测；
#   若丢点改单次 notify 批 2-3 行）。

import bluetooth
import time
from machine import ADC, Pin

adc = ADC(Pin(34))            # GPIO34 = ADC1_CH6（仅输入，无上下拉，正合适）
adc.atten(ADC.ATTN_11DB)      # 量程扩到 ~3.3V 满量程
adc.width(ADC.WIDTH_12BIT)    # 0-4095

# ---- BLE ----
_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2

_NUS = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")     # Nordic UART Service
_TX = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")      # NUS TX（设备→主机）

NAME = b"exo-fsr"

ble = bluetooth.BLE()
ble.active(True)
try:
    ble.config(gap_name=NAME.decode())   # NimBLE 支持；失败也不影响（名字在广播里手动带）
except Exception:
    pass

conn = [-1]          # 当前连接句柄；-1 = 未连接
ble.irq(_irq)      # 2026-10-03 首刷遇漏：忘了挂 IRQ，连接后 conn 恒 -1、notify 一条不发

def _irq(ev, data):
    if ev == _IRQ_CENTRAL_CONNECT:
        conn[0] = data[0]
    elif ev == _IRQ_CENTRAL_DISCONNECT:
        conn[0] = -1
        _advertise()                     # 断开后恢复广播，等主机重连

((tx_handle,),) = ble.gatts_register_services(
    ((_NUS, ((_TX, bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY),)),)
)

def _advertise():
    # 广播包：FLAGS(general discoverable) + 完整本地名，共 13B < 31B 上限
    payload = bytes([0x02, 0x01, 0x06, len(NAME) + 1, 0x09]) + NAME
    ble.gap_advertise(100_000, adv_data=payload)   # 100ms 间隔

_advertise()

# ---- 采样主循环（USB/BLE 双发）----
t0 = time.ticks_ms()
while True:
    ms = time.ticks_diff(time.ticks_ms(), t0)
    line = f"{ms},{adc.read()}"
    print(line)                            # 有线：USB 串口（115200，保持 V1 兼容）
    if conn[0] >= 0:                       # 无线：连接态才 notify
        try:
            ble.gatts_notify(conn[0], tx_handle, line.encode() + b"\n")
        except Exception:
            pass                           # 断连瞬间窗口，由 IRQ 收尾并恢复广播
    time.sleep_ms(10)                      # ~100Hz（报告 20260910 §9.1）
