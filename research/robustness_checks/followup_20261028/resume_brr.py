"""Operational resume only: retry Windows transient atomic-replace failures.
Frozen statistical source, input hashes and checkpoint files remain unchanged.
"""
from pathlib import Path
import os,time,json,uuid,runpy
import common

def retry_save(path,obj):
    path=Path(path)
    temporary=path.with_name(path.name+'.'+str(os.getpid())+'.'+uuid.uuid4().hex+'.tmp')
    text=json.dumps(obj,ensure_ascii=False,indent=2,default=str)
    for attempt in range(121):
        try:
            temporary.write_text(text,encoding='utf-8')
            os.replace(temporary,path)
            return
        except PermissionError:
            if attempt==120:raise
            time.sleep(.25)

common.save=retry_save
if __name__=='__main__':
    runpy.run_path(str(common.ROOT/'full_refit_brr.py'),run_name='__main__')
