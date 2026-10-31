"""Hidden terminal credential input; worker receives it only on a process pipe."""
import argparse,getpass,subprocess,sys
from pathlib import Path

parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group();mode.add_argument('--recovery',action='store_true');mode.add_argument('--semantic',action='store_true');mode.add_argument('--semantic-schema-recovery',type=int);mode.add_argument('--teacher-summaries',action='store_true');args=parser.parse_args()
if not sys.stdin.isatty():raise RuntimeError('A private interactive terminal is required; refusing echoed credential input.')
key=getpass.getpass('Runtime API credential (hidden): ')
if not key:raise RuntimeError('No credential entered.')
root=Path('D:/pisa2022/outputs_grade_agent_deepseek41flash300_20261026')
assert root.is_dir()
worker=Path(__file__).with_name('build_teacher_summary_v2.py' if args.teacher_summaries else ('recover_semantic_schema.py' if args.semantic_schema_recovery else ('semantic_review300.py' if args.semantic else ('recover_deepseek300_transport.py' if args.recovery else 'run_deepseek300_locked.py'))))
log_prefix='teacher_summaries' if args.teacher_summaries else ('semantic_schema_recovery' if args.semantic_schema_recovery else ('semantic_review' if args.semantic else ('transport_recovery' if args.recovery else 'worker')))
command=[sys.executable,'-X','utf8',str(worker)]+(['--wait-pid',str(args.semantic_schema_recovery)] if args.semantic_schema_recovery else ([] if args.recovery else ['--run']))
with (root/(log_prefix+'_stdout.log')).open('ab') as stdout,(root/(log_prefix+'_stderr.log')).open('ab') as stderr:
    p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,
        cwd=str(Path(__file__).parent.parent),creationflags=subprocess.CREATE_NO_WINDOW)
    p.stdin.write((key+'\n').encode('utf-8'));p.stdin.flush();p.stdin.close()
key=None
print('Background worker started. PID='+str(p.pid),flush=True)
