# FSR V1 桌面版 —— ESP32 + FSR402 分压首读

L3 电子动力 · 实操首课的固件与电脑端脚本。
电路：`3.3V —[FSR402]—●(GPIO34)—[10kΩ]—GND`，详见 exoskeleton 仓 `learn/l3-电子动力/materials/接线图_V1桌面版.html`。

## 文件

- `main.py` —— MicroPython 固件：GPIO34 (ADC1_CH6) 100Hz 采样，串口输出 `毫秒,原始值(0-4095)`。
- `plot_fsr.py` —— 电脑端实时曲线：读 USB 串口，matplotlib 实时画波形。

## 烧录与运行（mini / MBP 通用）

```bash
# 1. 工具链（一次性）
uv tool install mpremote          # 或 pip install mpremote esptool
python3 -m pip install esptool matplotlib pyserial

# 2. 插上 ESP32（Type-C），找串口
ls /dev/cu.*                      # mac 上一般是 /dev/cu.usbserial-XXXX（CH340）

# 3. 刷 MicroPython 固件（首次一次即可，固件文件另行下载 ESP32_GENERIC.bin）
esptool.py --port /dev/cu.usbserial-XXXX erase_flash
esptool.py --port /dev/cu.usbserial-XXXX --baud 460800 write_flash -z 0x1000 ESP32_GENERIC.bin

# 4. 传 main.py 并运行
mpremote cp main.py : && mpremote reset

# 5. 电脑端看曲线
python3 plot_fsr.py /dev/cu.usbserial-XXXX
```

## 验收判据

手指按压 FSR → 曲线实时起伏（松手回落）= 链路全通，V1 完成。

## 诚实边界（对外口径同此）

量程 ~0.2–20N：绝对力值不可读（迟滞 ±10%、重压顶格）；本课只验证「压力→波形」链路。
