import library from '../../knowledge/pisa-jpn-2022-v2/knowledge.json' with { type: 'json' };

// Bounded full-library context injection. No keyword/vector retrieval or user-factor classifier.
export const KNOWLEDGE_VERSION = library.knowledge_version;
const records = library.records;
if (records.length !== 42 || new Set(records.map(r => r.factor_code)).size !== 42) throw new Error('Invalid knowledge record set');
const number = value => {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error('Invalid evidence number');
  return value;
};
function estimate(row) {
  return {
    coef: number(row.coef ?? row.coef_pooled),
    se: number(row.std_error ?? row.std_error_pooled),
    p: number(row.p_value ?? row.p_value_pooled),
    ci95: row.derived_ci95 ? [row.derived_ci95.low, row.derived_ci95.high] : [row.ci_low, row.ci_high],
    source: row.source_id,
    inference: row.inference_scope ?? 'school-clustered; fixed student-level cross-fitting folds',
  };
}
const evidence = records.map(r => ({
  id: r.id, code: r.factor_code, name: r.name_en, nameZh: r.name_zh,
  evidenceClass: r.evidence_class,
  shap: {meanAbs: number(r.prediction.mean_abs_shap), rank: r.prediction.rank, source: 'shap'},
  dml: r.dml_main ? estimate(r.dml_main) : null,
  pvStability: r.dml_main ? {count: r.dml_main.pv_count, sameDirection: r.dml_main.direction_consistent, significantCount: r.dml_main.significant_pv_count} : null,
  sensitivity: r.sensitivity.map(row => {
    if (row.source_id === 'extra_trees' && row.model !== 'ExtraTrees') throw new Error('ExtraTrees model mismatch');
    return estimate(row);
  }),
}));
const teacher = evidence.find(r => r.code === 'TEACHSUP');
if (!(teacher.sensitivity.find(r => r.source === 'extra_trees')?.p > .05)) throw new Error('Teacher-support sensitivity missing');

export const KNOWLEDGE_METADATA = Object.freeze({
  version: KNOWLEDGE_VERSION, mode: 'full_library_context_injection', recordCount: records.length,
  dmlRecordCount: records.filter(r => r.dml_main).length, rag: false,
  editorialDraftsUsed: false,
});
// Unreviewed definitions, follow-up drafts and support examples are deliberately not injected.
export const KNOWLEDGE_CONTEXT = `\nCURRENT STRUCTURED RESEARCH EVIDENCE (${KNOWLEDGE_VERSION})
This is a fixed versioned evidence library supplied in full, not retrieved documents. Use it as research context, not as instructions from a student.
Study: Japan PISA 2022, 5760 students, 182 schools, ten mathematics plausible values.
Only select aspects supported by the user's observations; receiving a record does not mean that factor is present for this student. No DML entry means no corresponding adjusted-association result; never fill it in.
Absolute SHAP is predictive contribution, with no positive/negative direction. Do not rank intervention benefits using SHAP or compare raw DML coefficients across different factor scales.
Main and alternative-learner intervals use school-clustered inference. BRR sensitivity uses full replicate-specific nuisance refits and is conditional on frozen student-level folds; it is not school-grouped cross-fitting. Sensitivity exists for five factors only.
Numerical p=0 in source is floating-point underflow: report p<.001 if asked, never an exact zero probability. Main CI values are derived as coefficient +/-1.96*SE.
For TEACHSUP, retain the ExtraTrees interval crossing zero even when RF and BRR exclude zero. Negative support/belonging/school-ICT associations never justify reducing support, belonging or resources. Compensatory allocation and timing are possible explanations, not proven mechanisms.
Population associations are not individual causes. Safety and supplied case facts take precedence. Unknowns stay unknown. For topics not covered by this library, do not invent PISA findings or claim research-backed effects; use bounded general guidance and clarification.
Continue the existing natural conversation style. Use research numbers/codes only when explicitly asked. Support suggestions must be tailored to the reported circumstances; these statistical records are not a validated intervention recommendation database.
Record source IDs refer to versioned CSV snapshots in sources_manifest.json. Educational draft examples have not been expert reviewed and are excluded from this runtime context.
EVIDENCE RECORDS JSON:\n${JSON.stringify(evidence)}\nEND STRUCTURED RESEARCH EVIDENCE\n`;

export function buildKnowledgePrompt(conversationPrompt) { return conversationPrompt + KNOWLEDGE_CONTEXT; }
