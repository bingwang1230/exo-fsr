#!/usr/bin/env python3
"""同一电路的「布局式」画法 v2——对照 draw_v1_schematic.py（原理图式），证明两图等价。"""

import matplotlib

matplotlib.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

import schemdraw
import schemdraw.elements as elm

with schemdraw.Drawing(file="web/v1_schematic_layout.png", dpi=130, show=False) as d:
    d.config(unit=2.4, fontsize=12, font="PingFang SC")

    # 两条长轨（照实物画全长）
    d += elm.Line().at((0, 0)).to((10, 0)).label("GND 轨（0V）", loc="top")
    d += elm.Ground().at((0, 0))
    d += elm.Line().at((0, -5.5)).to((10, -5.5)).label("3.3V 轨", loc="bottom")

    # ESP32 方框
    esp = elm.Ic(pins=[
        elm.IcPin(name="GND", side="top"),
        elm.IcPin(name="3V3", side="bottom"),
        elm.IcPin(name="D34", side="right", slot="3/3"),
    ], edgepadW=1.0, edgepadH=0.6, label="ESP32").at((1.2, -3.0))
    d += esp

    # 3V3 → 下方 3.3V 轨（竖直短线 + 节点）
    d += elm.Line().at(esp.absanchors["3V3"]).toy(-5.5)
    d += elm.Dot()

    # GND → 上方 GND 轨
    d += elm.Line().at(esp.absanchors["GND"]).toy(0)
    d += elm.Dot()

    # D34 → 右行至中点 ●
    d += elm.Line().at(esp.absanchors["D34"]).tox(8).label("D34", loc="top")
    mid = (8, esp.absanchors["D34"][1])

    # 右侧立链：3.3V 轨 — FSR — ●(D34) — 10k — GND 轨
    # endpoints() 显式钉死两端坐标（.toy() 对 2 端子元件有渲染偏移，曾致 FSR 悬空）
    d += elm.ResistorVar().endpoints((8, -5.5), mid).label("FSR", loc="bottom")
    d += elm.Dot().at(mid)
    d += elm.Resistor().endpoints(mid, (8, -0.3)).label("10kΩ", loc="bottom")
    d += elm.Line().at((8, -0.3)).toy(0)
    d += elm.Dot()
