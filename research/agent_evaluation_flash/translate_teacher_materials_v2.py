"""Reading-aid translation only. Experimental generations are never rewritten."""
import json,hashlib,sys,time,subprocess,getpass
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path('C:/Users/84130/Documents/Codex/2026-08-09/zh/outputs/teacher_comparison_bilingual_v2_20261027')
SOURCE=Path('D:/pisa2022/outputs_grade_agent_english_comparison_v2_20261027')
ENGLISH=Path('C:/Users/84130/Documents/Codex/2026-08-09/zh/outputs/teacher_comparison_english_v2_20261027')
PROMPT='''Translate English educational case facts and assistant replies into faithful simplified Chinese. This is a reading aid for independent evaluation, not a rewrite. Preserve every claim, qualification, uncertainty, time order, recommendation and error. Do not improve, correct, soften, strengthen, summarize or score any reply. Preserve distinction between unknown and absent, possibility and certainty, association and causation. Do not add explanations or infer case facts. Translate each item independently; do not transfer details between items. Keep paragraph boundaries and quoted phrases as appropriate. Return JSON only: {"translations":{"opaque_id":"complete Chinese translation"}} with exactly the input IDs and no commentary.'''
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)
class Redirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  if urlparse(newurl).scheme!='https' or urlparse(newurl).hostname!='api.deepseek.com':raise RuntimeError('Cross-origin redirect refused')
  return super().redirect_request(req,fp,code,msg,headers,newurl)
def inputs():
 rows=json.loads((SOURCE/'final_replies.json').read_text(encoding='utf-8'));cases=json.loads((SOURCE/'protocol_lock.json').read_text(encoding='utf-8'))['plan']['cases']
 records=[]
 for i,c in enumerate(cases,1):records.append({'id':f'C{i:03d}','source_id':c['case_id'],'kind':'case','english':'\n'.join(c['facts'].values())})
 for i,r in enumerate(sorted(rows,key=lambda r:r['job']['id']),1):records.append({'id':f'T{i:03d}','source_id':r['job']['id'],'kind':'reply','english':r['final_reply']})
 return records
def batch_translate(index,items,key):
 target=ROOT/'translation_records'/f'batch_{index:03d}.json'
 if target.exists():return json.loads(target.read_text(encoding='utf-8'))
 payload={'model':'deepseek-flash','messages':[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps({r['id']:r['english'] for r in items},ensure_ascii=False)}],'response_format':{'type':'json_object'},'thinking':{'type':'disabled'},'temperature':0,'max_tokens':4500,'stream':False}
 for attempt in range(4):
  request=Request('https://api.deepseek.com/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'GRADE-Agent-Translation/1.0'})
  try:
   with build_opener(Redirect()).open(request,timeout=150) as response:data=json.load(response)
   save(ROOT/'translation_api'/f'batch_{index:03d}_attempt_{attempt+1:02d}.json',{'request':payload,'response':data})
   choice=data['choices'][0];assert choice['finish_reason']=='stop','Incomplete translation'
   translated=json.loads(choice['message']['content'])['translations']
   assert set(translated)=={r['id'] for r in items},'IDs do not match'
   assert all(isinstance(v,str) and v.strip() for v in translated.values()),'Empty translation'
   result=[{**r,'chinese':translated[r['id']],'source_sha256':hashlib.sha256(r['english'].encode()).hexdigest(),'translation_model':data.get('model'),'status':'AI_translation_pending_human_verification'} for r in items]
   save(target,result);return result
  except (HTTPError,URLError,TimeoutError) as error:
   save(ROOT/'translation_api'/f'batch_{index:03d}_error_{attempt+1:02d}.json',{'type':type(error).__name__,'code':getattr(error,'code',None)})
   if isinstance(error,HTTPError) and error.code not in (429,500,502,503,504):raise
   if attempt==3:raise
   time.sleep(5*2**attempt)
 raise RuntimeError('Translation attempts exhausted')
def main():
 ROOT.mkdir(parents=True,exist_ok=True)
 if '--launch' in sys.argv:
  assert sys.stdin.isatty();key=getpass.getpass('DeepSeek translation credential (hidden): ')
  with (ROOT/'stdout.log').open('ab') as out,(ROOT/'stderr.log').open('ab') as err:
   p=subprocess.Popen([sys.executable,'-X','utf8',str(Path(__file__)),'--run'],stdin=subprocess.PIPE,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
   p.stdin.write((key+'\n').encode());p.stdin.close()
  key=None;print('Translation worker PID='+str(p.pid));return
 key=sys.stdin.readline().strip();assert key
 records=inputs();save(ROOT/'internal/translation_manifest.json',{'purpose':'AI-generated Chinese reading aids, not new experiment outputs or teacher ratings','items':records,'prompt':PROMPT})
 groups=[records[i:i+4] for i in range(0,len(records),4)];all_rows=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  pending={pool.submit(batch_translate,i+1,g,key):i+1 for i,g in enumerate(groups)}
  for future in as_completed(pending):
   all_rows.extend(future.result());save(ROOT/'status.json',{'translated':len(all_rows),'planned':len(records),'status':'translating'});print(f'{len(all_rows)}/{len(records)} translated',flush=True)
 save(ROOT/'internal/translations.json',all_rows);save(ROOT/'status.json',{'translated':len(all_rows),'planned':len(records),'status':'translation_completed_pending_material_packaging'})
 key=None
if __name__=='__main__':main()
