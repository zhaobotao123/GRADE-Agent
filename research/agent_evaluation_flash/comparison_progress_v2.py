"""Loopback-only read-only experiment status; never serves raw files or keys."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json
ROOT=Path('D:/pisa2022/outputs_grade_agent_english_comparison_v2_20261027')
PAGE='''<!doctype html><meta charset="utf-8"><title>English comparison v2 progress</title><style>body{font:17px system-ui;background:#f4f7f5;color:#183c30;max-width:850px;margin:50px auto;padding:24px}section{background:white;border-radius:16px;padding:25px;margin:18px 0}progress{width:100%;height:25px}pre{white-space:pre-wrap}small{color:#5e6c64}</style><h1>English conversation comparison · v2</h1><p>GRADE-Agent vs ordinary DeepSeek Flash · 12 cases × 2 systems × 5 runs = 120 conversations</p><section><h2 id="stage">Loading…</h2><progress id="bar" max="120" value="0"></progress><p id="counts"></p><p id="groups"></p><small id="updated"></small></section><section><strong>What this means</strong><p>Each conversation has four user turns. Both systems receive identical staged case information and produce English replies. Connection pilots are excluded from the 120 conversations.</p><p>These are generation counts, not quality scores. Independent teacher evaluation is pending. No winner has been assigned.</p></section><pre id="detail"></pre><script>async function refresh(){try{let r=await fetch('/status',{cache:'no-store'}),s=await r.json();document.getElementById('stage').textContent=s.status;document.getElementById('bar').value=s.completed+s.failed;document.getElementById('counts').textContent=`Completed: ${s.completed} | Failed: ${s.failed} | Active: ${s.active} | Remaining: ${s.remaining}`;document.getElementById('groups').textContent=`Ordinary LLM: ${s.by_system.ordinary_llm}/60 | GRADE-Agent: ${s.by_system.grade_agent}/60`;document.getElementById('updated').textContent='Updated: '+s.updated_utc;document.getElementById('detail').textContent=(s.note||'')+' | Language flags: '+(s.language_flagged_conversations||0);}catch(e){document.getElementById('stage').textContent='Waiting for local status…';}}refresh();setInterval(refresh,3000);</script>'''
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path=='/':body=PAGE.encode();kind='text/html; charset=utf-8'
  elif self.path=='/status':
   p=ROOT/'status.json';data=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
   if not (ROOT/'pilot_check.json').exists():data['status']='connection_pilots_running';data['note']='Both four-turn pilot conversations must succeed before formal generation begins.'
   if (ROOT/'worker_failure.json').exists():data['note']='Worker stopped; inspect the local error record. No results were silently replaced.'
   body=json.dumps(data).encode();kind='application/json'
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8769),Handler).serve_forever()
