# S020 步态事件离线分析（2026-10-07）
# 用法：python3 analyze_gait.py <csv> [起始秒 结束秒]   （秒为 CSV 相对时间）
# 管线：BLE 丢帧小洞插值/大洞标记 → 中值5 + EMA 滤波 → 状态机事件检测（跟击/全掌/跟离/指离）→ 统计报告
# CSV 格式：ms,左跟,左跖,右跟,右跖（v9.6 起物理正确；≤20261006 旧文件需先手工换算，见 fsr_live.py 头注）
# 阈值自校准：跟通道 p95×0.3 定站立门；跖临界 = 摆动期电平与站立期电平的中点（兼容预载传感器）

import csv
import statistics
import sys

GAP_SMALL = 0.05   # ≤50ms 丢帧 → 线性插值
GAP_BIG = 0.10     # >100ms → 数据洞，检测器不跨洞配对事件


def load(path):
    rows = []
    with open(path) as f:
        for r in csv.reader(f):
            if not r or len(r) < 5:
                continue
            try:
                rows.append([int(x) for x in r[:5]])
            except ValueError:
                pass
    return rows


def resample(rows, hz_out=100.0):
    """均匀重采样：小洞线性插值；大洞(>GAP_BIG)插值但记录洞区间 [t0,t1]。"""
    t = [r[0] / 1000.0 for r in rows]
    holes = []
    out = []
    ti, i = t[0], 0
    n = len(rows)
    while ti <= t[-1] and i < n - 1:
        while i < n - 2 and t[i + 1] < ti:
            i += 1
        if t[i + 1] - t[i] > GAP_BIG and t[i] <= ti <= t[i + 1]:
            if not holes or holes[-1][1] < t[i] - 1e-6:
                holes.append((t[i], t[i + 1]))
        w = (ti - t[i]) / (t[i + 1] - t[i]) if t[i + 1] > t[i] else 0.0
        w = min(max(w, 0.0), 1.0)
        vals = [round(a + (b - a) * w) for a, b in zip(rows[i][1:], rows[i + 1][1:])]
        out.append((ti, vals))
        ti += 1.0 / hz_out
    return out, holes


def med5(x):
    y = list(x)
    for k in range(2, len(x) - 2):
        y[k] = sorted(x[k - 2:k + 3])[2]
    return y


def ema(x, a=0.3):
    y = [float(x[0])]
    for v in x[1:]:
        y.append(a * v + (1 - a) * y[-1])
    return y


def detect(heel, met, hz, k0=0, k1=None):
    """状态机（自校准阈值 + 0.15s 确认期）。返回 [(k, kind)]，kind∈HS/FF/HO/TO。
    跖摆动电平标定只用「持续≥0.3s 的跟低位段」——短暂跟离地（站立后期）时跖仍在承力，
    混入会拍摆动电平标高、指离提前（2026-10-07 实测踩坑）。"""
    n = len(heel) if k1 is None else k1
    hp = sorted(heel[k0:n])
    heel_th = max(300, int(hp[int(len(hp) * 0.95)] * 0.3))
    heel_tl = heel_th // 2
    CONF = int(0.15 * hz)
    # 找持续低位段（真摆动）
    below = 0
    swing_segs = []          # [(start, end)]
    for k in range(k0, n + 1):
        low = heel[k] < heel_tl if k < n else False
        if low:
            below += 1
        else:
            if below >= int(0.3 * hz):
                swing_segs.append((k - below, k))
            below = 0
    swing_vals = [met[k] for a, b in swing_segs for k in range(a, b)]
    sw = sorted(swing_vals)[int(len(swing_vals) * 0.75)] if swing_vals else 0
    st = sorted(met[k] for k in range(k0, n) if heel[k] > heel_th)
    stl = st[int(len(st) * 0.75)] if st else 1000   # p75：跟高位期间跖从击后低到满载，中位会偏早
    met_tl = max(300, int((sw + stl) // 2)) if sw < stl else max(300, int(stl * 0.5))
    evs = []
    state = "stance" if heel[k0] > heel_th else "swing"
    below = 0
    ff = ho = False
    for k in range(k0, n):
        H, M = heel[k], met[k]
        if state == "swing":
            if H < heel_tl:
                below += 1
            # 注意：过潲带（tl<H≤th）不清零 below——EMA 平滑后爬坡需多个样本，
            # 清零会让 HS 永远凑不齐确认数（2026-10-07 实测踩坑）
            if below >= CONF and H > heel_th:
                evs.append((k, "HS"))
                state = "stance"
                ff = ho = False
                below = 0
        else:
            if not ff and M > met_tl and H > heel_tl:
                evs.append((k, "FF"))
                ff = True
            if not ho and H < heel_tl and M > met_tl:
                evs.append((k, "HO"))
                ho = True
            if H < heel_tl and M < met_tl:
                below += 1
                if below >= CONF:
                    evs.append((k - CONF, "TO"))
                    state = "swing"
            else:
                below = 0
    return evs, (heel_th, heel_tl, met_tl)


def report(path, w0=None, w1=None):
    rows = load(path)
    if len(rows) < 100:
        print("数据太少")
        return
    hz = len(rows) / ((rows[-1][0] - rows[0][0]) / 1000.0)
    rs, holes = resample(rows, hz_out=100.0)
    hzr = 100.0
    k0 = int((w0 if w0 else 0) * hzr)
    k1 = min(int((w1 if w1 else rs[-1][0]) * hzr), len(rs) - 2)
    chf = []
    for c in range(4):
        chf.append(ema(med5([v[1][c] for v in rs]))[k0:k1])
    print(f"{path}: {len(rows)} 行, 原始 {hz:.0f}Hz, 重采样 {hzr:.0f}Hz")
    if holes:
        hs_ = ", ".join(f"{a:.1f}~{b:.1f}s({(b-a)*1000:.0f}ms)" for a, b in holes)
        print(f"数据洞 {len(holes)} 个: {hs_}")
    allst = {}
    for nm, (hi, mi) in [("左脚", (0, 1)), ("右脚", (2, 3))]:
        ev, (th, tl, mtl) = detect(chf[hi], chf[mi], hzr)
        hs = sorted(k for k, x in ev if x == "HS")
        to = sorted(k for k, x in ev if x == "TO")
        stances = []
        for a in hs:
            nx = [b for b in to if b > a and 0.3 < (b - a) / hzr < 2.0]
            if nx:
                stances.append((nx[0] - a) / hzr)
        cyc = [(b - a) / hzr for a, b in zip(hs, hs[1:]) if 0.5 < (b - a) / hzr < 2.5]
        ms_ = statistics.median(stances) if stances else 0
        mc = statistics.median(cyc) if cyc else 0
        print(f"  {nm}: 跟击 {len(hs)} 指离 {len(to)} 全掌 {sum(1 for _, x in ev if x == 'FF')} "
              f"跟离 {sum(1 for _, x in ev if x == 'HO')}"
              f" ｜ 阈值 跟>{th}/<{tl} 跖临界{mtl}"
              f" ｜ 站立相中位 {ms_:.2f}s 周期中位 {mc:.2f}s 占比 {(ms_ / mc * 100 if mc else 0):.0f}%")
        allst[nm] = (hs, to, ms_, mc)
    L, R = allst["左脚"], allst["右脚"]
    dur = (k1 - k0) / hzr
    print(f"  对称性: 站立相差 {abs(L[2] - R[2]) * 1000:.0f}ms ｜ 步频 ≈ {(len(L[0]) + len(R[0])) / (dur / 60):.0f} 步/分")
    return allst


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    w0 = float(sys.argv[2]) if len(sys.argv) > 2 else None
    w1 = float(sys.argv[3]) if len(sys.argv) > 3 else None
    report(sys.argv[1], w0, w1)
