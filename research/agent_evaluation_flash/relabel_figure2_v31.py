"""Re-export the original Python plot with association labels; data unchanged."""
from pathlib import Path
import os,sys,hashlib,json
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
sys.path.insert(0,str(Path('work/figure_python_deps').resolve()))
source=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/work/draw_v8_integrated_figure2.py')
code=source.read_text(encoding='utf-8')
code=code.replace('Adjusted-effect evidence','Adjusted-association evidence')
code=code.replace('"Adjusted-association evidence\\nDML + 95% CI"','"Adjusted-association\\nevidence\\nDML + 95% CI"')
code=code.replace('top=0.90, bottom=0.14','top=0.86, bottom=0.14').replace('hspace=0.32','hspace=0.55')
code=code.replace('axd.set_xlim(0,1)','axd.set_xlim(-0.04,1.02)')
code=code.replace('y+h-0.12), w, 0.12','y+h*0.56), w, h*0.44')
code=code.replace('y+h-0.13), w, 0.07','y+h*0.56), w, h*0.12')
code=code.replace('y+h-0.06, title','y+h*0.78, title').replace('fontsize=5.8, fontweight="bold"','fontsize=5.2, fontweight="bold"')
code=code.replace('y+(h-0.13)/2, body','y+h*0.25, body')
code=code.replace('"Evidence convergence\\n+\\nuncertainty and\\nstability review"','"Evidence\\nconvergence\\n+\\nuncertainty and\\nstability review"')
namespace={'__name__':'_figure2_label_revision_'}
exec(compile(code,str(source),'exec'),namespace)
out=Path('D:/Users/84130/Desktop/投稿/转投修改_20261022/Figures_v31')
out.mkdir(parents=True,exist_ok=True)
namespace['OUT']=out
namespace['STEM']=out/'Figure2_adjusted_associations'
inputs=[namespace[n] for n in ['MODEL','SHAP','DML']]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
namespace['draw']()
assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
qa=Path('outputs/manuscript_revision_v31_20261027')
qa.mkdir(parents=True,exist_ok=True)
(qa/'figure_contract.json').write_text(json.dumps({'claim':'Prediction and adjusted associations provide distinct empirical information; neither alone proves an individual cause.','archetype':'quantitative grid with schematic','backend':'Python','change':'Two effect-label occurrences changed to association; original plotting routine and exact input files retained.','source_data_sha256':hashes,'exports':['png','svg','pdf','tiff'],'font':'Times New Roman','no_new_estimation':True},indent=2),encoding='utf-8')
