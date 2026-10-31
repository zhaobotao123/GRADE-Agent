"""Operational retry wrapper; leaves locked statistical code unchanged."""
import gc
import json
import os
import time
import uuid
import run_weight_loco as job

original_atomic=job.atomic

def resilient_atomic(path,obj):
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    for attempt in range(120):
        try:
            os.replace(temp,path)
            if path.parent.name=='checkpoints': gc.collect()
            return
        except PermissionError:
            if attempt==119: raise
            time.sleep(.25)

job.atomic=resilient_atomic

if __name__=='__main__':
    try: job.main()
    except Exception as exc:
        resilient_atomic(job.OUT/'failure.json',{'time_utc':job.now(),'error':str(exc),'type':type(exc).__name__})
        raise
