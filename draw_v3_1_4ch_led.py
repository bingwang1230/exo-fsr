#!/usr/bin/env python3
"""V3.1 + LED 秒闪 · 4 通道 FSR 装配图——SYB-170 迷你面包板（正拓扑 ×4 + LED 时钟同步支路）。

2026-10-23 在 draw_v3_4ch_syb170.py 基础上增 LED 支路（板宽 pitch 0.55→0.7 腾出右端三列）：
  D16(RX2) ←220Ω← LED(红5mm) ← GND₂（ESP32 第二个 GND 脚）——整秒亮 60ms（固件 ms%1000<60），
  与数据行同一 ms 时钟，视频帧对齐锚点（帖④前提）。选脚 D16/RX2 非 strapping【AI 设定，待确认】。
FSR 四通道拓扑不变：FSR 上臂 3.3V、330Ω 下臂 GND、中点→ADC（正逻辑：受压上升，空载≈0）。
通道映射（续 V2.6）：D32=左跟 D33=右跟 D34=左跖 D35=右跖。
导线配色（仅为辨识）：红=3V3，黄=中点→ADC，深蓝=GND，绿=D16（LED 支路）。
用法：.venv/bin/python draw_v3_1_4ch_led.py            # 出 web/v3_1_4ch_led.png
      CHECK=1 .venv/bin/python draw_v3_1_4ch_led.py    # 无标签检查版 + 泛洪连通性验收
"""

import os

import matplotlib

matplotlib.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

import schemdraw
import schemdraw.elements as elm

CHECK = bool(os.environ.get("CHECK"))
OUT = "/tmp/v3_1_4ch_led_check.png" if CHECK else "web/v3_1_4ch_led.png"

RED = "#d40000"
YEL = "#d4a017"
BLU = "#1a1a8c"
GRN = "#0a7a0a"
GRID = "#b8b8b8"
RAIL = "#8a8a8a"
# 检查模式：框线用浅灰（泛洪时不当导线），标签全省（文字不桥接）
BOXFRAME = "#b8b8b8" if CHECK else "#999"

with schemdraw.Drawing(file=OUT, dpi=130, show=False) as d:
    d.config(unit=2.4, fontsize=12, font="PingFang SC")

    def note(x, y, text, fs=10, halign=None):
        if not CHECK:
            kw = {"halign": halign} if halign else {}
            d.add(elm.Label().at((x, y)).label(text, fontsize=fs, **kw))

    # ---- SYB-170 板框与孔阵（上半区 bank A 全用；下半区仅示意） ----
    x0, pitch, cols = 4.7, 0.7, 17
    xs = [x0 + pitch * i for i in range(cols)]
    rowsA = [7.7, 7.15, 6.6, 6.05, 5.5]
    rowsB = [4.5, 3.95, 3.4, 2.85, 2.3]

    for (xa, ya, xb, yb) in [(4.4, 2.0, 16.2, 2.0), (4.4, 7.95, 16.2, 7.95),
                             (4.4, 2.0, 4.4, 7.95), (16.2, 2.0, 16.2, 7.95)]:
        d += elm.Line().at((xa, ya)).to((xb, yb)).color(BOXFRAME)
    note(9.6, 1.5, "SYB-170 迷你面包板（俯视）", 11)

    for r in rowsA + rowsB:
        for x in xs:
            d += elm.Dot(radius=0.045).at((x, r)).color(GRID)

    # ---- 列分配：每通道一对（GND 菊花列, 中点列），3V3 公共红列=最右；LED 支路用右端三列 ----
    c3v = [xs[0], xs[3], xs[6], xs[9]]
    cm = [xs[2], xs[5], xs[8], xs[11]]
    cG = xs[16]
    cLED_D16, cLED_K, cLED_A = xs[12], xs[13], xs[14]   # D16 列 / LED 阴极(GND₂)列 / 220Ω-LED 阳极列
    for cx, ytop, ybot in [(c3v[0], 7.15, 5.5), (c3v[1], 7.15, 5.5),
                           (c3v[2], 7.15, 5.5), (c3v[3], 7.15, 5.5),
                           (cm[0], 7.7, 6.05), (cm[1], 7.7, 6.05),
                           (cm[2], 7.7, 6.05), (cm[3], 7.7, 6.05),
                           (cG, 7.7, 6.6), (cLED_A, 7.7, 6.3)]:
        d += elm.Line().at((cx, ytop)).to((cx, ybot)).color(RAIL)

    # ---- ESP32 方框（左侧，八根引脚柱；标签放框内右对齐，避让彩色走线）----
    for (xa, ya, xb, yb) in [(0.7, 2.7, 3.5, 2.7), (0.7, 6.5, 3.5, 6.5),
                             (0.7, 2.7, 0.7, 6.5), (3.5, 2.7, 3.5, 6.5)]:
        d += elm.Line().at((xa, ya)).to((xb, yb)).color(BOXFRAME)
    note(2.0, 4.6, "ESP32\nDevKit", 13)

    yGND = 6.15
    stubs = [(5.7, "D33"), (5.25, "D32"), (4.8, "D35"), (4.35, "D34"),
             (3.9, "D16"), (3.45, "GND₂"), (3.0, "3V3")]
    for y, name in [(yGND, "GND")] + stubs:
        d += elm.Line().at((3.5, y)).to((4.0, y))
        note(3.38, y, name, 9.5, halign="right")

    # ---- GND 深蓝菊花链：ESP32 → 首列上行，横线走 6.6 行 ----
    d += elm.Line().at((4.0, yGND)).tox(c3v[0]).color(BLU)
    d += elm.Line().at((c3v[0], yGND)).toy(7.15).color(BLU)
    d += elm.Dot().at((c3v[0], 6.6))
    d += elm.Dot().at((c3v[0], 7.15))
    for i in range(1, 4):
        d += elm.Line().at((c3v[i - 1], 6.6)).tox(c3v[i]).color(BLU)
        d += elm.Line().at((c3v[i], 6.6)).toy(7.15).color(BLU)
        d += elm.Dot().at((c3v[i], 6.6))
        d += elm.Dot().at((c3v[i], 7.15))

    # ---- 中点黄线：四列各出一根，接到对应 ADC 引脚（零交叉） ----
    ch = [(0, 5.7), (1, 5.25), (2, 4.8), (3, 4.35)]   # cm[i] → 引脚柱 y
    for i, y in ch:
        d += elm.Line().at((cm[i], 6.05)).toy(y).color(YEL)
        d += elm.Line().at((cm[i], y)).tox(4.0).color(YEL)
        d += elm.Dot().at((cm[i], 6.05))

    # ---- 3V3 红线：ESP32 → 最右列（FSR 上臂公共端） ----
    d += elm.Line().at((4.0, 3.0)).tox(cG).color(RED)
    d += elm.Line().at((cG, 3.0)).toy(7.7).color(RED)
    d += elm.Dot().at((cG, 7.7))

    # ---- 330Ω ×4 下臂：上半区 7.15 行，各跨 GND 菊花列 → 中点列 ----
    for i in range(4):
        d += elm.Resistor().endpoints((c3v[i], 7.15), (cm[i], 7.15)).label(
            "330Ω" if i == 1 and not CHECK else "", loc="bottom", fontsize=11)
        d += elm.Dot().at((cm[i], 7.15))

    # ---- FSR ×4 上臂：板上方错层，左端=中点列顶，右端共 3V3 列 ----
    fsr_y = [13.0, 11.6, 10.2, 8.8]
    fsr_names = ["FSR 右跟（D33）", "FSR 左跟（D32）", "FSR 右跖（D35）", "FSR 左跖（D34）"]
    for i in range(4):
        d += elm.ResistorVar().endpoints((cm[i], fsr_y[i]), (cG, fsr_y[i])).label(
            fsr_names[i] if not CHECK else "", loc="top", fontsize=11)
        d += elm.Line().at((cm[i], fsr_y[i])).toy(7.7)
        d += elm.Dot().at((cm[i], 7.7))
    d += elm.Line().at((cG, fsr_y[0])).toy(7.7).color("#444")
    for y in fsr_y:
        d += elm.Dot().at((cG, y))

    # ---- LED 秒闪支路：D16 → 220Ω → LED（阳极朝电阻）→ GND₂ 回线（零交叉） ----
    d += elm.Line().at((4.0, 3.9)).tox(cLED_D16).color(GRN)          # D16 横线
    d += elm.Line().at((cLED_D16, 3.9)).toy(7.7).color(GRN)          # 上行至 220Ω 行
    d += elm.Resistor().endpoints((cLED_D16, 7.7), (cLED_A, 7.7)).label(
        "220Ω" if not CHECK else "", loc="top", fontsize=11)
    d += elm.LED().endpoints((cLED_A, 6.6), (cLED_K, 6.6)).label(    # 阳极=右(电阻侧)，阴极=左(GND₂)
        "LED 红 5mm" if not CHECK else "", loc="top", fontsize=10)
    d += elm.Line().at((cLED_K, 6.6)).toy(3.45).color(BLU)           # GND₂ 回线（深蓝=GND 语义）
    d += elm.Line().at((cLED_K, 3.45)).tox(4.0).color(BLU)
    for (px, py) in [(cLED_D16, 7.7), (cLED_A, 7.7), (cLED_A, 6.6), (cLED_K, 6.6)]:
        d += elm.Dot().at((px, py))

    # ---- 线色图例与标题、四查 ----
    note(7.6, 1.0,
         "红线 = 3V3（最右列）｜ 黄线 ×4 = 中点 → D32/33/34/35 ｜ 深蓝线 = GND（菊花链 + LED 回线）｜ 绿线 = D16 → 220Ω（LED 支路）", 10)
    note(7.6, 0.3,
         "LED 支路：D16 → 220Ω → LED → GND₂，整秒亮 60ms（时钟对齐标记）｜ 实拍时 LED 不插面包板：220Ω 留板上，LED 经两根 1m 杜邦延长至脚边/鞋面（长脚线标红色胶带）——板在口袋里，LED 必须进画框", 10)
    note(7.6, -0.4,
         "引脚柱顺序 = 实物丝印反读方向；3V3/GND 实板另侧，接线认丝印不认图位；GND₂ = 任选一个空闲 GND 脚（30Pin 板不止一个）", 10)
    note(7.9, 14.9,
         "V3.1 + LED 秒闪 · 4 通道 FSR 装配图（FSR 上臂 3V3 / 330Ω 下臂 GND ×4，正逻辑；LED 支路做视频-数据时钟对齐）", 14)
    note(0.5, -1.5,
         "四查：① 每通道三件同列才算通——330Ω 一脚与深蓝菊花链同列（GND），另一脚与黄线同列（中点列），"
         "FSR 两脚分别在中点列与最右红列（3V3）——全部插上半区（SYB-170 上下两半互不导通！）", 11)
    note(0.5, -2.25,
         "② 预检（指压四角，按位置报序）：空载稳定 ≈0、指压对应通道上升且其余三路不动＝通过；"
         "重点核右脚：压右脚跟必须 D33 上升、压右脚跖必须 D35 上升", 11)
    note(0.5, -3.0,
         "③ LED 支路三件同列：220Ω 一脚与绿线同列（D16 列）、另一脚接 1m 杜邦 → 脚边 LED 长脚(+)；短脚(−)另一根 1m 杜邦 → 面包板 GND——"
         "上电即每秒一闪；不亮先查方向（长脚必须朝 220Ω 侧），再看亮度（暗可换 100Ω）", 11)
    note(0.5, -3.75,
         "④ 上鞋：FSR 移鞋内四点，中点侧与 GND 侧各换 1m 杜邦延长；自热观察照旧——静止站立 2-3 分钟看读数有无单向漂移", 11)

# ---- 检查模式：泛洪连通性验收（红→蓝 = FSR 通路；绿→蓝 = LED 通路）----
if CHECK:
    from collections import deque

    from PIL import Image

    img = Image.open(OUT).convert("RGB")
    w, h = img.size
    px = img.load()

    def near(c1, c2, tol=40):
        return all(abs(a - b) <= tol for a, b in zip(c1, c2))

    REDC, GRNC, BLUC = (212, 0, 0), (10, 122, 10), (26, 26, 140)
    mask = [[False] * w for _ in range(h)]
    seeds_red, seeds_grn = [], []

    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            sat = max(r, g, b) - min(r, g, b)
            lum = 0.3 * r + 0.59 * g + 0.11 * b
            if near((r, g, b), REDC) or near((r, g, b), GRNC) or sat > 45 or lum < 120:
                mask[y][x] = True
                if near((r, g, b), REDC):
                    seeds_red.append((x, y))
                if near((r, g, b), GRNC):
                    seeds_grn.append((x, y))

    # 膨胀 2px：抗锯齿细线直接泛洪会断——闭运算后导线像素连片，再判连通
    D = 2
    dil = [[any(mask[y + dy][x + dx] for dy in range(-D, D + 1) for dx in range(-D, D + 1)
                if 0 <= y + dy < h and 0 <= x + dx < w) for x in range(w)] for y in range(h)]

    def flood_reaches_blue(seeds):
        seen = [[False] * w for _ in range(h)]
        q = deque(seeds)
        for s in seeds:
            seen[s[1]][s[0]] = True
        while q:
            x, y = q.popleft()
            if near(px[x, y], BLUC, 60):
                return True
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and dil[ny][nx] and not seen[ny][nx]:
                    seen[ny][nx] = True
                    q.append((nx, ny))
        return False

    ok1 = flood_reaches_blue(seeds_red)
    ok2 = flood_reaches_blue(seeds_grn)
    print(f"BFS 3V3→GND(FSR通路): {'PASS' if ok1 else 'FAIL'}")
    print(f"BFS D16→GND(LED通路): {'PASS' if ok2 else 'FAIL'}")
    if not (ok1 and ok2):
        raise SystemExit(1)
print("done ->", OUT)
