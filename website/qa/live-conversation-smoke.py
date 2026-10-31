"""Small synthetic local smoke check; not part of the historical experiments."""
import argparse,json,time,urllib.request,urllib.error
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--provider',choices=['zhipu','deepseek'],default='zhipu')
args=parser.parse_args()
url='http://127.0.0.1:5181/api/chat';history=[];results=[]
inputs=[
 '孩子最近数学成绩下降了，我不知道该关注什么。',
 '最近三次测验逐渐下降。他跟着老师的例题能做，自己换一道相似题就不知道怎么开始，错了会等提示。课堂比较安静，老师是在第一次低分之后才增加辅导。',
 '我想补充：最近两周睡得比较晚，早上有时很困；前面说的独立做题困难仍然存在。',
 '目前就知道这些，能先用一小段话总结一下我该关注什么、先怎么做吗？',
 '你说的逐步减少提示，具体可以怎么做？举一个做数学题时的例子就好。',
]
for index,text in enumerate(inputs,1):
 history.append({'role':'user','content':text})
 request=urllib.request.Request(url,data=json.dumps({'messages':history},ensure_ascii=False).encode(),headers={'Content-Type':'application/json'},method='POST')
 for attempt in range(5):
  try:
   with urllib.request.urlopen(request,timeout=180) as response:result=json.load(response)
   break
  except urllib.error.HTTPError as error:
   if error.code!=429 or attempt==4:
    print('HTTP_ERROR '+str(error.code)+' '+error.read().decode('utf-8',errors='replace'),flush=True)
    raise
   time.sleep(5*(attempt+1))
 assert isinstance(result.get('reply'),str) and result['reply']
 assert result.get('provider')==args.provider
 assert ('glm-4.5-flash' if args.provider=='zhipu' else 'deepseek') in result.get('model','')
 assert not any(k in result for k in ['assessment','report','riskLevel','evidenceCompleteness'])
 history.append({'role':'assistant','content':result['reply']});results.append({'step':index,'user':text,'result':result})
 print(json.dumps({'step':index,'phase':result['phase'],'reply':result['reply'],'model':result['model']},ensure_ascii=False),flush=True)
 time.sleep(3)
assert results[0]['result']['phase']=='question'
assert results[3]['result']['phase']=='summary'
# A practical answer may include one relevant follow-up; do not force it into
# the summary phase merely because it comes after a summary.
assert results[4]['result']['phase'] in ('question','summary')
assert len(results[4]['result']['reply'])>=60
assert results[1]['result']['reply']!=results[2]['result']['reply']
out=Path('qa/conversation-summary-smoke-'+args.provider+'-local.json')
out.write_text(json.dumps({'purpose':'Synthetic development smoke test, excluded from all paper experiments','production_deployed':False,'turns':results},ensure_ascii=False,indent=2),encoding='utf-8')
print('LIVE_SMOKE_PASSED')
