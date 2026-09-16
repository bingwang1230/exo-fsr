#!/usr/bin/env python3
"""ESP32 30Pin DevKit 引脚地图（按功能着色）。

用法：.venv/bin/python draw_esp32_pinout.py   （输出 web/esp32_pinout.png）

颜色约定：
  红=电源  黑=GND  灰=系统/占用  橙=ADC  绿=I2C  蓝=SPI  紫=UART  墨绿=通用数字
  标注 ※ = 上电敏感（strapping），外设慎用
"""

import matplotlib

matplotlib.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

import schemdraw
import schemdraw.elements as elm

# (丝印, GPIO号, 功能标注, 颜色)
LEFT = [
    ("EN",  "EN",  "复位(板载RST)", "gray"),
    ("VP",  "36",  "ADC1·只读", "darkorange"),
    ("VN",  "39",  "ADC1·只读", "darkorange"),
    ("D34", "34",  "ADC1·只读 ←FSR", "darkorange"),
    ("D35", "35",  "ADC1·只读 ←FSR2候选", "darkorange"),
    ("D32", "32",  "ADC1·双向", "orange"),
    ("D33", "33",  "ADC1·双向", "orange"),
    ("D25", "25",  "DAC/双向 ※", "goldenrod"),
    ("D26", "26",  "DAC/双向 ※", "goldenrod"),
    ("D27", "27",  "ADC2/双向 ※", "olive"),
    ("D14", "14",  "ADC2/双向 ※", "olive"),
    ("D12", "12",  "双向 ※!最毒", "firebrick"),
    ("D13", "13",  "ADC2/双向 ※", "olive"),
    ("GND", "",    "0V", "black"),
    ("VIN", "",    "5V输入", "crimson"),
]

RIGHT = [
    ("D23", "23",  "SPI(MOSI)", "royalblue"),
    ("D22", "22",  "I2C(SCL) 留给IMU", "mediumseagreen"),
    ("TX0", "1",   "串口0·烧录占用!", "gray"),
    ("RX0", "3",   "串口0·烧录占用!", "gray"),
    ("D21", "21",  "I2C(SDA) 留给IMU", "mediumseagreen"),
    ("D19", "19",  "SPI(MISO)", "royalblue"),
    ("D18", "18",  "SPI(SCK)", "royalblue"),
    ("D5",  "5",   "SPI(CS) ※", "royalblue"),
    ("TX2", "17",  "串口2·空闲", "mediumpurple"),
    ("RX2", "16",  "串口2·空闲", "mediumpurple"),
    ("D4",  "4",   "ADC2/双向 ※", "olive"),
    ("D2",  "2",   "板载LED ※", "olive"),
    ("D15", "15",  "ADC2/双向 ※", "olive"),
    ("GND", "",    "0V", "black"),
    ("3V3", "",    "3.3V输出", "crimson"),
]

def mk(side, lst):
    # schemdraw Ic 的 L/R 侧引脚自底向上排布，反转列表使首脚（EN/D23）落在顶部，与实物一致
    return [elm.IcPin(name=f"{n}\n[{t}]" if t else n, pin=p or n,
                      side=side, color=c, lblsize=9, pinlblsize=8)
            for (n, p, t, c) in reversed(lst)]

with schemdraw.Drawing(file="web/esp32_pinout.png", dpi=150, show=False) as d:
    d.config(font="PingFang SC", fontsize=11)
    d += elm.Ic(pins=mk("L", LEFT) + mk("R", RIGHT),
                size=(5.5, 12), label="ESP32\n30Pin", lblsize=13, labelcolor="steelblue")

with schemdraw.Drawing(file="web/esp32_pinout_legend.png", dpi=150, show=False) as d:
    d.config(font="PingFang SC", fontsize=10)
    legend = [
        ("电源", "crimson"), ("GND", "black"), ("系统/烧录占用", "gray"),
        ("ADC1(随时可用)", "darkorange"), ("ADC1双向", "orange"),
        ("DAC+双向", "goldenrod"), ("ADC2(WiFi开则失效)", "olive"),
        ("SPI", "royalblue"), ("I2C", "mediumseagreen"), ("串口2空闲", "mediumpurple"),
    ]
    for i, (t, c) in enumerate(legend):
        d += elm.Line().right(0.5).color(c).linewidth(3).at((0, -i * 0.45))
        d += elm.Label().at((0.7, -i * 0.45)).label(t, loc="right")
    d += elm.Label().at((4.2, -0.2)).label("※ = 上电敏感(strapping)\n外设慎用；D12 最毒", loc="right")

print("done")
