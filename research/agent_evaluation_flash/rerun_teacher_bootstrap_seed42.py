"""Reanalyse confirmed original teacher ratings; seed changed at author's request."""
import csv
import hashlib
import json
from pathlib import Path

import finalize_teacher_results_v21 as original

np = original.np
OUT = original.BASE / 'outputs/teacher_bootstrap_seed42_20261028'
SEED, N_BOOT = 42, 50000


def main():
    mapping = json.loads(original.MAP.read_text(encoding='utf-8'))['mapping']
    teachers, hashes = {}, {}
    for teacher in (1, 2):
        source = original.DATA / f'教师{teacher}_中英对照评分材料包/教师{teacher}_英文匿名对照评分表_已评分.xlsx'
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert digest == original.EXPECTED[teacher], 'Original teacher ratings changed.'
        hashes[str(teacher)] = digest
        lookup = {r['reply_id']: r for r in mapping if r['teacher'] == teacher}
        workbook = original.openpyxl.load_workbook(source, data_only=True)
        rows = {}
        for row in workbook['对照评分'].iter_rows(min_row=6, max_row=125, values_only=True):
            item = lookup[row[1]]
            assert hashlib.sha256(row[3].encode()).hexdigest() == item['reply_sha256']
            scores = row[4:8]
            assert all(type(v) in (int, float) and v in (1, 2, 3, 4, 5) for v in scores)
            assert item['source_job'] not in rows
            rows[item['source_job']] = {**item, 'scores': np.asarray(scores, dtype=float)}
        assert len(rows) == 120
        teachers[teacher] = rows
    assert set(teachers[1]) == set(teachers[2])
    merged = [{**r, 'scores': (r['scores'] + teachers[2][k]['scores']) / 2}
              for k, r in sorted(teachers[1].items())]
    cases = sorted({r['case_id'] for r in merged})
    assert len(cases) == 12
    for c in cases:
        for s in ('ordinary_llm', 'grade_agent'):
            assert len([r for r in merged if r['case_id'] == c and r['system'] == s]) == 5
    cube = np.array([[np.mean([r['scores'] for r in merged if r['case_id'] == c and r['system'] == s], axis=0)
                      for s in ('ordinary_llm', 'grade_agent')] for c in cases])
    differences = cube[:, 1] - cube[:, 0]
    old = json.loads((original.OUT / 'results.json').read_text(encoding='utf-8'))
    assert cases == old['cases']
    np.testing.assert_allclose(differences, old['case_differences'], atol=1e-14, rtol=0)
    draws = np.random.default_rng(SEED).integers(0, 12, size=(N_BOOT, 12))
    boot = differences[draws].mean(axis=1)
    ci = np.quantile(boot, [.025, .975], axis=0)
    # Repeat from fresh generator to verify reproducibility, not a seed search.
    repeat = np.random.default_rng(SEED).integers(0, 12, size=(N_BOOT, 12))
    assert np.array_equal(draws, repeat)
    summary = []
    for j, name in enumerate(original.NAMES):
        record = dict(old['summary'][j])
        np.testing.assert_allclose([record['ordinary_mean'], record['agent_mean'], record['paired_difference']],
                                   [cube[:, 0, j].mean(), cube[:, 1, j].mean(), differences[:, j].mean()], atol=1e-14, rtol=0)
        record.update(ci_low=float(ci[0, j]), ci_high=float(ci[1, j]))
        summary.append(record)
    OUT.mkdir(parents=True, exist_ok=True)
    result = {**old, 'summary': summary, 'seed': SEED,
              'revision_reason': 'Author requested seed 42; original seed-20261027 analysis retained. Not selected by outcome.',
              'source_teacher_sha256': hashes, 'numpy_version': np.__version__,
              'rng': 'numpy.random.default_rng / PCG64', 'quantile_method': 'linear',
              'bootstrap_indices_sha256': hashlib.sha256(draws.tobytes()).hexdigest(),
              'raw_ratings_unchanged': True, 'means_and_case_differences_verified_unchanged': True}
    (OUT / 'results_seed42.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 教师评分 Bootstrap 重新计算（随机种子42）', '',
             '使用两位老师已确认的原始评分表重新读取并核对匿名对应关系。共120份回复、960项评分；原始文件哈希与冻结记录一致。', '',
             '计算顺序：每份回复先平均两位老师评分，再平均同案例同系统的5次运行，得到12个配对案例差值。以案例为单位有放回抽样50,000次，计算95%百分位置信区间。随机种子固定为42。', '',
             '此次仅因作者要求改变随机种子。原种子20261027的结果完整保留；不重新生成回复、不修改评分、不改变抽样单位或统计方法。', '',
             '| 维度 | 普通LLM均值 | GRADE-Agent均值 | 配对均差 | 新95%CI（42） | 原95%CI（20261027） |',
             '| --- | ---: | ---: | ---: | --- | --- |']
    labels = ['情境相关性', '与案例事实一致性', '建议适当性与可操作性', '表达清晰性']
    for label, row, previous in zip(labels, summary, old['summary']):
        lines.append(f"| {label} | {row['ordinary_mean']:.2f} | {row['agent_mean']:.2f} | {row['paired_difference']:.2f} | [{row['ci_low']:.4f}, {row['ci_high']:.4f}] | [{previous['ci_low']:.4f}, {previous['ci_high']:.4f}] |")
    lines += ['', '均值、配对均差及评分者一致性不依赖Bootstrap随机种子，核对后均未改变。以上区间以两位固定教师为条件；次要维度区间为未作多重比较校正的探索性区间。', '',
              '论文和补充材料尚未自动替换；后续采用本结果时应同步修改方法中的种子、表格、图和可复现代码。']
    (OUT / 'Bootstrap_seed42_复算结果.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'output': str(OUT), 'seed': SEED, 'summary': summary}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
