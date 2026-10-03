#!/usr/bin/env python3
"""V2.6 双脚版装配图——SYB-170 迷你面包板（双通道 330Ω 正式拓扑）。

拓扑（沿用 V2 正式版，×2）：330Ω 上臂接 3.3V，FSR 下臂接 GND，中点 → ADC。
左脚 → D34（黄），右脚 → D35（绿）；3V3 单脚引出、板上中列共享（两支 330Ω 同列堆叠）；
GND 用 ESP32 两只脚分别引（30Pin DevKit 有 ≥2 只 GND）。
SYB-170 上下两半（bank）互不导通——本图全部连接在上半区，底部走线走两 bank 之间的空隙与板外，不压任何孔。

设计要点：单 ESP32 双通道 = 双脚时间戳同源（重心转移=双脚时间差，免费同步）。
导线配色：红=3V3，黄=D34 左脚中点，绿=D35 右脚中点，深蓝=GND（图例见图底部）。
"""

import matplotlib

matplotlib.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

import schemdraw
import schemdraw.elements as elm

RED = "#d40000"
YEL = "#d4a017"
GRN = "#1e8f4e"
BLU = "#1a1a8c"
GRID = "#b8b8b8"
RAIL = "#8a8a8a"

with schemdraw.Drawing(file="web/v2_6_dual_fsr.png", dpi=130, show=False) as d:
    d.config(unit=2.4, fontsize=12, font="PingFang SC")

    # ---- SYB-170 板框与孔阵（上半区 bank A：5 行 × 17 列；下半区 bank B 仅示意，不用）----
    x0, pitch, cols = 4.7, 0.55, 17
    xs = [x0 + pitch * i for i in range(cols)]
    rowsA = [7.7, 7.15, 6.6, 6.05, 5.5]
    rowsB = [4.5, 3.95, 3.4, 2.85, 2.3]

    for (xa, ya, xb, yb) in [(4.4, 2.0, 13.8, 2.0), (4.4, 7.95, 13.8, 7.95),
                             (4.4, 2.0, 4.4, 7.95), (13.8, 2.0, 13.8, 7.95)]:
        d += elm.Line().at((xa, ya)).to((xb, yb)).color("#999")
    d += elm.Label().at((9.1, 1.55)).label("SYB-170 迷你面包板（俯视，全部用上半区）", fontsize=11)

    for r in rowsA + rowsB:
        for x in xs:
            d += elm.Dot(radius=0.045).at((x, r)).color(GRID)

    # ---- 用到的五列：列内竖向导通示意（细灰线）----
    cG_L, cM_L, cV3, cM_R, cG_R = xs[2], xs[4], xs[7], xs[10], xs[12]
    for cx, ybot in [(cG_L, 5.5), (cM_L, 5.5), (cV3, 6.05), (cM_R, 5.5), (cG_R, 5.5)]:
        d += elm.Line().at((cx, 7.7)).to((cx, ybot)).color(RAIL)

    # ---- ESP32 方框（左侧；3V3 从顶部引出，四只脚从右侧）----
    for (xa, ya, xb, yb) in [(0.7, 2.6, 3.5, 2.6), (0.7, 5.4, 3.5, 5.4),
                             (0.7, 2.6, 0.7, 5.4), (3.5, 2.6, 3.5, 5.4)]:
        d += elm.Line().at((xa, ya)).to((xb, yb))
    d += elm.Label().at((2.1, 4.0)).label("ESP32\nDevKit", fontsize=13)

    d += elm.Line().at((2.1, 5.4)).to((2.1, 6.0))            # 3V3 顶部引脚
    d += elm.Label().at((2.8, 6.0)).label("3V3", fontsize=11)
    y34, y35, yG1, yG2 = 4.9, 4.4, 3.9, 3.4
    for y, name in [(y34, "D34"), (y35, "D35"), (yG1, "GND①"), (yG2, "GND②")]:
        d += elm.Line().at((3.5, y)).to((4.0, y))
        d += elm.Label().at((3.78, y + 0.27)).label(name, fontsize=11)

    # ---- 红 3V3：中列顶行 → 板上方 → ESP32 顶部（全程不穿板面孔阵）----
    d += elm.Line().at((cV3, 7.7)).toy(10.4).color(RED)
    d += elm.Line().at((cV3, 10.4)).tox(2.1).color(RED)
    d += elm.Line().at((2.1, 10.4)).toy(6.0).color(RED)
    d += elm.Dot().at((cV3, 7.7))
    d += elm.Label().at((9.7, 10.65)).label("红 · 3V3（中列共享）", fontsize=11)

    # ---- 黄 D34（左脚中点）：中列底行 → 两 bank 空隙 → ESP32 ----
    d += elm.Line().at((cM_L, 5.5)).toy(5.2).color(YEL)
    d += elm.Line().at((cM_L, 5.2)).tox(3.6).color(YEL)
    d += elm.Line().at((3.6, 5.2)).toy(y34).color(YEL)
    d += elm.Line().at((3.6, y34)).tox(4.0).color(YEL)
    d += elm.Dot().at((cM_L, 5.5))

    # ---- 绿 D35（右脚中点）：右中列底行 → 空隙 → ESP32 ----
    d += elm.Line().at((cM_R, 5.5)).toy(4.7).color(GRN)
    d += elm.Line().at((cM_R, 4.7)).tox(3.6).color(GRN)
    d += elm.Line().at((3.6, 4.7)).toy(y35).color(GRN)
    d += elm.Line().at((3.6, y35)).tox(4.0).color(GRN)
    d += elm.Dot().at((cM_R, 5.5))

    # ---- 深蓝 GND①：左 GND 列 → 空隙 → 板左侧下行 → ESP32 ----
    d += elm.Line().at((cG_L, 5.5)).toy(4.95).color(BLU)
    d += elm.Line().at((cG_L, 4.95)).tox(4.1).color(BLU)
    d += elm.Line().at((4.1, 4.95)).toy(yG1).color(BLU)
    d += elm.Line().at((4.1, yG1)).tox(4.0).color(BLU)
    d += elm.Dot().at((cG_L, 5.5))

    # ---- 深蓝 GND②：右 GND 列 → 绕板右侧 → 板下方 → ESP32（不压下半区孔）----
    d += elm.Line().at((cG_R, 5.5)).toy(4.8).color(BLU)
    d += elm.Line().at((cG_R, 4.8)).tox(14.2).color(BLU)
    d += elm.Line().at((14.2, 4.8)).toy(1.2).color(BLU)
    d += elm.Line().at((14.2, 1.2)).tox(3.8).color(BLU)
    d += elm.Line().at((3.8, 1.2)).toy(yG2).color(BLU)
    d += elm.Line().at((3.8, yG2)).tox(4.0).color(BLU)
    d += elm.Dot().at((cG_R, 5.5))

    # ---- 立链元件：两支 330Ω（中列堆叠共享 3V3）+ 两片 FSR（板上方直插顶行）----
    d += elm.Resistor().endpoints((cM_L, 6.6), (cV3, 6.6))
    d += elm.Resistor().endpoints((cV3, 6.05), (cM_R, 6.05))
    for px, py in [(cV3, 6.6), (cV3, 6.05), (cM_L, 6.6), (cM_R, 6.05)]:
        d += elm.Dot().at((px, py))
    d += elm.Label().at(((cM_L + cV3) / 2, 7.0)).label("330Ω-L", fontsize=11)
    d += elm.Label().at(((cV3 + cM_R) / 2, 5.72)).label("330Ω-R", fontsize=11)

    d += elm.ResistorVar().endpoints((cG_L, 9.3), (cM_L, 9.3))
    d += elm.Line().at((cG_L, 9.3)).toy(7.7)
    d += elm.Line().at((cM_L, 9.3)).toy(7.7)
    d += elm.Dot().at((cG_L, 7.7))
    d += elm.Dot().at((cM_L, 7.7))
    d += elm.Label().at(((cG_L + cM_L) / 2, 9.85)).label("FSR-L 左脚\n（第一跖骨头位）", fontsize=11)

    d += elm.ResistorVar().endpoints((cM_R, 9.3), (cG_R, 9.3))
    d += elm.Line().at((cM_R, 9.3)).toy(7.7)
    d += elm.Line().at((cG_R, 9.3)).toy(7.7)
    d += elm.Dot().at((cM_R, 7.7))
    d += elm.Dot().at((cG_R, 7.7))
    d += elm.Label().at(((cM_R + cG_R) / 2, 9.85)).label("FSR-R 右脚\n（镜像位）", fontsize=11)

    # ---- 标题 / 图例 / 三查 ----
    d += elm.Label().at((7.5, 11.6)).label(
        "V2.6 双脚版装配图 · 双通道分压（330Ω 上臂 / FSR 下臂，D34 左脚 · D35 右脚）", fontsize=14)
    d += elm.Label().at((0.7, 0.55)).label(
        "图例：红=3V3　黄=D34 左脚中点　绿=D35 右脚中点　深蓝=GND（用 ESP32 两只 GND 脚）｜"
        "同列才导通；上下两半互不导通", fontsize=11)
    d += elm.Label().at((0.5, -0.5)).label(
        "三查：① 红 3V3 + 两支 330Ω 各一脚 同列（中列堆叠）；每片中点列 = 330Ω 另一脚 + FSR 一脚 + 黄/绿线；"
        "每片 GND 列 = FSR 另一脚 + 深色线——全部插上半区", fontsize=11)
    d += elm.Label().at((0.5, -1.25)).label(
        "② 上电预期（板载直插预检）：两片空载都稳 ≈4095；指压哪片哪路下掉（反逻辑）；"
        "任一路 0–4095 乱跳 = 该路中点悬空，重插该路黄/绿线", fontsize=11)
    d += elm.Label().at((0.5, -2.0)).label(
        "③ 上鞋：每片 FSR 两脚各接 1m 杜邦延长（中点色线 + GND 深色线，共 4 根）；FSR 贴鞋垫下第一跖骨头位（大脚趾根圆球正下）；"
        "板贴充电宝收脚踝/口袋——单板双通道=双脚时间戳同源，重心转移可直接算", fontsize=11)
