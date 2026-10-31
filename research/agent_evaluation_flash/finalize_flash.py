"""Audit frozen test sessions, export blinded human packet, summarize without ratings."""
from collections import Counter,defaultdict
import csv
import hashlib
import html
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'work/pisa_audit_deps'))
import numpy as np

from run_multiturn_v2 import ROOT,SYSTEMS

DELIVERY=Path(__file__).resolve().parents[1]/'outputs/grade_agent_flash_20261025'
LABELS={'llm_baseline':'普通LLM','agent_no_dml_no_critic':'无DML、无复核',
 'agent_dml_only':'有DML、无复核','agent_critic_only':'无DML、有复核','agent_full':'完整智能体'}
DOMAINS_ZH={'confidence':'信心与考试感受','classroom':'课堂情况','support':'帮助与时间顺序','context':'情境与安全','resources':'家庭资源'}
FACTOR_ZH={'confidence':'学习信心','anxiety':'数学考试担忧','classroom':'课堂环境','support_timing':'支持时序',
 'belonging':'归属','school_ict':'学校ICT','home_resources':'家庭学习资源','family_engagement':'家庭学习安排',
 'language':'教学语言','health_attendance':'健康出勤','assessment_event':'测验事件','independent_work':'独立解题','bullying':'同伴威胁/欺凌'}


def read(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    lock=read(ROOT/'protocol_lock.json')
    status=read(ROOT/'formal/status.json')
    if status['completed_sessions']!=300: raise RuntimeError('Test generation not complete')
    for path,expected in lock['source_hashes'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,path
    assert hashlib.sha256((ROOT/'cases_author_reference.json').read_bytes()).hexdigest()==lock['case_sha256']
    cases={c['case_id']:c for c in read(ROOT/'cases_author_reference.json')['cases']}
    rows=[read(p) for p in (ROOT/'formal/sessions').glob('*/session.json')]
    keys=[(r['case_id'],r['system'],r['repeat']) for r in rows]
    assert len(rows)==len(set(keys))==300
    assert all(r['signature']==lock['signature'] and r['split']=='test' for r in rows)
    counts=Counter((r['case_id'],r['system']) for r in rows)
    assert len(counts)==150 and set(counts.values())=={2}
    metrics=read(ROOT/'formal/session_metrics.json')
    assert len(metrics)==300
    by_key={(m['case_id'],m['system'],m['repeat']):m for m in metrics}
    for r in rows:
        m=by_key[(r['case_id'],r['system'],r['repeat'])]
        case=cases[r['case_id']]
        truth=set(v for vals in case['author_reference_factors_by_domain'].values() for v in vals)
        entries=(r.get('assessment') or {}).get('factors',[])
        pred={str(e.get('id','INVALID')) for e in entries if isinstance(e,dict)}
        a,b,c=len(pred&truth),len(pred-truth),len(truth-pred)
        assert (a,b,c)==(m['tp'],m['fp'],m['fn'])
        expected=2*a/(2*a+b+c) if truth else None
        assert expected==m['f1']
    # Average repeats and related variants within scenario families before uncertainty.
    contrasts=[]
    rng=np.random.default_rng(20261025)
    fields=['f1','required_domain_coverage','valid_final','assessment_before_required_domains']
    for field in fields:
        groups=defaultdict(list)
        for m in metrics:
            if m[field] is not None: groups[(m['family'],m['system'])].append(float(m[field]))
        vectors=defaultdict(list)
        for family in sorted({m['family'] for m in metrics}):
            values={s:float(np.mean(groups[(family,s)])) for s in SYSTEMS if groups[(family,s)]}
            if len(values)!=5: continue
            a,b,c,d=[values[s] for s in SYSTEMS[1:]]
            vectors['完整减普通LLM'].append(d-values['llm_baseline'])
            vectors['DML主效应'].append(((b-a)+(d-c))/2)
            vectors['复核主效应'].append(((c-a)+(d-b))/2)
            vectors['DML与复核交互'].append(d-b-c+a)
        for name,values in vectors.items():
            v=np.asarray(values)
            boot=v[rng.integers(0,len(v),(5000,len(v)))].mean(axis=1)
            low,high=np.quantile(boot,[.025,.975])
            contrasts.append({'metric':field,'contrast':name,'difference':float(v.mean()),
                'scenario_families':len(v),'exploratory_CI_low':float(low),'exploratory_CI_high':float(high)})
    save(ROOT/'formal/exploratory_family_cluster_contrasts.json',contrasts)
    with (ROOT/'formal/session_metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(metrics[0]));writer.writeheader();writer.writerows(metrics)
    # Frozen, output-independent sample selection; no replacements for invalid output.
    plan=read(ROOT/'restricted_human_sample_plan.json')
    assert plan['signature']==lock['signature'] and len(plan['slots'])==30
    indexed={(r['case_id'],r['system'],r['repeat']):r for r in rows}
    packets=[]
    for slot in plan['slots']:
        r=indexed[(slot['case_id'],slot['system'],slot['repeat'])]
        case=cases[r['case_id']]
        packets.append({'report_id':slot['report_id'],'opening':case['opening'],
            'received_facts':{d:case['facts'][d] for d in r['revealed_domains']},
            'assessment':r['assessment'],'generation_status':r['status']})
    DELIVERY.mkdir(parents=True,exist_ok=True)
    save(DELIVERY/'anonymous_report_packets.json',packets)
    save(DELIVERY/'packet_index.json',[{'report_id':p['report_id'],'status':p['generation_status']} for p in packets])
    parts=['<!DOCTYPE html><html lang="zh-CN"><meta charset="utf-8"><title>匿名报告材料</title>',
        '<style>body{max-width:900px;margin:32px auto;font:17px/1.8 "Microsoft YaHei",sans-serif;color:#243246}section{border-top:2px solid #ccd4df;padding-top:20px;margin-top:36px;page-break-before:always}h1{font-size:28px}h2{font-size:24px}h3{font-size:18px}pre{white-space:pre-wrap;font:inherit}li{margin:8px 0}.notice{background:#fff3d5;padding:14px}</style>',
        '<h1>匿名报告材料：30份</h1><p class="notice">请配合独立评分表使用。每份仅评因素合理性、建议适用性、不确定性处理，各0—2分。这里没有教师参考分，也没有系统名称。若无报告，请保留评分空白并注明生成失败。</p>',
        '<p>仅依据下方已经收到的案例事实判断报告。未披露内容保持未知；保护性、正常表现不等于负面影响因素。下方因素清单是模型原始输出，不是参考答案。</p>']
    for p in packets:
        parts.append(f'<section id="{p["report_id"]}"><h2>{p["report_id"]}</h2><h3>初始情况</h3><p>{html.escape(p["opening"])}</p><h3>本场咨询已收到的事实</h3><ul>')
        for d,fact in p['received_facts'].items():parts.append(f'<li><b>{DOMAINS_ZH[d]}：</b>{html.escape(fact)}</li>')
        parts.append('</ul><h3>模型报告</h3>')
        if p['assessment'] is None:
            parts.append('<p class="notice">本场没有形成有效最终报告。保留为生成失败，不替换其他次结果，不填写内容质量分。</p>')
        else:
            parts.append('<pre>'+html.escape(p['assessment'].get('report',''))+'</pre><h3>模型列出的因素（非参考标签）</h3><ul>')
            for entry in p['assessment'].get('factors',[]):
                if isinstance(entry,dict):
                    name=FACTOR_ZH.get(entry.get('id'),entry.get('id','未知代码'))
                    parts.append(f'<li>{html.escape(str(name))}；模型引文：{html.escape(str(entry.get("case_quote","")))}</li>')
            parts.append('</ul>')
        parts.append('</section>')
    parts.append('</html>')
    (DELIVERY/'匿名报告材料.html').write_text('\n'.join(parts),encoding='utf-8')
    summary=read(ROOT/'formal/automatic_summary.json')
    lines=['# Flash受控多轮测试结果','',
        '这是30个作者设计合成案例的预定测试，参考标签尚未获独立专家验证。开发与测试共享10个情境族。结果不代表真实学生因果诊断准确率。','',
        f"共300场咨询，形成有效最终报告{status['valid_sessions']}场；其余场次保留，不挑选重跑。",'',
        '| 条件 | 有效最终报告比例 | 非空标签案例平均F1 | 必要信息领域覆盖率 |',
        '|---|---:|---:|---:|']
    for s in summary:
        lines.append(f"| {LABELS[s['system']]} | {s['valid_final_rate']:.1%} | {s['mean_nonempty_reference_F1']:.3f} | {s['required_domain_coverage']:.1%} |")
    lines+=['','F1相对作者预设的案例支持因素集合；不是独立专家金标准。无正向参考标签案例另报正确暂缓，不自动记满分F1。',
        '无效最终输出在非空标签案例中计入漏识别分母；不只统计成功场次。',
        '部分输出把正常或保护性条件也列入factors，而参考集合关注困难相关因素。清单编码与正文可能不一致；保留原定评分并披露歧义，不改标签救分，不能把所有集合假阳性直接当作有害诊断。',
        '逐字引文匹配仅验证文本来源，不验证引文是否支持模型解释。领域覆盖率是粗粒度代理，并不直接测量问题质量。','',
        '## 消融与不确定性','',
        '四个智能体条件用于分别观察DML分析信息、复核提示及交互。探索性差值按情境族平均并重抽样；F1仅涉及9个非空标签情境族，不能宣称强外部验证。未计算确认性p值。','']
    for c in contrasts:
        if c['metric']=='f1':
            lines.append(f"- {c['contrast']}：F1差值{c['difference']:+.3f}，探索性95%区间[{c['exploratory_CI_low']:+.3f}, {c['exploratory_CI_high']:+.3f}]，{c['scenario_families']}个情境族。")
    lines+=['','## 人工材料','',
        f"按生成前锁定抽样方案导出30份匿名材料，实际有报告{sum(p['assessment'] is not None for p in packets)}份。两份工作簿保持空白，由教师独立填写；没有伪造评分或一致性结果。",'',
        f"本轮正式调用{status['saved_logical_calls']}次，记录输入{status['usage']['prompt_tokens']}tokens、输出{status['usage']['completion_tokens']}tokens。",
        f"按非高峰未缓存价格估算上限约${status['usage']['estimated_USD_off_peak_no_cache']:.3f}；实际缓存优惠和账单另核。",
        '原论文、旧Pro结果及在线系统未修改。']
    (DELIVERY/'Flash多轮实验结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    audit={'status':'frozen_test_generation_audited_human_ratings_pending','unique_sessions':300,'hashes_verified':True,
        'factor_set_arithmetic_independently_recomputed':True,'valid_sessions':status['valid_sessions'],
        'human_packets':30,'human_valid_reports':sum(p['assessment'] is not None for p in packets),
        'human_ratings_completed':False,'independent_reference_validation':False,'website_deployed':False,
        'original_manuscript_modified':False,'signature':lock['signature']}
    save(ROOT/'formal/audit.json',audit)
    print(json.dumps(audit,ensure_ascii=False))


if __name__=='__main__':main()
