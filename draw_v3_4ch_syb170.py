#!/usr/bin/env python3
"""V3 前哨 · 4 通道 FSR 装配图——SYB-170 迷你面包板（330Ω 正式拓扑 ×4）。

沿用 V2/V2.6 拍板拓扑：330Ω 上臂接 3.3V，FSR 下臂接 GND，中点 → ADC 引脚（反逻辑：空载≈4095）。
通道映射（续 V2.6：D34/D35 仍是左/右第一跖骨，双脚数据可直接对比）：
  D32=左脚跟（ADC1_CH4）  D33=右脚跟（ADC1_CH5）  D34=左跖（CH6）  D35=右跖（CH7）
  ——四脚同在 DevKit 同一边缘相邻排布，且全属 ADC1（WiFi 共存不失效），避开 strapping 五脚。
SYB-170 无长电源轨、上下两半（bank）互不导通——全部插上半区；3V3 用新杜邦线菊花链分发。
导线配色（仅为本图辨识用）：红=3V3，黄=各中点→ADC，深蓝=GND（验收目标色）。
"""

import matplotlib

matplotlib.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

import schemdraw
import schemdraw.elements as elm

RED = "#d40000"
YEL = "#d4a017"
BLU = "#1a1a8c"
GRID = "#b8b8b8"
RAIL = "#8a8a8a"

with schemdraw.Drawing(file="web/v3_4ch_syb170.png", dpi=130, show=False) as d:
    d.config(unit=2.4, fontsize=12, font="PingFang SC")

    # ---- SYB-170 板框与孔阵（上半区 bank A：5 行 × 17 列全部用上；下半区仅示意） ----
    x0, pitch, cols = 4.7, 0.55, 17
    xs = [x0 + pitch * i for i in range(cols)]
    rowsA = [7.7, 7.15, 6.6, 6.05, 5.5]
    rowsB = [4.5, 3.95, 3.4, 2.85, 2.3]

    for (xa, ya, xb, yb) in [(4.4, 2.0, 13.8, 2.0), (4.4, 7.95, 13.8, 7.95),
                             (4.4, 2.0, 4.4, 7.95), (13.8, 2.0, 13.8, 7.95)]:
        d += elm.Line().at((xa, ya)).to((xb, yb)).color("#999")
    d += elm.Label().at((9.1, 1.5)).label("SYB-170 迷你面包板（俯视）", fontsize=11)

    for r in rowsA + rowsB:
        for x in xs:
            d += elm.Dot(radius=0.045).at((x, r)).color(GRID)

    # ---- 列分配：每通道一对（3V3 列, 中点列），GND 全板共用最右列 ----
    #  通道1 D32 左跟: 3V3=xs[0], 中点=xs[2] | 通道2 D33 右跟: xs[3], xs[5]
    #  通道3 D34 左跖: xs[6], xs[8]          | 通道4 D35 右跖: xs[9], xs[11] | GND=xs[16]
    c3v = [xs[0], xs[3], xs[6], xs[9]]
    cm = [xs[2], xs[5], xs[8], xs[11]]
    cG = xs[16]
    for cx, ytop, ybot in [(c3v[0], 7.15, 5.5), (c3v[1], 7.15, 5.5),
                           (c3v[2], 7.15, 5.5), (c3v[3], 7.15, 5.5),
                           (cm[0], 7.7, 6.05), (cm[1], 7.7, 6.05),
                           (cm[2], 7.7, 6.05), (cm[3], 7.7, 6.05),
                           (cG, 7.7, 6.6)]:
        d += elm.Line().at((cx, ytop)).to((cx, ybot)).color(RAIL)

    # ---- ESP32 方框（左侧，五根中点线 + 电源地共 6 个引脚柱） ----
    for (xa, ya, xb, yb) in [(0.7, 2.8, 3.5, 2.8), (0.7, 5.9, 3.5, 5.9),
                             (0.7, 2.8, 0.7, 5.9), (3.5, 2.8, 3.5, 5.9)]:
        d += elm.Line().at((xa, ya)).to((xb, yb))
    d += elm.Label().at((2.1, 4.35)).label("ESP32\nDevKit", fontsize=13)

    y3v3 = 5.6
    # 引脚柱按用户实物丝印方向排（从下往上读）：D33, D32, D35, D34；3V3/GND 实板在别处，认丝印
    stubs = [(5.2, "D33"), (4.8, "D32"), (4.4, "D35"), (4.0, "D34"), (3.2, "GND")]
    for y, name in [(y3v3, "3V3")] + stubs:
        d += elm.Line().at((3.5, y)).to((4.0, y))
        d += elm.Label().at((3.95, y + 0.26)).label(name, fontsize=11)

    # ---- 3V3 红线：ESP32 → 首列上行，菊花链横线走 6.6 行（在黄线出口 6.05 上方，黄线向下走，零交叉） ----
    d += elm.Line().at((4.0, y3v3)).tox(c3v[0]).color(RED)
    d += elm.Line().at((c3v[0], y3v3)).toy(7.15).color(RED)
    d += elm.Dot().at((c3v[0], 6.6))
    d += elm.Dot().at((c3v[0], 7.15))
    for i in range(1, 4):
        d += elm.Line().at((c3v[i - 1], 6.6)).tox(c3v[i]).color(RED)
        d += elm.Line().at((c3v[i], 6.6)).toy(7.15).color(RED)
        d += elm.Dot().at((c3v[i], 6.6))
        d += elm.Dot().at((c3v[i], 7.15))

    # ---- 中点黄线：四列各出一根，接到对应 ADC 引脚（最近列对最上脚，零交叉） ----
    # 列通道分配随实物引脚序：cm[0]→D33 右跟、cm[1]→D32 左跟、cm[2]→D35 右跖、cm[3]→D34 左跖（固件映射不变）
    ch = [(0, 5.2), (1, 4.8), (2, 4.4), (3, 4.0)]   # (中点列序号, 引脚柱 y)
    for i, y in ch:
        d += elm.Line().at((cm[i], 6.05)).toy(y).color(YEL)
        d += elm.Line().at((cm[i], y)).tox(4.0).color(YEL)
        d += elm.Dot().at((cm[i], 6.05))

    # ---- GND 深蓝线：ESP32 → 最右列（y=3.2 最低，横穿无阻挡） ----
    d += elm.Line().at((4.0, 3.2)).tox(cG).color(BLU)
    d += elm.Line().at((cG, 3.2)).toy(7.7).color(BLU)
    d += elm.Dot().at((cG, 7.7))

    # ---- 330Ω ×4：上半区 7.15 行，各跨 3V3 列 → 中点列（腿弯紧；阻值标在通道2 下方） ----
    for i in range(4):
        d += elm.Resistor().endpoints((c3v[i], 7.15), (cm[i], 7.15)).label(
            "330Ω" if i == 1 else "", loc="bottom", fontsize=11)
        d += elm.Dot().at((cm[i], 7.15))

    # ---- FSR ×4：板上方错层（左通道最高、右通道最低 → 与各通道中点竖线零交叉） ----
    # 左端（中点侧）插各通道中点列顶行；右端共 GND 列（竖线上四个节点圆点）
    fsr_y = [13.0, 11.6, 10.2, 8.8]   # 随列序：右跟最高 … 左跖最低（层距拉足，符号不压线）
    fsr_names = ["FSR 右跟（D33）", "FSR 左跟（D32）", "FSR 右跖（D35）", "FSR 左跖（D34）"]
    for i in range(4):
        d += elm.ResistorVar().endpoints((cm[i], fsr_y[i]), (cG, fsr_y[i])).label(
            fsr_names[i], loc="top", fontsize=11)
        d += elm.Line().at((cm[i], fsr_y[i])).toy(7.7)
        d += elm.Dot().at((cm[i], 7.7))
    d += elm.Line().at((cG, fsr_y[0])).toy(7.7).color("#444")
    for y in fsr_y:
        d += elm.Dot().at((cG, y))

    # ---- 线色图例（避开引脚标签区）与标题、三查 ----
    d += elm.Label().at((7.0, 1.0)).label(
        "红线 = 3V3 菊花链 ×4 ｜ 黄线 ×4 = 各中点 → D32/33/34/35 ｜ 深色线 = GND（全板共用最右列）",
        fontsize=10)
    d += elm.Label().at((7.0, 0.3)).label(
        "菊花链走线：中间列各插两根跳线，同列不同孔（如 6.6 行与 6.05 行）——同列即导通，一孔只插一头",
        fontsize=10)
    d += elm.Label().at((2.1, 6.6)).label("", fontsize=10)
    d += elm.Label().at((7.0, -0.4)).label(
        "引脚柱顺序 = 实物丝印反读方向（D33/D32/D35/D34）；3V3/GND 实板另侧，接线认丝印不认图位",
        fontsize=10)
    d += elm.Label().at((7.5, 14.9)).label(
        "V3 前哨 · 4 通道 FSR 装配图（330Ω 上臂 / FSR 下臂 ×4，反逻辑）", fontsize=14)
    d += elm.Label().at((0.5, -1.5)).label(
        "三查：① 每通道三件同列才算通——330Ω 一脚与红线同列（3V3 列），另一脚与黄线同列（中点列），"
        "FSR 两脚分别在中点列与最右 GND 列——全部插上半区（SYB-170 上下两半互不导通！）", fontsize=11)
    d += elm.Label().at((0.5, -2.25)).label(
        "② 预检（逐通道指压）：空载稳定 ≈4095、指压对应通道下掉且其余三路不动＝通道通过；"
        "四路互串＝查中点列是否与邻列短路", fontsize=11)
    d += elm.Label().at((0.5, -3.0)).label(
        "③ 明晚上鞋：FSR 移到鞋内（左/右脚 · 跖骨头/脚跟四点），中点侧与 GND 侧各换 1m 杜邦延长；"
        "自热观察点照旧——静止站立 2-3 分钟看读数有无单向漂移", fontsize=11)
