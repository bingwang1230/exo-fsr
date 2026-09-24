#!/usr/bin/env python3
"""V2 拓扑A 原理图：330Ω 上臂（参考）+ FSR 下臂（被测），ADC 测中点对地 = FSR 电压。

用法：.venv/bin/python draw_v2_topology_a.py   （输出 web/v2_topology_a.png）
骨架照抄 draw_v1_schematic.py（原理图式）；区别=上下换位 + 10k→330。
标签策略：竖直元件锚点行为不稳（ResistorVar 翻车三连），正文标注一律 elm.Label 显式坐标。
"""

import matplotlib

matplotlib.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

import schemdraw
import schemdraw.elements as elm

with schemdraw.Drawing(file="web/v2_topology_a.png", dpi=130, show=False) as d:
    d.config(unit=2.4, fontsize=12, font="PingFang SC")

    # 电源：ESP32 当电池用（内部稳压器 5V→3.3V）
    d += (src := elm.SourceV().up().label("ESP32\n(内部稳压 5V→3.3V)", loc="left", ofst=0.3))
    d += elm.Line().up(0.8)
    d += (v33 := elm.Dot(open=True).label("3.3V 电源轨", loc="left"))

    # 330Ω 在上（参考臂）
    d += elm.Line().right(0.8).label("电流 →", loc="top")
    d += (r330 := elm.Resistor().right().label("330Ω 上臂（参考）\n压降 V₃₃₀ = 3.3V − V_FSR", loc="top"))

    # 中点：ADC 从这里看出去
    d += (mid := elm.Dot())

    # FSR 在下（被测臂）——本体不带标签，标注走显式坐标
    d += (fsr := elm.ResistorVar().down())

    # 回地
    d += elm.Line().left(0.8)
    d += (gnd := elm.Ground().label("GND 电源轨（0V 基准）→ ESP32 GND 脚", loc="bottom", ofst=(1.2, 0)))
    d += elm.Line().down(0.6).at(gnd.center)

    # 表笔：GPIO34 只看不流，测的=中点对地=FSR 两端电压
    d += elm.Line().right(d.unit * 1.5).at(mid.center)
    d += elm.Dot(open=True).label("GPIO34 (ADC) 电压表笔\n测「中点对地」= FSR 两端电压\n（不是 330 的）；空载≈4095\n压力↑ → 读数掉向 0", loc="right")

    # FSR 标注：显式坐标放在右下空白区（FSR 右侧、GPIO 表笔下方的三角地带）
    fx = mid.center[0]
    d += elm.Label().at((fx + 2.0, mid.center[1] - 1.15)).label(
        "FSR402 下臂（被测）", fontsize=12)
    d += elm.Label().at((fx + 2.35, mid.center[1] - 2.0)).label(
        "压力↑ → R_FSR↓ → V_FSR↓\n读数越压越低（反逻辑）", fontsize=11)
