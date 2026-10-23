# FSR V3 前哨 4 通道固件（草稿 2026-10-05，待晚上会话拍板后刷入）—— USB ASCII + BLE 二进制帧双模
# 电路：3.3V —[330Ω]—●(中点)—[FSR402]—GND ×4（装配图 web/v3_4ch_syb170.png，330Ω 上臂/FSR 下臂，反逻辑）
# 通道映射（续 V2.6：D34/D35 仍是左/右第一跖骨，双脚数据可直接对比）：
#   左跟 → GPIO32（ADC1_CH4）  右跟 → GPIO33（ADC1_CH5）
#   左跖 → GPIO34（ADC1_CH6）  右跖 → GPIO35（ADC1_CH7）
# USB（115200）：每行 "毫秒数,左跟,左跖,右跟,右跖"（0-4095，12 位 ADC；左右各两通道相邻排，便于分析）
# BLE：二进制帧 b"\xAA" + struct.pack("<IHHHH", ms, 左跟, 左跖, 右跟, 右跖) + 校验和 1B = 14B ≤ 20B 默认 MTU。
#   校验和 = 12B 载荷算术和 & 0xFF——哨兵帧没有它时，线上的坏字节可能凑出「值域恰好合法」的假帧吞掉真帧
#   （fsr_live 解析器值域校验单闸不够，2026-10-05 单测抓到）；双闸 = 校验和 + 值域 ≤4095。
#   为什么不走 ASCII：4 通道 ASCII 行最长 28B 装不下默认 20B（V2.6 双通道 18B 是压线过的，10-03 拍板「先保可靠」）；
#   fsr_live v9 双格式自动兼容。
# 吞吐：100Hz × 13B ≈ 1.3KB/s，与 V2.6 同量级（BLE 连接态余量充足，AI 依协议惯例设定，待实测）。
# LED 秒闪（V3 新增，2026-10-23）：D16(RX2) ←220Ω← LED →GND，与数据同一 ms 时钟对齐——
#   每整秒亮 ~60ms（ms%1000<60），120fps 视频里≈7 帧，肉眼与逐帧都可见；
#   视频帧里 LED 亮 ⟺ 数据行 ms%1000<60，这就是时钟同步锚点（帖④对齐的前提）。
#   选脚 D16/D17（串口2·空闲，非 strapping）【AI 设定，待确认】；勿用 D12（最毒）与 21/22（留给 IMU）。

import bluetooth
import struct
import time
from machine import ADC, Pin

PINS = (32, 34, 33, 35)       # 发送顺序：左跟, 左跖, 右跟, 右跖（左右各自相邻）
adcs = []
for p in PINS:
    a = ADC(Pin(p))
    a.atten(ADC.ATTN_11DB)    # 量程扩到 ~3.3V 满量程
    a.width(ADC.WIDTH_12BIT)  # 0-4095
    adcs.append(a)

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

# ---- LED 秒闪标记（视频↔数据时钟对齐用）----
LED_PIN = 16            # D16/RX2，串口2空闲脚；换脚改这里（避开 D12/21/22/32/33/34/35）
LED_ON_MS = 60          # 每秒亮 60ms：占空比 6%，≈0.4mA 平均电流，电池无感
led = Pin(LED_PIN, Pin.OUT)

# ---- 采样主循环（USB ASCII / BLE 二进制帧 双发 + LED 秒闪）----
FRAME_HDR = 0xAA
OVERSAMPLE = 8    # 过采样：每点读 8 次平均，随机噪声 ÷√8，偶发 ADC 毛刺被稀释（2026-10-07）

def read_avg(a):
    s = 0
    for _ in range(OVERSAMPLE):
        s += a.read()
    return s >> 3                     # OVERSAMPLE=8 → 移位平均，比 //8 快

t0 = time.ticks_ms()
while True:
    ms = time.ticks_diff(time.ticks_ms(), t0)
    led.value(1 if ms % 1000 < LED_ON_MS else 0)   # 非阻塞秒闪：整秒亮 60ms，不占采样节奏
    v = [read_avg(a) for a in adcs]   # [左跟, 左跖, 右跟, 右跖]
    print(f"{ms},{v[0]},{v[1]},{v[2]},{v[3]}")     # 有线：USB 串口（ASCII 人读）
    if conn[0] >= 0:                       # 无线：连接态才 notify
        try:
            payload = struct.pack("<IHHHH", ms, *v)                       # 12B
            frame = bytes([FRAME_HDR]) + payload + bytes([sum(payload) & 0xFF])  # 14B ≤ 20B
            ble.gatts_notify(conn[0], tx_handle, frame)
        except Exception:
            pass                           # 断连瞬间窗口，由 IRQ 收尾并恢复广播
    time.sleep_ms(10)                      # ~100Hz（报告 20260910 §9.1）
