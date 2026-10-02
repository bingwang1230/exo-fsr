#!/usr/bin/env python3
"""V2 桌面预检装配图——SYB-170 迷你面包板（330Ω 正式拓扑）。

正式版拓扑（09-19 拍板）：330Ω 上臂接 3.3V，FSR 下臂接 GND，中点 → D34。
SYB-170 无长电源轨、上下两半（bank）互不导通——三根跳线与 330、FSR 必须全插上半区。

导线配色（仅为本图辨识用，实际任取）：红=3V3，黄=D34 中点，深蓝=GND。
深蓝色专用于程序化连通性验收（泛洪 BFS 的目标色）。
"""

import matplotlib

matplotlib.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

import schemdraw
import schemdraw.elements as elm

RED = "#d40000"
YEL = "#d4a017"
BLU = "#1a1a8c"  # 近黑的深蓝：GND 线（验收目标色）
GRID = "#b8b8b8"
RAIL = "#8a8a8a"

with schemdraw.Drawing(file="web/v2_precheck_syb170.png", dpi=130, show=False) as d:
    d.config(unit=2.4, fontsize=12, font="PingFang SC")

    # ---- SYB-170 板框与孔阵（上半区 bank A：5 行 × 17 列；下半区 bank B 仅示意） ----
    x0, pitch, cols = 4.7, 0.55, 17
    xs = [x0 + pitch * i for i in range(cols)]
    rowsA = [7.7, 7.15, 6.6, 6.05, 5.5]   # 上半区（本图全部连接在此）
    rowsB = [4.5, 3.95, 3.4, 2.85, 2.3]   # 下半区（未用，示意）

    for (xa, ya, xb, yb) in [(4.4, 2.0, 13.8, 2.0), (4.4, 7.95, 13.8, 7.95),
                             (4.4, 2.0, 4.4, 7.95), (13.8, 2.0, 13.8, 7.95)]:
        d += elm.Line().at((xa, ya)).to((xb, yb)).color("#999")
    d += elm.Label().at((9.1, 1.5)).label("SYB-170 迷你面包板（俯视）", fontsize=11)

    for r in rowsA + rowsB:
        for x in xs:
            d += elm.Dot(radius=0.045).at((x, r)).color(GRID)

    # ---- 用到的三列：列内竖向导通示意（细灰线） ----
    cR, cM, cG = xs[2], xs[6], xs[10]  # 红=3V3 列，中点列，GND 列
    for cx, ytop, ybot in [(cR, 7.7, 6.05), (cM, 7.7, 5.5), (cG, 7.7, 5.5)]:
        d += elm.Line().at((cx, ytop)).to((cx, ybot)).color(RAIL)

    # ---- ESP32 方框（手动画，右侧三个引脚小柱） ----
    for (xa, ya, xb, yb) in [(0.7, 2.6, 3.5, 2.6), (0.7, 5.4, 3.5, 5.4),
                             (0.7, 2.6, 0.7, 5.4), (3.5, 2.6, 3.5, 5.4)]:
        d += elm.Line().at((xa, ya)).to((xb, yb))
    d += elm.Label().at((2.1, 4.0)).label("ESP32\nDevKit", fontsize=13)

    y3v3, y34, ygnd = 4.8, 3.9, 3.0
    d += elm.Line().at((3.5, y3v3)).to((4.0, y3v3))
    d += elm.Line().at((3.5, y34)).to((4.0, y34))
    d += elm.Line().at((3.5, ygnd)).to((4.0, ygnd))
    d += elm.Label().at((3.95, y3v3 + 0.26)).label("3V3", fontsize=11)
    d += elm.Label().at((3.95, y34 + 0.26)).label("D34", fontsize=11)
    d += elm.Label().at((3.95, ygnd + 0.26)).label("GND", fontsize=11)

    # ---- 三根跳线：先横后竖，互不交叉 ----
    d += elm.Line().at((4.0, y3v3)).tox(cR).color(RED)
    d += elm.Line().at((cR, y3v3)).toy(7.7).color(RED)
    d += elm.Dot().at((cR, 7.7))
    d += elm.Label().at((5.7, y3v3 + 0.3)).label("红 · 3V3", fontsize=11)

    d += elm.Line().at((4.0, y34)).tox(cM).color(YEL)
    d += elm.Line().at((cM, y34)).toy(5.5).color(YEL)
    d += elm.Dot().at((cM, 5.5))
    d += elm.Label().at((5.7, y34 + 0.3)).label("黄 · D34（中点）", fontsize=11)

    d += elm.Line().at((4.0, ygnd)).tox(cG).color(BLU)
    d += elm.Line().at((cG, ygnd)).toy(5.5).color(BLU)
    d += elm.Dot().at((cG, 5.5))
    d += elm.Label().at((5.7, ygnd + 0.3)).label("深色线 · GND", fontsize=11)

    # ---- 立链元件：330Ω（上半区内横跨）+ FSR（板上方，长尾插上半区顶行） ----
    d += elm.Resistor().endpoints((cR, 6.05), (cM, 6.05)).label("330Ω（上臂）", loc="bottom", fontsize=11)
    d += elm.Dot().at((cR, 6.05))
    d += elm.Dot().at((cM, 6.05))

    d += elm.ResistorVar().endpoints((cM, 9.3), (cG, 9.3)).label(
        "FSR402（下臂）· 预检直插上半区顶行", loc="top", fontsize=11)
    d += elm.Line().at((cM, 9.3)).toy(7.7)
    d += elm.Line().at((cG, 9.3)).toy(7.7)
    d += elm.Dot().at((cM, 7.7))
    d += elm.Dot().at((cG, 7.7))

    # ---- 标题与三查 ----
    d += elm.Label().at((7.5, 11.5)).label(
        "V2 桌面预检装配图 · 330Ω 上臂 / FSR 下臂（正式拓扑，反逻辑）", fontsize=14)
    d += elm.Label().at((0.5, -0.6)).label(
        "三查：① 红线 + 330Ω 一脚同列；330Ω 另一脚 + FSR 一脚 + 黄线 同列（中点）；FSR 另一脚 + 深色线 同列"
        "——全部插在上半区（SYB-170 上下两半互不导通！）", fontsize=11)
    d += elm.Label().at((0.5, -1.35)).label(
        "② 预期表现：空载读数稳定 ≈4095；指压 FSR 圆片读数往下掉（反逻辑）＝预检通过；"
        "0–4095 乱跳＝中点悬空，先重插黄线", fontsize=11)
    d += elm.Label().at((0.5, -2.1)).label(
        "③ 预检通过后：SYB-170 背胶贴充电宝；上鞋时 FSR 从板上拔下，"
        "改用 1m 杜邦延长（中点列、GND 列各一根接到 FSR 两脚）", fontsize=11)
