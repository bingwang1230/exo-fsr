#!/usr/bin/env python3
"""标定曲线绘制 —— 20260919 单片标定（V1 桌面装置）。

读 data/20260919_单片标定.md 同源数据（硬编码表），输出：
  data/calib_20260919.png —— 左：ADC-F 散点+折线；右：log-log R-F
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]

# 档, g, N, adc（档0 无稳态不入图）
rows = [
    (4, 172, 1.69, 3227),
    (3, 314, 3.08, 3565),
    (1, 341, 3.34, 3755),
    (2, 522, 5.12, 3862),
    (5, 303, 2.97, 3626),
]
fs = sorted(r[2] for r in rows)
adc = {r[2]: r[3] for r in rows}
adcs = [adc[f] for f in fs]
rs = [10000 * (4095 / a - 1) for a in adcs]

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5), facecolor="#f7f7f7")

a1.plot(fs, adcs, "o-", color="#d32f2f", lw=2, ms=8)
for r in rows:
    a1.annotate(f"{r[1]}g", (r[2], r[3]), textcoords="offset points",
                xytext=(8, -4), fontsize=10)
a1.set_xlabel("力 F (N)")
a1.set_ylabel("ADC 中位数 (0–4095)")
a1.set_title("ADC – 力（对数压缩：×3 重量 → +20% 读数）")
a1.grid(alpha=0.3)
a1.set_ylim(3000, 4095)

a2.loglog(fs, rs, "s-", color="#1565c0", lw=2, ms=8)
a2.set_xlabel("力 F (N)")
a2.set_ylabel("R_FSR (Ω)   [10kΩ×(4095/ADC−1)]")
a2.set_title("log–log R–F（FSR 特征视图）")
a2.grid(alpha=0.3, which="both")

fig.suptitle("FSR402 单片标定 · 2026-09-19 · V1 桌面装置（0.3–5N 适用，>5N 近饱和）",
             fontsize=13)
fig.tight_layout()
fig.savefig("data/calib_20260919.png", dpi=110)
print("saved data/calib_20260919.png")
