"""Hidden credential input; launch experiment without saving credentials."""
import getpass,subprocess,sys
from pathlib import Path
assert sys.stdin.isatty()
root=Path('D:/pisa2022/outputs_grade_agent_english_comparison_20261027');root.mkdir(exist_ok=True,parents=True)
key=getpass.getpass('DeepSeek runtime credential (hidden): ')
assert key
with (root/'worker_stdout.log').open('ab') as out,(root/'worker_stderr.log').open('ab') as err:
 p=subprocess.Popen([sys.executable,'-X','utf8',str(Path(__file__).with_name('run_conversation_comparison.py')),'--run'],stdin=subprocess.PIPE,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 p.stdin.write((key+'\n').encode());p.stdin.close()
key=None
print('Experiment worker PID='+str(p.pid))
