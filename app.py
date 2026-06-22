#!/usr/bin/env python3
# ============================================================
#  Claude Quota Cloud Bridge  —  สำหรับ deploy บน Render.com
# ------------------------------------------------------------
#  - ใช้ไลบรารีมาตรฐานล้วน (ไม่ต้อง pip install)
#  - bind พอร์ตตาม $PORT ที่ Render กำหนดให้
#  - เก็บค่าลงไฟล์ quota.json (อยู่ได้ตลอดที่ service รัน)
#
#  Endpoint:
#    GET /quota                      -> {"session":..,"weekly":..,"reset":".."}
#    GET /set?session=&weekly=&reset= -> อัปเดตค่า
#    GET /                           -> หน้าฟอร์มกรอกค่า
# ============================================================

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", "8080"))   # Render กำหนด PORT ให้เอง
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quota.json")
DEFAULT = {"session": 0, "weekly": 0, "reset": "--"}


def load():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return {
            "session": max(0, min(100, int(d.get("session", 0)))),
            "weekly":  max(0, min(100, int(d.get("weekly", 0)))),
            "reset":   str(d.get("reset", "--")),
        }
    except Exception:
        save(DEFAULT)
        return dict(DEFAULT)


def save(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


PAGE = """<!doctype html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Claude Quota</title><style>
body{{font-family:sans-serif;background:#111;color:#eee;max-width:420px;margin:24px auto;padding:0 16px}}
h2{{color:#c878ff}}label{{display:block;margin:14px 0 4px}}
input{{width:100%;padding:10px;font-size:18px;border-radius:8px;border:1px solid #555;background:#222;color:#fff;box-sizing:border-box}}
button{{margin-top:18px;width:100%;padding:14px;font-size:18px;border:0;border-radius:8px;background:#c878ff;color:#111;font-weight:bold}}
.now{{color:#8c8;margin:8px 0}}</style></head><body>
<h2>Claude Quota (Cloud)</h2>
<p class='now'>ตอนนี้: SESSION {s}% / WEEKLY {w}% / reset {r}</p>
<form action='/set' method='get'>
<label>SESSION % (รีเซ็ตทุก 5 ชม.)</label><input type='number' name='session' min='0' max='100' value='{s}'>
<label>WEEKLY %</label><input type='number' name='weekly' min='0' max='100' value='{w}'>
<label>reset in (เช่น 3h 10m)</label><input type='text' name='reset' value='{r}'>
<button type='submit'>บันทึก</button></form>
<p style='color:#777;margin-top:20px'>อ่านค่าจริงจาก Claude &rarr; Settings &rarr; Usage</p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/quota":
            self._send(200, json.dumps(load(), ensure_ascii=False))
        elif u.path == "/set":
            q = parse_qs(u.query)
            d = load()
            if "session" in q: d["session"] = max(0, min(100, int(q["session"][0])))
            if "weekly"  in q: d["weekly"]  = max(0, min(100, int(q["weekly"][0])))
            if "reset"   in q: d["reset"]   = q["reset"][0]
            save(d)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        elif u.path in ("/", "/index.html"):
            d = load()
            self._send(200, PAGE.format(s=d["session"], w=d["weekly"], r=d["reset"]), "text/html")
        elif u.path == "/healthz":
            self._send(200, json.dumps({"ok": True}))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not os.path.exists(DATA_FILE):
        save(DEFAULT)
    print(f"Claude Quota cloud bridge on 0.0.0.0:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
