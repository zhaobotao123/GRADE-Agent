"""Verify full-text preservation, quotations, identifiers and frozen score sheets."""
from pathlib import Path
from collections import Counter
import hashlib,html,json,re,zipfile

BASE=Path('C:/Users/84130/Documents/Codex/2026-08-09/zh/outputs')
ROOT=BASE/'teacher_summary_20261026_v2'
OLD=BASE/'teacher_evaluation_20261026_v1'
INTERNAL=ROOT/'研究者留存_不要发给老师'
source_path=Path('D:/pisa2022/outputs_grade_agent_deepseek41flash300_20261026/raw_reports.json')
source_by_hash={hashlib.sha256(r['report'].encode()).hexdigest():r['report'] for r in json.loads(source_path.read_text(encoding='utf-8'))}
summaries=[json.loads(p.read_text(encoding='utf-8')) for p in (INTERNAL/'summaries').glob('*.json')]
assert len(summaries)==60 and len({r['blind_id'] for r in summaries})==60
reports={r['blind_id']:source_by_hash[r['source_sha256']] for r in summaries}
count=0
for row in summaries:
    assert row['status']=='completed' and row['fidelity_checks'][-1]['faithful'] is True
    for metric in ['main','advice','boundary']:
        block=row['reading_aid'][metric];assert re.search('[\u4e00-\u9fff]',block['summary_zh'])
        for q in block['verified_quotes']:
            assert reports[row['blind_id']][q['start']:q['end']]==q['text'];count+=1
for teacher in [1,2]:
    new_dir=ROOT/f'教师{teacher}'
    new_page=(new_dir/'60匿名报告_中文摘要与原文.html').read_text(encoding='utf-8')
    old_page=(OLD/'确认A后再发_阶段B'/f'教师{teacher}'/'60匿名报告.html').read_text(encoding='utf-8')
    assert re.findall(r'<option value="(B\d{3})">',old_page)==re.findall(r'<option value="(B\d{3})">',new_page)
    assert new_page.count('中文忠实摘要（AI辅助，不是原始输出）')==60
    assert new_page.count('展开英文完整回复（原文未改动）')==60
    assert new_page.count('查看对应英文原句')==180
    parsed=re.findall(r'<article id="(B\d{3})"[^>]*>.*?<pre class="report" lang="en">(.*?)</pre></details></article>',new_page,re.S)
    assert len(parsed)==60
    for ident,encoded in parsed:assert html.unescape(encoded)==reports[ident]
    name=f'阶段B_报告评分_教师{teacher}.xlsx'
    with zipfile.ZipFile(OLD/f'阶段B_教师{teacher}_材料包.zip') as z:original_book=z.read(name)
    assert (new_dir/name).read_bytes()==original_book
    with zipfile.ZipFile(ROOT/f'教师{teacher}_中文摘要评分材料包.zip') as z:
        assert len(z.namelist())==3 and z.read(name)==original_book
        assert z.read('60匿名报告_中文摘要与原文.html')==(new_dir/'60匿名报告_中文摘要与原文.html').read_bytes()
        assert not any('mapping' in name or 'calls/' in name for name in z.namelist())
plan=json.loads((OLD/'研究者留存_不要发给老师/evaluation_plan.json').read_text(encoding='utf-8'))
assert hashlib.sha256(source_path.read_bytes()).hexdigest()==plan['source_raw_sha256']
result={'n_reading_aids':60,'n_exact_source_quotes_verified':count,'fidelity_checked_in_separate_same_model_sessions':True,
    'content_revision_distribution':dict(Counter(r['final_revision'] for r in summaries)),
    'assistant_source_checked_translation_edits':[r['blind_id'] for r in summaries if r.get('assistant_source_checked_translation_edit')],
    'full_originals_unchanged_in_both_teacher_pages':True,'teacher_ids_and_report_order_unchanged':True,
    'score_workbooks_byte_identical_to_original_blank_templates':True,'source_300_reports_unchanged':True,
    'packages_exclude_internal_labels_and_checks':True,'no_new_report_quality_scores_computed':True,
    'browser_visual_preview':'Not performed: browser tool disallows file URLs. No bypass attempted.',
    'limitation':'Chinese aids are AI-assisted and source checked, not certified human translations; teachers must consult original replies.'}
(INTERNAL/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
