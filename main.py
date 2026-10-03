# FSR V2.6 双脚版固件（USB 串口 + BLE 双模）—— 双通道分压采样，100Hz
# 电路：3.3V —[330Ω]—●(中点)—[FSR402]—GND ×2（V2.6 装配图，exo-fsr web/v2_6_dual_fsr.png）
# 左脚 → GPIO34（ADC1_CH6），右脚 → GPIO35（ADC1_CH7）
# 输出格式（115200 / BLE notify 同）：每行 "毫秒数,左脚,右脚"，各 0-4095（12 位 ADC）
# 反逻辑：空载 ≈4095，受压读数下掉。单行 ≤18B，默认 ATT MTU 23-3=20B 装得下；
#   批量打包（2行/包 33B）需 MTU 协商支持，暂不做（2026-10-03 拍板：先保可靠）。

import bluetooth
import time
from machine import ADC, Pin

adcL = ADC(Pin(34))           # 左脚
adcR = ADC(Pin(35))           # 右脚
for adc in (adcL, adcR):
    adc.atten(ADC.ATTN_11DB)  # 量程扩到 ~3.3V 满量程
    adc.width(ADC.WIDTH_12BIT)

# ---- BLE ----
_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2

_NUS = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")     # Nordic UART Service
_TX = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")      # NUS TX（设备→主机）

NAME = b"exo-fsr"

ble = bluetooth.BLE()
ble.active(True)
try:
    ble.config(gap_name=NAME.decode())
except Exception:
    pass

conn = [-1]          # 当前连接句柄；-1 = 未连接

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
    payload = bytes([0x02, 0x01, 0x06, len(NAME) + 1, 0x09]) + NAME
    ble.gap_advertise(100_000, adv_data=payload)   # 100ms 间隔

ble.irq(_irq)   # 挂载顺序坑：必须在 def 之后（见 learn ch03 双坑笔记）
_advertise()

# ---- 采样主循环（USB/BLE 双发）----
t0 = time.ticks_ms()
while True:
    ms = time.ticks_diff(time.ticks_ms(), t0)
    line = f"{ms},{adcL.read()},{adcR.read()}"
    print(line)                            # 有线：USB 串口（115200）
    if conn[0] >= 0:                       # 无线：连接态才 notify
        try:
            ble.gatts_notify(conn[0], tx_handle, line.encode() + b"\n")
        except Exception:
            pass                           # 断连瞬间窗口，由 IRQ 收尾并恢复广播
    time.sleep_ms(10)                      # ~100Hz（报告 20260910 §9.1）
