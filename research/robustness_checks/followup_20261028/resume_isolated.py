"""Release all native allocations after each new replicate via process isolation.
No changes to frozen estimators, data, weights, folds, pooling or checkpoints.
"""
from pathlib import Path
import sys,os,subprocess,json,time,runpy
ROOT=Path(__file__).resolve().parent
def count():return len(list((ROOT/'BRR_checkpoints').glob('*.json')))
if '--child' in sys.argv:
    import common
    import resume_brr_low_memory
    initial=count();original_progress=common.progress
    def bounded_progress(stage,**kw):
        original_progress(stage,**kw)
        if stage=='replication_complete' and count()>initial:
            raise SystemExit(0)
    common.progress=bounded_progress
    runpy.run_path(str(ROOT/'full_refit_brr.py'),run_name='__main__')
else:
    retries=0
    while True:
        previous=count()
        print(f'Isolated supervisor: {previous}/405 completed',flush=True)
        with (ROOT/'isolated_children.log').open('a',encoding='utf-8')as out:
            result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--child'],stdout=out,stderr=subprocess.STDOUT)
        if result.returncode!=0:
            failure=ROOT/'failure_BRR.json'
            if failure.exists():
                destination=ROOT/'execution_history'/f'failure_isolated_{time.time_ns()}.json'
                os.replace(failure,destination)
            retries+=1
            if retries>=3:raise RuntimeError('Three child failures; inspect isolated_children.log and execution_history')
            time.sleep(2)
            continue
        retries=0
        if previous==405:
            # With no new checkpoint the original worker runs through final pooling.
            break
        assert count()>previous,'No new checkpoint; stop instead of silently looping'
    subprocess.run([sys.executable,'-X','utf8',str(ROOT/'audit_followup.py')],check=True)
    print('405/405 computations and independent audit complete.',flush=True)
