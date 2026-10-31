from pathlib import Path
from docx import Document
from zipfile import ZipFile
import io,re,json,unicodedata,urllib.request,urllib.parse,concurrent.futures,difflib

BASE=Path('D:/Users/84130/Desktop/投稿/转投修改_20261022')
OUT=Path('outputs/manuscript_revision_v31_20261027')
OUT.mkdir(parents=True,exist_ok=True)
d=Document(BASE/'GRADE-Agent_SEE_NatureSkills_Polished_v30.docx')
ri=next(i for i,p in enumerate(d.paragraphs) if p.text=='References')
body='\n'.join(p.text for p in d.paragraphs[:ri])+'\n'+'\n'.join(c.text for t in d.tables for row in t.rows for c in row.cells)
def normalize(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c)).lower()
nb=normalize(body)
supp=[]
sp=Path('work/GRADE-Agent_Supplementary_Materials.docx')
sd=Document(sp)
supp.append((str(sp),'\n'.join(p.text for p in sd.paragraphs)+'\n'+'\n'.join(c.text for t in sd.tables for row in t.rows for c in row.cells)))
for zp in [BASE/'Supplementary_Evaluation_Materials_v21.zip',Path('D:/Users/84130/Desktop/投稿/GRADE-Agent Source Code.zip')]:
    if not zp.exists():continue
    with ZipFile(zp) as z:
        for name in z.namelist():
            if name.endswith(('.md','.tex','.bib','.ris')) and 'node_modules' not in name:
                supp.append((str(zp)+'::'+name,z.read(name).decode('utf-8',errors='replace')))
def hits(text,author,year):
    nt=normalize(text)
    a=re.escape(normalize(author))
    # Author-year matching spans semicolon-separated parenthetical citations.
    pat=a+r'[^.\n;]{0,100}?'+re.escape(year)
    direct=re.search(pat,nt)
    if direct:return direct.group(0)
    # et al. has a period, handled separately.
    pat=a+r'\s+et al\.\s*[,\(]?\s*'+re.escape(year)
    m=re.search(pat,nt)
    return m.group(0) if m else None
refs=[]
for i,p in enumerate(d.paragraphs[ri+1:],ri+1):
    if not p.text:continue
    t=p.text
    author=t.split(',')[0] if not t.startswith('OECD.') else 'OECD'
    year=re.search(r'\((\d{4}[ab]?|in press)\)',t).group(1)
    h=hits(body,author,year)
    sh=[name for name,tx in supp if hits(tx,author,year)]
    doi=re.search(r'https://doi.org/([^\s]+)',t)
    refs.append({'paragraph':i,'first_author':author,'year':year,'entry':t,'body_match':h,'supplement_matches':sh,'doi':doi.group(1).rstrip('.') if doi else None})
def remote(ref):
    doi=ref['doi']
    if not doi:return {'status':'manual_needed','reason':'No DOI in supplied entry; retained original metadata.'}
    url='https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='')
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'ManuscriptReferenceAudit/1.0 (read-only metadata verification)'})
        with urllib.request.urlopen(req,timeout=25) as r:msg=json.load(r)['message']
        title=msg.get('title',[''])[0]
        journal=msg.get('container-title',[''])[0] if msg.get('container-title') else ''
        dates={key:msg[key]['date-parts'][0][0] for key in ['published','published-print','published-online','issued'] if key in msg and 'date-parts' in msg[key]}
        aa=msg.get('author',[])
        first=aa[0].get('family','') if aa else ''
        metadata={'title':title,'journal':journal,'dates':dates,'first_author':first,'volume':msg.get('volume'),'issue':msg.get('issue'),'pages':msg.get('page'),'article_number':msg.get('article-number')}
        words=lambda s:set(re.findall(r'[a-z0-9]+',normalize(s)))
        overlap=len(words(title)&words(ref['entry']))/max(1,len(words(title)))
        authorok=normalize(first)==normalize(ref['first_author']) or ref['first_author']=='OECD'
        yearok=int(ref['year'][:4]) in dates.values() if ref['year']!='in press' else True
        status='verified_title_author_year' if overlap>.85 and authorok and yearok else 'metadata_review_needed'
        return {'status':status,'metadata':metadata,'title_word_coverage':round(overlap,3),'source':url}
    except Exception as e:
        return {'status':'manual_needed','reason':type(e).__name__+': '+str(e)[:200],'source':url}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    for ref,res in zip(refs,ex.map(remote,refs)):ref['external_metadata']=res
data={'main_reference_count':len(refs),'uncited_main_count':sum(not r['body_match'] for r in refs),'supplement_narrative_sources_checked':[name for name,_ in supp],'scope':'Main-text author-year matches plus available supplementary narrative. Raw generated replies and datasets are not bibliography sources. DOI metadata checks do not verify claim support.','references':refs}
(OUT/'reference_audit.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('References',len(refs),'Uncited main',data['uncited_main_count'])
for r in refs:
    print(r['first_author'],r['year'],'MAIN',bool(r['body_match']),'SUPP',len(r['supplement_matches']),r['external_metadata']['status'])
