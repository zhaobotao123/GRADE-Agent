# GRADE-Agent knowledge v2

Corrected model-aware ExtraTrees mapping. All five rows checked against the ExtraTrees model rows, including all numeric fields and Markdown values.

The website /api/chat imports knowledge.json through functions/lib/knowledge.js. All 42 prediction records, 12 main DML records and 15 sensitivity entries are supplied as structured research context on every model call. No retrieval or vectors. Unreviewed educational drafts are excluded.

Original experimental runtime archived separately; this is a new website version and does not relabel historical evaluations. V1 has incorrect ExtraTrees mapping and must not be used.
