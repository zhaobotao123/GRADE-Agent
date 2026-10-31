from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parent
import json
record=json.loads((ROOT/'manuscript_change_log.json').read_text(encoding='utf-8'))
renderer='C:/Users/84130/.codex/plugins/cache/openai-primary-runtime/documents/26.1025.11240/skills/documents/render_docx.py'
subprocess.run([sys.executable,renderer,record['output'],'--output_dir',str(ROOT/'render_v39'),'--emit_pdf'],check=True)
