import subprocess,sys
from pathlib import Path
renderer=Path('C:/Users/84130/.codex/plugins/cache/openai-primary-runtime/documents/26.1025.11240/skills/documents/render_docx.py')
source=Path('D:/Users/84130/Desktop/投稿/转投修改_20261022/GRADE-Agent_SEE_Audited_Draft_v33.docx')
subprocess.run([sys.executable,str(renderer),str(source),'--output_dir','outputs/submission_audit_v33_20261028/render','--emit_pdf'],check=True)
