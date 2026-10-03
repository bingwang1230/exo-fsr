#!/usr/bin/env python3
"""FSR live 波形页 v7（serial / BLE 双数据源 + canvas 页面 + 录制）。

MBP 上运行：python3 /tmp/fsr_live.py  → 浏览器 http://localhost:8324/
- 串口（默认）：自动探测 /dev/cu.usbserial*，stty 配 115200 后（换 USB 口编号会变），stty 配 115200 后
  select 非阻塞读 + 手动拼行（v1 的 readline 会卡死，缓冲区只剩 1 点）。
- BLE（--ble）：bleak 扫描广播名 "exo-fsr"（Nordic UART Service TX，与固件 main.py 同 UUID）
  → 连接 → 订阅 notify，行格式与串口完全同；断线/断流自动重扫重连。
  依赖：pip3 install bleak（串口模式另需 pyserial）。
- 页面：canvas 滚动曲线 + 大号当前值 + 窗口 min/max + 实时数据率。
- 自身守护化（双 fork 脱离会话），异常写 /tmp/fsr_live.log。
"""

import collections
import glob
import http.server
import json
import os
import select
import subprocess
import sys
import threading
import time

DEV_CANDIDATES = "/dev/cu.usbserial*"
HTTP_PORT = 8324
LOG = "/tmp/fsr_live.log"

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>FSR live · V2 预检</title>
<style>body{margin:0;background:#111;color:#eee;font-family:sans-serif}
#cur{font-size:64px;font-weight:bold;color:#ffd42a}
#meta{font-size:14px;color:#aaa;line-height:1.7}</style></head>
<body>
<div id="cur">--</div>
<canvas id="cv" width="1200" height="400" style="width:99vw"></canvas>
<div style="margin:8px 0"><button id="rec" onclick="toggleRec()" style="font-size:18px;padding:6px 24px;background:#a02020;color:#fff;border:none;border-radius:6px">● 录制</button> <span id="recinfo" style="color:#aaa"></span></div>
<div id="meta">连接中…</div>
<script>
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
let data=[];
function draw(){
 ctx.fillStyle='#111';ctx.fillRect(0,0,cv.width,cv.height);
 [4095,3072,2048,1024,0].forEach(v=>{
  const y=cv.height-(v/4095)*cv.height;
  ctx.strokeStyle=v==2048?'#555':'#333';ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(cv.width,y);ctx.stroke();
  ctx.fillStyle='#666';ctx.font='12px sans-serif';ctx.fillText(v,4,y-3);});
 if(!data.length)return;
 const t1=Date.now()/1000,t0=t1-6;
 ctx.strokeStyle='#ffd42a';ctx.lineWidth=2;ctx.beginPath();
 let started=false;
 data.forEach(p=>{
  if(p[0]===t0)return;
  const x=((p[0]-t0)/6)*cv.width,y=cv.height-(p[1]/4095)*cv.height;
  if(!started){ctx.moveTo(x,y);started=true;}else ctx.lineTo(x,y);});
 ctx.stroke();
}
async function tick(){
 try{const r=await fetch('/data');data=await r.json();
  const cur=data[data.length-1];
  const now=Date.now()/1000;
  const last1s=data.filter(p=>now-p[0]===0?false:(now-p[0])<1).length;
  if(cur)document.getElementById('cur').textContent=cur[1];
  const vals=data.map(p=>p[1]);
  document.getElementById('meta').innerHTML=
   '数据率 '+last1s+' 点/s（应≈100）｜窗口6s min='+Math.min(...vals)+' max='+Math.max(...vals)+
   '（当前 '+cur[1]+'）｜V2 反逻辑：空载≈4095，受压读数<b>下掉</b>';
 }catch(e){document.getElementById('meta').textContent='服务未响应：'+e;}
 draw();
}
let recOn=false;
async function toggleRec(){
 recOn=!recOn;
 const r=await fetch(recOn?'/rec/start':'/rec/stop');
 const j=await r.json();
 document.getElementById('rec').style.background=recOn?'#a02020':'#333';
 document.getElementById('recinfo').textContent=j.file||'';
}
setInterval(tick,300);tick();
</script></body></html>"""


def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass


STATS = {"opens": 0, "chunks": 0, "bytes": 0, "stalls": 0, "last_chunk": 0.0}


RAW = collections.deque(maxlen=4)


def feed_line(s, buf):
    """串口/BLE 共用：一行 "ms,raw" → 最新值进 buf + 录制落盘。"""
    if len(RAW) == 0 or RAW[-1] != s:
        RAW.append(s[:40])
    if "," in s:
        p = s.split(",")[1]
        if p.isdigit():
            buf.append((time.time(), int(p)))
            if REC["file"] is not None:
                REC["file"].write(s + "\n")
                REC["count"] += 1


def split_chunks(pending, buf):
    """字节流 → 按行喂 feed_line，返回剩余不完整行。"""
    while b"\n" in pending:
        line, pending = pending.split(b"\n", 1)
        feed_line(line.decode("utf-8", "ignore").strip(), buf)
    return pending


def reader(buf):
    import serial as pyserial  # macOS CH340：必须 IOSSIOSPEED（pyserial），stty 不生效
    while True:
        ser = None
        try:
            dev = (sorted(glob.glob(DEV_CANDIDATES)) or [None])[0]
            if not dev:
                log("no serial device, retrying")
                time.sleep(2)
                continue
            log("opening " + dev)
            ser = pyserial.Serial(dev, 115200, timeout=0.5)
            STATS["opens"] += 1
            STATS["last_chunk"] = time.time()
            pending = b""
            while True:
                chunk = ser.read(4096)
                if chunk:
                    STATS["chunks"] += 1
                    STATS["bytes"] += len(chunk)
                    STATS["last_chunk"] = time.time()
                    pending = split_chunks(pending + chunk, buf)
                elif time.time() - STATS["last_chunk"] > 3.0:
                    STATS["stalls"] += 1
                    raise OSError("stall watchdog: reopen")
        except Exception as e:
            log("reader error: %r" % e)
            if ser is not None:
                try:
                    ser.close()
                except Exception:
                    pass
            time.sleep(1)


def ble_main(buf):
    """BLE 数据源：事件循环独占线程，扫描→连接→notify→断线重连。"""
    import asyncio

    async def run():
        from bleak import BleakClient, BleakScanner

        TX = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # NUS TX，与固件一致
        while True:
            try:
                log("ble: scanning for exo-fsr ...")
                dev = await BleakScanner.find_device_by_name("exo-fsr", timeout=10)
                if dev is None:
                    STATS["stalls"] += 1
                    continue
                log("ble: connecting " + str(dev.address))
                async with BleakClient(dev, timeout=15) as client:
                    log("ble: connected")
                    STATS["opens"] += 1
                    STATS["last_chunk"] = time.time()
                    state = {"pending": b""}

                    def on_notify(_h, data):
                        STATS["chunks"] += 1
                        STATS["bytes"] += len(data)
                        STATS["last_chunk"] = time.time()
                        state["pending"] = split_chunks(state["pending"] + bytes(data), buf)

                    await client.start_notify(TX, on_notify)
                    while client.is_connected and time.time() - STATS["last_chunk"] < 5.0:
                        await asyncio.sleep(0.5)
                    log("ble: link lost or stalled, will rescan")
                    STATS["stalls"] += 1
            except Exception as e:
                log("ble error: %r" % e)
            await asyncio.sleep(1)  # 重连退避

    asyncio.run(run())


REC = {"file": None, "count": 0}


def serve(buf):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/rec/start"):
                if REC["file"] is None:
                    import datetime
                    name = os.path.join(os.path.expanduser("~/code/exo-fsr/data"),
                                        datetime.datetime.now().strftime("v2_%Y%m%d_%H%M%S.csv"))
                    REC["file"] = open(name, "w")
                    REC["count"] = 0
                body = json.dumps({"recording": True, "file": REC["file"].name}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            elif self.path.startswith("/rec/stop"):
                if REC["file"] is not None:
                    REC["file"].close()
                    n, name = REC["count"], REC["file"].name
                    REC["file"] = None
                    body = json.dumps({"recording": False, "file": name, "samples": n}).encode()
                else:
                    body = json.dumps({"recording": False, "file": None}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            elif self.path.startswith("/dbg"):
                st = dict(STATS)
                st["now"] = time.time()
                st["idle"] = round(time.time() - STATS["last_chunk"], 1)
                st["points"] = len(buf)
                st["raw"] = list(RAW)
                body = json.dumps(st).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            elif self.path.startswith("/data"):
                body = json.dumps(list(buf)[-800:]).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            else:
                body = PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    http.server.HTTPServer(("127.0.0.1", HTTP_PORT), H).serve_forever()


def main():
    buf = collections.deque(maxlen=3000)
    use_ble = "--ble" in sys.argv[1:]
    threading.Thread(target=ble_main if use_ble else reader, args=(buf,), daemon=True).start()
    log("server starting on %d (source: %s)" % (HTTP_PORT, "ble" if use_ble else "serial"))
    serve(buf)


if __name__ == "__main__":
    pid = os.fork()
    if pid == 0:
        os.setsid()
        pid2 = os.fork()
        if pid2 == 0:
            try:
                fd = os.open("/dev/null", os.O_RDWR)
                os.dup2(fd, 0)
                os.dup2(fd, 1)
                os.dup2(fd, 2)
                main()
            except Exception as e:
                log("fatal: %r" % e)
        os._exit(0)
    sys.exit(0)
