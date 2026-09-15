#!/usr/bin/env python3
"""V1 分压电路原理图（schemdraw 渲染）—— L3 裸重演修正版参照图。

用法：.venv/bin/python draw_v1_schematic.py   （输出 web/v1_schematic.png）
设计：ESP32 既是电源（左）也是电压表（右表笔）；FSR 上、10k 下（与面包板实物一致）。
"""

import matplotlib

matplotlib.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

import schemdraw
import schemdraw.elements as elm

with schemdraw.Drawing(file="web/v1_schematic.png", dpi=130, show=False) as d:
    d.config(unit=2.4, fontsize=12, font="PingFang SC")

    # 电源：ESP32 当电池用（内部稳压器 5V→3.3V）
    d += (src := elm.SourceV().up().label("ESP32\n(内部稳压 5V→3.3V)", loc="left", ofst=0.3))
    d += elm.Line().up(0.8)
    d += (v33 := elm.Dot(open=True).label("3.3V 电源轨", loc="left"))

    # FSR 在上（接 3.3V 端）
    d += elm.Line().right(0.8).label("电流 →", loc="top")
    d += (fsr := elm.ResistorVar().right().label("FSR402\n压力↑→接触↑→电阻↓\n(10MΩ→2kΩ)", loc="top"))

    # 中点
    d += (mid := elm.Dot())
    d += elm.Resistor().down().label("10kΩ\n(1%)", loc="bottom")

    # 回地
    d += elm.Line().left(0.8)
    d += (gnd := elm.Ground().label("GND 电源轨（0V 基准）→ ESP32 GND 脚", loc="bottom", ofst=(1.2,0)))
    d += elm.Line().down(0.6).at(gnd.center)

    # 表笔：GPIO34 只看不流
    d += elm.Line().right(d.unit * 1.5).at(mid.center)
    d += elm.Dot(open=True).label("GPIO34 (ADC)\n电压表笔：只看不流\n读数 0–4095", loc="right")

