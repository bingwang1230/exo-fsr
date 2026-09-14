# FSR V1 桌面版固件 —— GPIO34 分压采样，100Hz，串口输出
# 电路：3.3V —[FSR402]—●(GPIO34)—[10kΩ]—GND
# 输出格式（115200 baud）：每行 "毫秒数,原始值"，原始值 0-4095（12 位 ADC）

import time
from machine import ADC, Pin

adc = ADC(Pin(34))            # GPIO34 = ADC1_CH6（仅输入，无上下拉，正合适）
adc.atten(ADC.ATTN_11DB)      # 量程扩到 ~3.3V 满量程
adc.width(ADC.WIDTH_12BIT)    # 0-4095

t0 = time.ticks_ms()
while True:
    ms = time.ticks_diff(time.ticks_ms(), t0)
    print(f"{ms},{adc.read()}")
    time.sleep_ms(10)         # ~100Hz：脚部动作几 Hz、上升沿几十 ms，够用（报告 20260910 §9.1）
