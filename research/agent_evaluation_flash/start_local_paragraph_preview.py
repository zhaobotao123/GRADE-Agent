"""Launch the local Zhipu conversation preview with memory-only credentials."""
import argparse,getpass,json,subprocess,sys
from pathlib import Path
assert sys.stdin.isatty(),'Private interactive credential input required'
parser=argparse.ArgumentParser()
parser.add_argument('--provider',choices=['zhipu','deepseek'],default='zhipu')
args=parser.parse_args()
key=getpass.getpass(args.provider+' runtime credential (hidden): ')
assert key
project=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/gradeagent')
logs=Path('C:/Users/84130/Documents/Codex/2026-08-09/zh/work/paragraph_backup_20261027')
node='C:/Users/84130/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
with (logs/'preview_stdout.log').open('ab') as out,(logs/'preview_stderr.log').open('ab') as err:
 p=subprocess.Popen([node,'qa/local-consultation-server.mjs'],cwd=project,stdin=subprocess.PIPE,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 p.stdin.write((json.dumps({'provider':args.provider,'apiKey':key})+'\n').encode());p.stdin.close()
key=None
print('Local preview worker PID='+str(p.pid))
