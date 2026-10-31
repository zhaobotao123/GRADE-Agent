"""Resume cached GLM sessions; retry HTTP429 transport errors only, never content."""
import json,time,uuid
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import run_glm_english_illustration as run

def api(path,key,body=None):
    for attempt in range(3):
        req=Request(run.core.API+path,data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urlopen(req,timeout=150) as response:return json.loads(response.read().decode())
        except HTTPError as exc:
            try:payload=json.loads(exc.read().decode())
            except Exception:payload={}
            err=payload.get('error',{})
            message=str(err.get('message','')).replace(key,'[REDACTED]')
            run.core.save(run.core.ROOT/'transport_events'/f'{uuid.uuid4().hex}.json',
                {'status':exc.code,'provider_code':err.get('code'),'message':message,'timestamp':run.core.now(),
                 'attempt':attempt+1,'content_based_retry':False})
            if exc.code!=429 or str(err.get('code'))=='1113' or attempt==2:
                raise RuntimeError(f'API HTTP {exc.code}, provider code {err.get("code")}; preserved cached responses') from None
            time.sleep(20*(attempt+1))

run.core.api=api
if __name__=='__main__':run.main()
