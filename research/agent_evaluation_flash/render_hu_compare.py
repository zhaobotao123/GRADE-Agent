from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]/'outputs/hu_grade_comparison_20261028'
pdf='D:/微信/xwechat_files/wxid_lhoxzs8swzbs22_7edd/msg/file/2026-10/2026 Studies in Educational Evaluation.pdf'
exe='C:/Users/84130/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for n in [1,5,8,9,10]:subprocess.run([exe,'-f',str(n),'-l',str(n),'-r','100','-png','-singlefile',pdf,str(root/f'published_page{n}')],check=True)
