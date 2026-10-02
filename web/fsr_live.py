#!/usr/bin/env python3
"""FSR live 波形页 · 零依赖版（无 pyserial/matplotlib）。

MBP 上运行：python3 /tmp/fsr_live.py  → 浏览器 http://localhost:8324/
stty 配好波特率后直读 /dev/cu.usbserial-110，HTTP 服务推 JSON，前端 canvas 画滚动曲线。
自身守护化（双 fork 脱离会话），异常写 /tmp/fsr_live.log。
"""

import base64
import collections
import http.server
import json
import os
import subprocess
import sys
import threading
import time

DEV = "/dev/cu.usbserial-110"
HTTP_PORT = 8324
LOG = "/tmp/fsr_live.log"

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>FSR live · V2 预检</title>
<style>body{margin:0;background:#111;color:#eee;font-family:sans-serif}
#cur{font-size:64px;font-weight:bold;color:#ffd42a}
#meta{font-size:14px;color:#aaa;line-height:1.7}</style></head>
<body>
<div id="cur">--</div>
<canvas id="cv" width="1200" height="400" style="width:99vw"></canvas>
<div id="meta">V2 反逻辑：空载≈4095，受压读数<b>下掉</b>。窗口 6s 滚动，300ms 刷新。</div>
<script>
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
let data=[];
function draw(){
 ctx.fillStyle='#111';ctx.fillRect(0,0,cv.width,cv.height);
 ctx.strokeStyle='#333';ctx.beginPath();ctx.moveTo(0,cv.height/2);ctx.lineTo(cv.width,cv.height/2);ctx.stroke();
 ctx.strokeStyle='#666';[4095,3072,2048,1024,0].forEach(v=>{
  const y=cv.height-(v/4095)*cv.height;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(cv.width,y);ctx.stroke();
  ctx.fillStyle='#555';ctx.font='12px sans-serif';ctx.fillText(v,4,y-3);ctx.fillStyle='#555';});
 if(!data.length)return;
 const t1=Date.now()/1000,t0=t1-6;
 ctx.strokeStyle='#ffd42a';ctx.lineWidth=2;ctx.beginPath();
 data.forEach((p,i)=>{
  const x=((p[0]-t0)/6)*cv.width,y=cv.height-(p[1]/4095)*cv.height;
  i?ctx.lineTo(x,y):ctx.moveTo(x,y);});
 ctx.stroke();
}
async function tick(){
 try{const r=await fetch('/data');data=await r.json();
  const cur=data[data.length-1];
  if(cur)document.getElementById('cur').textContent=cur[1];
  const vals=data.map(p=>p[1]);
  const mn=Math.min(...vals),mx=Math.max(...vals);
  document.getElementById('meta').innerHTML=
   '窗口 min='+mn+' max='+mx+'（当前 '+cur[1]+'）｜V2 反逻辑：空载≈4095，受压读数<b>下掉</b>｜窗口 6s，300ms 刷新';
 }catch(e){}
 draw();
}
setInterval(tick,300);tick();
</script></body></html>"""


def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass


def reader(buf):
    subprocess.run(["stty", "-f", DEV, "115200", "raw", "-crtscts", "-hupcl"])
    while True:
        try:
            f = open(DEV, "rb")
            while True:
                line = f.readline().decode("utf-8", "ignore").strip()
                if "," in line:
                    p = line.split(",")[1]
                    if p.isdigit():
                        buf.append((time.time(), int(p)))
        except Exception as e:
            log("reader error: %r" % e)
            time.sleep(1)


def serve(buf):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/data"):
                body = json.dumps(list(buf)[-800:]).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                body = PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, *a):
            pass

    http.server.HTTPServer(("127.0.0.1", HTTP_PORT), H).serve_forever()


def main():
    buf = collections.deque(maxlen=3000)
    threading.Thread(target=reader, args=(buf,), daemon=True).start()
    log("server starting on %d" % HTTP_PORT)
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
