#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小礼品设计在线投票程序 (云就绪版: 本地 SQLite / 云端自动切 Postgres)
零依赖部署：python vote_app.py 即可运行；部署到 Render 时通过 DATABASE_URL 自动切换数据库。
"""
import json, os, sqlite3, uuid, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE, "gift_images")
OPTIONS_FILE = os.path.join(BASE, "options.json")
DB_FILE = os.path.join(BASE, "votes.db")
PORT = int(os.environ.get("PORT", 8765))   # 云平台通过环境变量注入端口
MAX_CHOICES = 4  # 每人最多选几种

# ---------- 数据库抽象 (SQLite / Postgres 自动切换) ----------
try:
    import psycopg2
    PG_AVAILABLE = True
except Exception:
    PG_AVAILABLE = False

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_PG = PG_AVAILABLE and DATABASE_URL.startswith("postgres")
PLACE = "%s" if USE_PG else "?"   # Postgres 用 %s，SQLite 用 ?

if USE_PG:
    print("[DB] 使用 Postgres (云端)")
else:
    print("[DB] 使用 SQLite (本地), 如需云端请把 DATABASE_URL 指向 Postgres")

def get_conn():
    if USE_PG:
        c = psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=10)
        c.autocommit = False
        return c
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    c = get_conn()
    try:
        cur = c.cursor()
        if USE_PG:
            cur.execute("""CREATE TABLE IF NOT EXISTS votes(
                id SERIAL PRIMARY KEY,
                voter_name TEXT,
                choices TEXT,
                token TEXT UNIQUE,
                created_at TEXT)""")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS votes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voter_name TEXT,
                choices TEXT,
                token TEXT UNIQUE,
                created_at TEXT)""")
        c.commit()
    finally:
        c.close()

init_db()

# ---------- 选项数据 ----------
with open(OPTIONS_FILE, encoding="utf-8") as f:
    OPTIONS = json.load(f)
OPT_IDS = {o["id"] for o in OPTIONS}
OPT_NAME = {o["id"]: o["name"] for o in OPTIONS}

# ---------- 结果汇总 ----------
def get_results():
    c = get_conn()
    try:
        cur = c.cursor()
        cur.execute("SELECT choices FROM votes")
        rows = cur.fetchall()
        counts = {oid: 0 for oid in OPT_IDS}
        for (ch,) in rows:
            for cid in json.loads(ch):
                if cid in counts:
                    counts[cid] += 1
        cur.execute("SELECT COUNT(*) FROM votes")
        total_voters = cur.fetchone()[0]
        per = sorted(
            [{"id": o["id"], "name": o["name"], "votes": counts[o["id"]]}
             for o in OPTIONS],
            key=lambda x: (-x["votes"], x["id"]))
        cur.execute("SELECT voter_name, choices, created_at FROM votes ORDER BY id DESC LIMIT 12")
        recent = [{"name": r[0], "choices": json.loads(r[1]), "time": r[2]} for r in cur.fetchall()]
        return {"total_voters": total_voters, "per_option": per, "recent": recent}
    finally:
        c.close()

# ---------- 前端页面 ----------
VOTE_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>小礼品设计投票</title>
<style>
 *{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,"Microsoft YaHei",sans-serif}
 body{background:#f4f6f9;color:#222;padding:20px}
 .wrap{max-width:960px;margin:0 auto}
 header{background:#2b5cff;color:#fff;border-radius:14px;padding:22px 26px;margin-bottom:18px}
 header h1{font-size:22px;margin-bottom:6px}
 header p{opacity:.9;font-size:14px}
 .tip{background:#fff7e6;border:1px solid #ffd591;color:#ad6800;
      padding:10px 14px;border-radius:10px;font-size:14px;margin-bottom:16px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
 .card{background:#fff;border:2px solid #e6e9ef;border-radius:12px;overflow:hidden;
       cursor:pointer;transition:.15s;position:relative}
 .card:hover{border-color:#91a7ff}
 .card.sel{border-color:#2b5cff;box-shadow:0 4px 14px rgba(43,92,255,.18)}
 .card img{width:100%;height:150px;object-fit:cover;background:#f0f0f0;display:block}
 .card .ph{width:100%;height:150px;display:flex;align-items:center;justify-content:center;
           background:#eef1f6;color:#9aa3b2;font-size:13px}
 .card .body{padding:12px 14px}
 .card .nm{font-weight:700;font-size:15px;margin-bottom:4px}
 .card .ds{font-size:12px;color:#6b7280;line-height:1.5}
 .card .pr{margin-top:6px;font-size:13px;color:#d4380d;font-weight:600}
 .card .ck{position:absolute;top:8px;right:8px;width:24px;height:24px;border-radius:50%;
           background:rgba(255,255,255,.85);border:2px solid #c9cfdb;display:flex;
           align-items:center;justify-content:center;font-size:14px;color:transparent}
 .card.sel .ck{background:#2b5cff;border-color:#2b5cff;color:#fff}
 .bar{position:sticky;bottom:0;background:#fff;border-top:1px solid #e6e9ef;
       padding:14px 16px;margin-top:18px;border-radius:12px;display:flex;gap:12px;
       align-items:center;flex-wrap:wrap}
 .name-in{flex:1;min-width:160px;padding:10px 12px;border:1px solid #d0d5dd;border-radius:8px;font-size:14px}
 button{padding:11px 22px;border:0;border-radius:8px;background:#2b5cff;color:#fff;
        font-size:15px;font-weight:600;cursor:pointer}
 button:disabled{background:#b9c2d6;cursor:not-allowed}
 .count{font-size:14px;color:#555}
 .done{text-align:center;padding:40px 20px}
 .done h2{color:#237804;margin-bottom:10px}
 a{color:#2b5cff}
</style></head>
<body><div class="wrap">
 <header><h1>小礼品设计投票</h1><p>请为你喜欢的礼品方案投票 · 每人可选 1–__MAX__ 种</p></header>
 <div class="tip">提示：勾选礼品卡片即可多选，填写你的名字后提交。提交后可在结果页查看实时汇总。</div>
 <div class="grid" id="grid"></div>
 <div class="bar">
   <input class="name-in" id="vname" placeholder="请输入你的名字（必填）">
   <span class="count" id="cnt">已选 0 / __MAX__</span>
   <button id="submit" disabled>提交投票</button>
 </div>
</div>
<script>
const MAX=__MAX__, OPTS=__OPTS__;
const sel=new Set();
const grid=document.getElementById('grid');
OPTS.forEach(o=>{
 const c=document.createElement('div'); c.className='card';
 const img = o.image
   ? `<img src="/images/${o.image}" alt="">`
   : `<div class="ph">暂无参考图</div>`;
 c.innerHTML=`${img}<div class="ck">✓</div>
   <div class="body"><div class="nm">${o.name}</div>
   <div class="ds">${o.desc||''}${o.material?'<br>材质：'+o.material:''}</div>
   ${o.price_text?`<div class="pr">${o.price_text}</div>`:''}</div>`;
 c.onclick=()=>{
   if(sel.has(o.id)){sel.delete(o.id);c.classList.remove('sel');}
   else{if(sel.size>=MAX){alert('最多选 '+MAX+' 种');return;}sel.add(o.id);c.classList.add('sel');}
   document.getElementById('cnt').textContent='已选 '+sel.size+' / '+MAX;
   document.getElementById('submit').disabled=!(sel.size>=1&&sel.size<=MAX&&document.getElementById('vname').value.trim());
 };
 grid.appendChild(c);
});
document.getElementById('vname').oninput=e=>{
 document.getElementById('submit').disabled=!(sel.size>=1&&sel.size<=MAX&&e.target.value.trim());
};
document.getElementById('submit').onclick=async()=>{
 const name=document.getElementById('vname').value.trim();
 if(!name){alert('请填写名字');return;}
 const token=localStorage.getItem('vt_'+name); // 防同一人重复投
 const body=JSON.stringify({name,choices:[...sel],token:token||null});
 const r=await fetch('/api/vote',{method:'POST',headers:{'Content-Type':'application/json'},body});
 const d=await r.json();
 if(!d.ok){alert(d.msg);return;}
 localStorage.setItem('vt_'+name, d.token);
 document.body.innerHTML='<div class="wrap"><div class="done"><h2>✓ 投票成功，谢谢！</h2>'
   +'<p>你选择了：'+d.choices.map(id=>OPTS.find(o=>o.id==id).name).join('、')+'</p>'
   +'<p style="margin-top:14px"><a href="/results">查看实时结果 →</a></p></div></div>';
};
</script></body></html>"""

RESULTS_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>投票结果汇总</title>
<style>
 *{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,"Microsoft YaHei",sans-serif}
 body{background:#f4f6f9;color:#222;padding:20px}
 .wrap{max-width:820px;margin:0 auto}
 header{background:#237804;color:#fff;border-radius:14px;padding:20px 26px;margin-bottom:18px}
 header h1{font-size:22px}
 header .sub{opacity:.9;font-size:14px;margin-top:4px}
 .live{display:inline-block;width:9px;height:9px;border-radius:50%;background:#52c41a;
       margin-right:6px;animation:bl 1s infinite}@keyframes bl{50%{opacity:.3}}
 .panel{background:#fff;border-radius:12px;padding:18px 20px;margin-bottom:16px}
 .row{display:flex;align-items:center;margin:10px 0;gap:10px}
 .row .nm{width:160px;font-size:14px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .track{flex:1;background:#eef1f6;border-radius:6px;height:26px;position:relative;overflow:hidden}
 .fill{height:100%;background:linear-gradient(90deg,#40a9ff,#2b5cff);border-radius:6px;transition:width .6s}
 .row .v{width:60px;text-align:right;font-weight:700;font-size:14px}
 .recent{font-size:13px;color:#555}
 .recent div{padding:5px 0;border-bottom:1px dashed #eee}
 a{color:#2b5cff}
 .exp{display:inline-block;margin-top:10px;padding:8px 16px;background:#237804;color:#fff;
      border-radius:8px;font-size:14px;text-decoration:none}
</style></head>
<body><div class="wrap">
 <header><h1>投票结果实时汇总</h1>
   <div class="sub"><span class="live"></span>参与人数：<b id="tv">0</b> 人 · 每 5 秒自动刷新 · <a href="/" style="color:#fff;text-decoration:underline">返回投票</a></div></header>
 <div class="panel" id="board"></div>
 <div class="panel"><h3 style="margin-bottom:8px">最近投票</h3><div class="recent" id="recent"></div>
   <a class="exp" href="/api/export">↓ 导出结果 CSV</a></div>
</div>
<script>
async function load(){
 const d=await (await fetch('/api/results')).json();
 document.getElementById('tv').textContent=d.total_voters;
 const max=Math.max(1,...d.per_option.map(o=>o.votes));
 document.getElementById('board').innerHTML=d.per_option.map(o=>
   `<div class="row"><div class="nm" title="${o.name}">${o.name}</div>
    <div class="track"><div class="fill" style="width:${o.votes/max*100}%"></div></div>
    <div class="v">${o.votes}</div></div>`).join('');
 document.getElementById('recent').innerHTML=d.recent.length?d.recent.map(r=>
   `<div>${r.time.slice(5)} · <b>${r.name}</b> 投了 ${r.choices.length} 项</div>`).join('')
   :'<div>暂无投票</div>';
}
load(); setInterval(load,5000);
</script></body></html>"""

# ---------- HTTP 处理 ----------
class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8") if isinstance(body, str) else body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/" or u.path == "/index.html":
            self._send(200, VOTE_HTML.replace("__MAX__", str(MAX_CHOICES))
                       .replace("__OPTS__", json.dumps(OPTIONS, ensure_ascii=False)),
                       "text/html; charset=utf-8")
        elif u.path == "/results":
            self._send(200, RESULTS_HTML, "text/html; charset=utf-8")
        elif u.path == "/api/options":
            self._send(200, json.dumps(OPTIONS, ensure_ascii=False))
        elif u.path == "/api/results":
            self._send(200, json.dumps(get_results(), ensure_ascii=False))
        elif u.path == "/api/export":
            self._export_csv()
        elif u.path.startswith("/images/"):
            fn = os.path.basename(u.path)
            fp = os.path.join(IMG_DIR, fn)
            if os.path.exists(fp):
                with open(fp, "rb") as f:
                    self._send(200, f.read(), "image/png")
            else:
                self._send(404, "not found")
        else:
            self._send(404, "not found")

    def _export_csv(self):
        c = get_conn()
        try:
            cur = c.cursor()
            cur.execute("SELECT voter_name, choices, created_at FROM votes ORDER BY id")
            rows = cur.fetchall()
        finally:
            c.close()
        lines = ["投票人,投票时间,选择的礼品"]
        for name, ch, ts in rows:
            names = "、".join(OPT_NAME.get(i, str(i)) for i in json.loads(ch))
            lines.append(f"{name},{ts},{names}")
        csv = "\ufeff" + "\n".join(lines)  # BOM 让 Excel 正确识别中文
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=gift_vote_results.csv")
        self.end_headers()
        self.wfile.write(csv.encode("utf-8"))

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/vote":
            try:
                ln = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(ln).decode("utf-8"))
            except Exception:
                self._send(400, json.dumps({"ok": False, "msg": "数据格式错误"}))
                return
            name = (data.get("name") or "").strip()
            choices = data.get("choices") or []
            token = data.get("token")
            if not name:
                self._send(200, json.dumps({"ok": False, "msg": "请填写名字"}))
                return
            if not isinstance(choices, list) or not (1 <= len(choices) <= MAX_CHOICES):
                self._send(200, json.dumps({"ok": False, "msg": f"请选择 1–{MAX_CHOICES} 种礼品"}))
                return
            try:
                choices = [int(x) for x in choices]
            except Exception:
                self._send(200, json.dumps({"ok": False, "msg": "选项非法"}))
                return
            if any(c not in OPT_IDS for c in choices):
                self._send(200, json.dumps({"ok": False, "msg": "包含无效选项"}))
                return
            c = get_conn()
            try:
                cur = c.cursor()
                cur.execute(f"SELECT 1 FROM votes WHERE voter_name={PLACE}", (name,))
                if cur.fetchone():
                    self._send(200, json.dumps({"ok": False, "msg": "该名字已投过票"}))
                    c.close()
                    return
                new_token = token or str(uuid.uuid4())
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute(
                    f"INSERT INTO votes(voter_name,choices,token,created_at) VALUES({PLACE},{PLACE},{PLACE},{PLACE})",
                    (name, json.dumps(choices), new_token, now))
                c.commit()
            except Exception:
                c.rollback()
                self._send(200, json.dumps({"ok": False, "msg": "请勿重复提交"}))
                c.close()
                return
            c.close()
            self._send(200, json.dumps({"ok": True, "token": new_token, "choices": choices}))
        else:
            self._send(404, json.dumps({"ok": False, "msg": "not found"}))

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    print(f"投票服务已启动: http://0.0.0.0:{PORT}  (结果页 /results)")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
