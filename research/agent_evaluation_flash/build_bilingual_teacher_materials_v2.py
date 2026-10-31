"""Package bilingual reading aids with the original unchanged rating workbook."""
import json,hashlib,html,shutil,zipfile,re
from pathlib import Path
BASE=Path('C:/Users/84130/Documents/Codex/2026-08-09/zh/outputs')
EN=BASE/'teacher_comparison_english_v2_20261027'
OUT=BASE/'teacher_comparison_bilingual_v2_20261027'
SOURCE=Path('D:/pisa2022/outputs_grade_agent_english_comparison_v2_20261027')
def main():
 translated=json.loads((OUT/'internal/translations.json').read_text(encoding='utf-8'))
 assert len(translated)==132
 corrections=[]
 for item in translated:
  before=item['chinese'];text=before
  text=text.replace('学生账户详情','学生自述的详细信息').replace('学生账户','学生自述').replace('学生账号','学生自述').replace('教牧负责人','学生关怀负责人').replace('保护负责人','学生保护负责人')
  if 'low-stakes' in item['english']:text=text.replace('低风险','低压力')
  if item['id']=='T079':text=text.replace('账户详情','相关叙述的详细信息')
  if item['id']=='T046':text=text.replace('学生何时主动发起 versus 何时需要提示','学生何时能主动开始解题、何时需要提示')
  if text!=before:corrections.append({'id':item['id'],'english':item['english'],'before':before,'after':text,'reviewer':'assistant spot-check, not independent human verification'})
  item['chinese']=text
 (OUT/'internal/translation_corrections.json').write_text(json.dumps(corrections,ensure_ascii=False,indent=2),encoding='utf-8')
 by_id={r['source_id']:r for r in translated};assert len(by_id)==132
 mappings=json.loads((EN/'internal/blinding_key_DO_NOT_SEND.json').read_text(encoding='utf-8'))['mapping']
 originals={r['job']['id']:r['final_reply'] for r in json.loads((SOURCE/'final_replies.json').read_text(encoding='utf-8'))}
 cases={r['case_id']:r for r in json.loads((SOURCE/'protocol_lock.json').read_text(encoding='utf-8'))['plan']['cases']}
 for r in translated:
  assert hashlib.sha256(r['english'].encode()).hexdigest()==r['source_sha256']
  assert re.search('[\u3400-\u9fff]',r['chinese']),r['id']
  assert len(r['chinese'])>30
  if r['kind']=='reply':assert originals[r['source_id']]==r['english']
 checks=[]
 for teacher in (1,2):
  folder=OUT/f'教师{teacher}';folder.mkdir(parents=True,exist_ok=True)
  xlsx=f'教师{teacher}_英文匿名对照评分表.xlsx'
  shutil.copy2(EN/f'教师{teacher}'/xlsx,folder/xlsx)
  assert (folder/xlsx).read_bytes()==(EN/f'教师{teacher}'/xlsx).read_bytes()
  items=sorted([m for m in mappings if m['teacher']==teacher],key=lambda m:m['excel_row'])
  blocks=[]
  for i in range(0,120,2):
   pair=items[i:i+2];assert pair[0]['pair_id']==pair[1]['pair_id']
   case=by_id[pair[0]['case_id']];assert case['english']=='\n'.join(cases[pair[0]['case_id']]['facts'].values())
   zh_labels={'trajectory':'成绩与表现的变化','confidence':'学习信心与做题表现','classroom':'课堂情况','safety':'安全情况','support':'已获得的支持','recentEvent':'近期事件','language':'教学语言','followThrough':'独立解题表现','resources':'学习资源','records':'现有材料','recentChange':'尚未核实的背景情况'}
   en_labels={'trajectory':'Performance over time','confidence':'Confidence and approach','classroom':'Classroom circumstances','safety':'Safety','support':'Support','recentEvent':'Recent event','language':'Instructional language','followThrough':'Independent work','resources':'Resources','records':'Available records','recentChange':'Context not yet checked'}
   case_keys=list(cases[pair[0]['case_id']]['facts'])
   zh_lines=case['chinese'].split('\n');assert len(zh_lines)==len(case_keys)
   zh_case='\n'.join(zh_labels[k]+'：'+line for k,line in zip(case_keys,zh_lines))
   en_case='\n'.join(en_labels[k]+': '+v for k,v in cases[pair[0]['case_id']]['facts'].items())
   cells=[]
   for m in pair:
    r=by_id[m['source_job']]
    cells.append(f'<article><h3>回复{m["reply_id"][-1]}　{m["reply_id"]}</h3><p class="zh">{html.escape(r["chinese"])}</p><details><summary>展开英文原回复</summary><p lang="en">{html.escape(r["english"])}</p></details></article>')
   blocks.append(f'<section id="{pair[0]["pair_id"]}"><h2>{pair[0]["pair_id"]}</h2><h3>完整案例信息（中文译文）</h3><p class="facts">{html.escape(zh_case)}</p><details><summary>展开英文案例原文</summary><p class="facts" lang="en">{html.escape(en_case)}</p></details><div class="pair">{"".join(cells)}</div><p class="hint">请在配套Excel中按回复编号分别填四项分数。A/B不代表固定系统。</p></section>')
  page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>教师{teacher} 中英对照阅读</title><style>body{{font:17px Arial,"Microsoft YaHei",sans-serif;color:#253548;background:#f3f5f7;max-width:1250px;margin:24px auto;padding:18px}}section,.intro{{background:white;padding:26px;margin:24px 0;border-radius:10px}}p{{line-height:1.8;white-space:pre-wrap}}.facts{{background:#eef2f6;padding:16px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}article{{border-top:2px solid #788ba2;min-width:0;overflow-wrap:anywhere}}.hint,small{{color:#596b7b}}summary{{cursor:pointer;color:#315774;padding:12px 0}}a{{color:#315774}}@media(max-width:800px){{.pair{{grid-template-columns:1fr}}}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #dce1e6;padding:12px;text-align:left;line-height:1.6}}</style><header class="intro"><h1>教师{teacher} 中英对照阅读</h1><p>60组配对，共120份回复。中文为AI辅助译文，尚未经独立人工逐条核对；英文原文未改写。点击每项下方可查看原文。译文不是模型的实验输出。</p><p>请根据英文原回复独立评分，中文只辅助理解。尤其“表达清晰性”必须看英文原文，不评价译文是否流畅；如译文与英文不符，以英文为准并记录疑问。不与另一位老师交换评分，不猜测系统身份。</p><p><a href="{html.escape(xlsx)}">打开配套Excel评分表</a>。评分表仍保留英文原文和空白分数，回复编号及A/B顺序与本页完全一致。</p><table><tr><th>项目</th><th>评价要点</th></tr><tr><td>情境相关性</td><td>是否抓住案例值得关注的问题，而非泛泛列举因素。</td></tr><tr><td>信息一致性</td><td>是否忠实于已有事实，没有编造、曲解或过度归因。</td></tr><tr><td>建议适用性</td><td>建议是否适合情境、具体可行；适当补充信息或优先保障安全也可得高分。</td></tr><tr><td>表达清晰性</td><td>英文原回复是否清楚、连贯、容易理解，不因中文译文更流畅而加分。</td></tr></table><p>每项1—5分整数：1很差，2较差，3基本合格，4较好，5很好。具体锚点见Excel“评分说明”。允许同分，不计算总分。不能评价时留空并注明原因，不填0分。</p></header>{''.join(blocks)}</html>'''
  reading=folder/f'教师{teacher}_中英对照阅读.html';reading.write_text(page,encoding='utf-8')
  package=OUT/f'教师{teacher}_中英对照评分材料包.zip'
  with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
   z.write(folder/xlsx,xlsx);z.write(reading,reading.name)
  with zipfile.ZipFile(package) as z:assert len(z.namelist())==2 and not any('internal' in n for n in z.namelist())
  assert len(re.findall(r'<article>',page))==120 and len(re.findall(r'<section id=',page))==60
  checks.append({'teacher':teacher,'pairs':60,'translated_replies':120,'case_source_matches':True,'english_preserved':True,'original_xlsx_byte_identical':True,'blinding_map_in_package':False})
 (OUT/'internal/package_audit.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
 (OUT/'status.json').write_text(json.dumps({'status':'packaged_AI_translations_pending_human_verification','translated':132,'planned':132}),encoding='utf-8')
 print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':main()
