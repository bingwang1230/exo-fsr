#!/usr/bin/env python3
"""FSR live 波形页 v8（serial / BLE 双源 · 双通道曲线 · 实时钟联动 + 录制）。

运行：python3 fsr_live.py [--ble]  →  浏览器 http://localhost:8324/
- 数据格式：固件 V2.6 起每行 "毫秒数,左,右"（双通道；单通道旧行 "毫秒数,raw" 自动兼容）。
- 串口（默认）：自动探测 /dev/cu.usbserial*；macOS CH340 必须用 pyserial（IOSSIOSPEED）。
- BLE（--ble）：bleak 扫描广播名 "exo-fsr"（Nordic UART Service TX）→ 连接 → 订阅 notify；
  断线/断流自动重扫重连。依赖：pip3 install bleak（串口另需 pyserial）。
- 页面：双曲线滚动窗（左=金/黄线 D34，右=绿线 D35）+ 两路大号当前值 + 各路窗口 min/max
  + 实时数据率 + **实时钟联动**：页首毫秒级时钟，x 轴下缘标墙上时钟（慢动作视频对齐用）。
- 录制：页面按钮 → data/v2_*.csv，原样落固件行（ms,left,right）。
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

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>FSR live · V2.6 双脚</title>
<style>body{margin:0;background:#111;color:#eee;font-family:sans-serif}
#curL{font-size:56px;font-weight:bold;color:#ffd42a}
#curR{font-size:56px;font-weight:bold;color:#3ecf6e;margin-left:48px}
.lbl{font-size:14px;color:#aaa;margin-right:24px}
#clk{font-size:20px;color:#7ec8ff;font-family:monospace;margin:2px 0 6px}
#meta{font-size:14px;color:#aaa;line-height:1.7}</style></head>
<body>
<span class="lbl">左脚 D34</span><span id="curL">--</span>
<span class="lbl" style="margin-left:48px">右脚 D35</span><span id="curR">--</span>
<div id="clk"></div>
<canvas id="cv" width="1200" height="400" style="width:99vw"></canvas>
<div style="margin:8px 0"><button id="rec" onclick="toggleRec()" style="font-size:18px;padding:6px 24px;background:#a02020;color:#fff;border:none;border-radius:6px">● 录制</button> <span id="recinfo" style="color:#aaa"></span></div>
<div id="meta">连接中…</div>
<script>
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
let data=[];
const COLS=['','#ffd42a','#3ecf6e'],NAMES=['','左','右'];
setInterval(()=>{const d=new Date();document.getElementById('clk').textContent=
 '⏱ '+d.toLocaleTimeString('zh-CN',{hour12:false})+'.'+String(d.getMilliseconds()).padStart(3,'0');},99);
function fmtClock(ts){const d=new Date(ts*1000);
 return d.toLocaleTimeString('zh-CN',{hour12:false});}
function draw(){
 ctx.fillStyle='#111';ctx.fillRect(0,0,cv.width,cv.height);
 [4095,3072,2048,1024,0].forEach(v=>{
  const y=8+cv.height-16-(v/4095)*(cv.height-16);
  ctx.strokeStyle=v==2048?'#555':'#333';ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(cv.width,y);ctx.stroke();
  ctx.fillStyle='#666';ctx.font='12px sans-serif';ctx.fillText(v,4,y-3);});
 const t1=Date.now()/1000,t0=t1-6;
 // x 轴墙上时钟刻度（实时钟联动：窗口随真实时间滚动）
 ctx.fillStyle='#888';ctx.font='12px monospace';
 for(let s=0;s<=6;s+=2){
  const x=(s/6)*cv.width;
  ctx.strokeStyle='#333';ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,cv.height);ctx.stroke();
  ctx.fillText(fmtClock(t0+s),x+3,cv.height-5);}
 if(!data.length)return;
 const nch=data[0].length-1;
 for(let c=1;c<=nch;c++){
  ctx.strokeStyle=COLS[c];ctx.lineWidth=2;ctx.beginPath();
  let started=false;
  data.forEach(p=>{
   const x=((p[0]-t0)/6)*cv.width,y=8+cv.height-16-(p[c]/4095)*(cv.height-16);
   if(!started){ctx.moveTo(x,y);started=true;}else ctx.lineTo(x,y);});
  ctx.stroke();}
}
async function tick(){
 try{const r=await fetch('/data');data=await r.json();
  const now=Date.now()/1000,cur=data[data.length-1];
  const last1s=data.filter(p=>now-p[0]<1).length;
  if(cur){
   document.getElementById('curL').textContent=cur[1];
   document.getElementById('curR').textContent=cur.length>2?cur[2]:'—';}
  let m='数据率 '+last1s+' 点/s（应≈70-100）｜窗口 6s';
  const nch=cur?cur.length-1:0;
  for(let c=1;c<=nch;c++){
   const vals=data.map(p=>p[c]);
   m+='｜'+NAMES[c]+' min='+Math.min(...vals)+' max='+Math.max(...vals);}
  m+='（反逻辑：空载≈4095，受压下掉）';
  document.getElementById('meta').textContent=m;
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
    """串口/BLE 共用：一行 "ms,a[,b]" → 进 buf（墙上时间戳 + 各通道值）+ 录制落盘。"""
    if len(RAW) == 0 or RAW[-1] != s:
        RAW.append(s[:60])
    parts = s.split(",")
    if len(parts) >= 2 and all(p.isdigit() for p in parts[1:]):
        vals = [int(p) for p in parts[1:]]
        buf.append((time.time(), *vals))
        if REC["file"] is not None:
            REC["file"].write(s + "\n")
            REC["count"] += 1


def split_chunks(pending, buf):
    """字节流 → 按行喂 feed_line，返回剩余不完整行。"""
    while b"\n" in pending:
        line, pending = pending.split(b"\n", 1)
        feed_line(line.decode("utf-8", "ignore").strip(), buf)
    return pending


def reader(buf):  # 串口数据源（默认）
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

    http.server.HTTPServer((os.environ.get("FSR_HOST", "127.0.0.1"), HTTP_PORT), H).serve_forever()


def main():
    buf = collections.deque(maxlen=3000)
    if "--ble" in sys.argv[1:]:
        threading.Thread(target=ble_main, args=(buf,), daemon=True).start()
    else:
        threading.Thread(target=reader, args=(buf,), daemon=True).start()
    log("server starting on %d (source: %s)" % (HTTP_PORT, "ble" if "--ble" in sys.argv[1:] else "serial"))
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
