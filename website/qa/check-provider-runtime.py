"""Print provider status/error codes only; credential remains in hidden input."""
import getpass,json,sys,urllib.request,urllib.error
assert sys.stdin.isatty()
key=getpass.getpass('Zhipu runtime credential (hidden): ')
request=urllib.request.Request('https://open.bigmodel.cn/api/paas/v4/chat/completions',data=json.dumps({'model':'glm-4.5-flash','messages':[{'role':'user','content':'只返回JSON：{"ok":true}'}],'max_tokens':30,'thinking':{'type':'disabled'},'stream':False}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key},method='POST')
try:
 with urllib.request.urlopen(request,timeout=45) as response:
  data=json.load(response);print(json.dumps({'status':response.status,'model':data.get('model'),'finish_reason':data.get('choices',[{}])[0].get('finish_reason')},ensure_ascii=False))
except urllib.error.HTTPError as error:
 data=json.loads(error.read().decode());message=str(data.get('error',{}).get('message','')).replace(key,'[REDACTED]')
 print(json.dumps({'status':error.code,'provider_code':data.get('error',{}).get('code'),'provider_message':message},ensure_ascii=False))
finally:key=None
