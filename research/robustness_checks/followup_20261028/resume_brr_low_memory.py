"""Operational-only resume: uncompressed atomic NPZ avoids compression buffer.
All frozen statistical code and settings remain unchanged.
"""
import os,uuid,runpy,gc
from pathlib import Path
import common
import resume_brr

original_savez=common.np.savez
def uncompressed_atomic(path,*args,**kwargs):
    path=Path(path)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp.npz')
    gc.collect()
    original_savez(temporary,*args,**kwargs)
    for attempt in range(121):
        try:
            os.replace(temporary,path)
            return
        except PermissionError:
            if attempt==120:raise
            common.time.sleep(.25)

common.np.savez_compressed=uncompressed_atomic
if __name__=='__main__':
    runpy.run_path(str(common.ROOT/'full_refit_brr.py'),run_name='__main__')
