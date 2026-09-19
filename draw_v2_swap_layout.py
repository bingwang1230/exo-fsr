#!/usr/bin/env python3
"""V2 预演版「上下换位」布局图——10k 上臂接 3.3V，FSR 下臂接 GND。

与原 V1（draw_v1_layout_style.py）对照：FSR 与 10k 位置对调，中点 D34 不变。
语义反转：空载 FSR 电阻≈∞ → 中点被 10k 拉到 3.3V → ADC≈4095；
        受压 R 变小 → 中点下坠 → 读数往下掉。
"""

import matplotlib

matplotlib.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

import schemdraw
import schemdraw.elements as elm

with schemdraw.Drawing(file="web/v2_swap_layout.png", dpi=130, show=False) as d:
    d.config(unit=2.4, fontsize=12, font="PingFang SC")

    # 两条长轨（照实物：顶轨里行 GND / 顶轨外行 3.3V；图上仍画上下两条）
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

    d += elm.Line().at(esp.absanchors["3V3"]).toy(-5.5)
    d += elm.Dot()
    d += elm.Line().at(esp.absanchors["GND"]).toy(0)
    d += elm.Dot()

    # D34 → 右行至中点 ●
    d += elm.Line().at(esp.absanchors["D34"]).tox(8).label("D34（只看不流）", loc="top")
    mid = (8, esp.absanchors["D34"][1])

    # 换位后的右侧立链：3.3V 轨 — 10k — ●(D34) — FSR — GND 轨
    d += elm.Resistor().endpoints((8, -5.5), mid).label("10kΩ（上臂）", loc="bottom")
    d += elm.Dot().at(mid)
    d += elm.ResistorVar().endpoints(mid, (8, -0.3)).label("FSR（下臂）", loc="bottom")
    d += elm.Line().at((8, -0.3)).toy(0)
    d += elm.Dot()

    # 语义注释
    d += elm.Label().at((5.0, 1.0)).label(
        "空载：R_FSR≈∞ → 中点≈3.3V → 读数≈4095；  受压：R 变小 → 中点下坠 → 读数下掉（语义反转）",
        fontsize=11)
