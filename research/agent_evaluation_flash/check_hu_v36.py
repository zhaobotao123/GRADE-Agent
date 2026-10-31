from pathlib import Path
import hashlib,json
from PIL import Image,ImageChops
BASE=Path(__file__).resolve().parents[1]
old=BASE/'outputs/submission_audit_v35_20261028/render'
new=BASE/'outputs/hu_publication_v36_20261028/render'
changed=[];same=[]
for p in sorted(new.glob('page-*.png')):
 q=old/p.name
 if q.exists()and Image.open(q).size==Image.open(p).size and ImageChops.difference(Image.open(p).convert('RGB'),Image.open(q).convert('RGB')).getbbox()is None:same.append(p.name)
 else:changed.append(p.name)
print(json.dumps({'same':same,'changed':changed},indent=2))
(new.parent/'page_comparison.json').write_text(json.dumps({'same':same,'changed':changed},indent=2),encoding='utf-8')
