#!/usr/bin/env python3
"""帖④/B站 素材：走路视频 × 四通道步态曲线 竖屏合成（LED 锚点对齐）。

用法: python3 web/render_gait_composite.py <csv> <video.mp4> <out.mp4> <board_ms_offset>
  csv            fsr_live 录制文件（ms,左跟,左跖,右跟,右跖）
  video          走路视频（与 CSV 同一场，含 LED 秒闪）
  board_ms_offset 视频 0s 对应的板载毫秒 = 1000*K - 400 + 1000*K'
  对时法：视频里抓红色 LED 闪帧（30fps 下 60ms≈2帧），闪帧时刻 t_v 满足
  board_ms % 1000 == 0，即 board_ms(t_v) = 1000*t_v + offset；多闪联合求 K。
依赖: .venv（numpy/PIL/matplotlib）；ffmpeg 在 PATH。
"""
import csv, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager, pyplot as plt

csv_path, video_path, out_path, OFF = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
W, H, FPS, DUR = 1080, 1220, 30, 32.2
rows = []
with open(csv_path) as f:
    for line in f:
        p = line.strip().split(',')
        if len(p) == 5: rows.append(tuple(map(int, p)))
data = np.array(rows)
t = (data[:, 0] - OFF) / 1000.0
names = ['左跟', '左跖', '右跟', '右跖']
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
for f in ['Hiragino Sans GB', 'STHeiti', 'PingFang SC', 'Arial Unicode MS']:
    if any(f.lower() == x.name.lower() for x in font_manager.fontManager.ttflist):
        plt.rcParams['font.family'] = f; break
def medfilt(x, k=9):
    half = k//2; out = np.copy(x)
    for i in range(len(x)): out[i] = np.median(x[max(0, i-half):i+half+1])
    return out
w0 = t[0]
fig, ax = plt.subplots(figsize=(10.8, 12.2), dpi=100)
fig.patch.set_facecolor('#111111'); ax.set_facecolor('#111111')
for c in range(4):
    ax.plot(t, medfilt(data[:, c+1]), color=colors[c], lw=2.2, label=names[c])
ax.set_xlim(w0, w0+DUR); ax.set_ylim(-80, 3080)
ax.grid(alpha=0.15, color='white'); ax.tick_params(colors='white', labelsize=16)
for s in ax.spines.values(): s.set_color('#444444')
leg = ax.legend(loc='upper right', ncol=4, fontsize=18, facecolor='#111111', edgecolor='#444444')
for txt in leg.get_texts(): txt.set_color('white')
ax.set_title('步态曲线 · 左脚跟/跖 + 右脚跟/跖 · 100Hz 蓝牙实时', color='white', fontsize=20, pad=14)
fig.tight_layout(); fig.canvas.draw()
bg = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3]).resize((W, H))
plt.close(fig)
os.makedirs('/tmp/curve_frames', exist_ok=True)
for f in os.listdir('/tmp/curve_frames'): os.remove(f'/tmp/curve_frames/{f}')
font = ImageFont.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc', 34)
frames = int(DUR*FPS)
for i in range(frames):
    img = bg.copy(); d = ImageDraw.Draw(img)
    x = int(45 + (W-90)*(i/FPS)/DUR)
    d.line([(x, 60), (x, H-60)], fill=(255, 215, 0), width=4)
    d.text((min(x+12, W-170), 70), f'{i/FPS:0.1f}s', fill=(255, 215, 0), font=font)
    img.save(f'/tmp/curve_frames/cf_{i:04d}.png')
subprocess.run(['ffmpeg', '-v', 'error', '-framerate', str(FPS), '-i', '/tmp/curve_frames/cf_%04d.png',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '/tmp/curves.mp4', '-y'], check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-i', video_path, '-i', '/tmp/curves.mp4', '-filter_complex',
                f'[0:v]scale=1080:608:flags=lanczos,pad=1080:700:(ow-iw)/2:(oh-ih)/2:black[top];'
                f'[1:v]scale=1080:1220[bot];[top][bot]vstack=inputs=2:shortest=1[out]',
                '-map', '[out]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '19', '-r', str(FPS), out_path, '-y'], check=True)
print('done:', out_path)
