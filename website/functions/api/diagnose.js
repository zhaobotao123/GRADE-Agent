import { getLlmConfig } from "../lib/llm.js";

const SYSTEM_PROMPT = `You are GRADE-Agent, an evidence-informed student mathematics performance diagnostic agent.

Use the supplied case answers and the fixed evidence map to generate a bounded support report. Distinguish population-level evidence from individual information. Do not invent facts or claim that a factor has been proven to cause this student's performance.

Evidence map:
- MATHEFF: stable positive conditional-effect signal across 10/10 plausible values; pooled estimate 28.90.
- DISCLIM: stable positive conditional-effect signal across 10/10 plausible values; pooled estimate 13.74.
- ICTQUAL: positive direction across 10/10 plausible values, but only 6/10 estimates were individually significant and the school-clustered pooled estimate was 2.37 (p = .063); treat as weak or context-sensitive.
- TEACHSUP, BELONG, and ICTSCH: stable negative estimates that require boundary review. Compensatory support, selection, and temporal ordering remain plausible.
- ESCS, HOMEPOS, ICTENQ, and BULLIED: weak or context-sensitive pooled evidence.
- ANXMAT and MATHEF21: unstable across plausible values.

Return concise English with exactly these headings:
CASE SUMMARY
PRIORITY SIGNALS
BOUNDARY-REVIEW SIGNALS
MISSING INFORMATION
COORDINATED SUPPORT PLAN
INTERPRETATION BOUNDARY

Under COORDINATED SUPPORT PLAN, give separate reversible actions for the teacher, family, and student. For every action, explicitly state: TARGET SIGNAL, ACTION, TIME WINDOW, and REVIEW INDICATOR. Each target signal must match a factor discussed earlier in the report; do not introduce generic actions unrelated to the case evidence. Prefer a two-week trial followed by human review. When evidence is insufficient or conflicting, request follow-up information rather than forcing a diagnosis. Keep the report below 450 words.`;

export async function onRequestPost({ request, env }) {
  const llm = getLlmConfig(env);
  if (!llm.apiKey) {
    return Response.json({ error: "The selected AI diagnosis service is not configured." }, { status: 503 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON request." }, { status: 400 });
  }

  const caseId = String(body?.caseId || "unnamed-case").slice(0, 80);
  const answers = JSON.stringify(body?.answers || {}, null, 2).slice(0, 10000);
  const expectedConstraints = JSON.stringify(body?.expectedConstraints || {}, null, 2).slice(0, 6000);
  const prompt = `Generate a GRADE-Agent report for ${caseId}.\n\nCASE ANSWERS\n${answers}\n\nKNOWN EVALUATION CONSTRAINTS\n${expectedConstraints}`;

  try {
    const response = await fetch(llm.endpoint, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${llm.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: llm.model,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: prompt },
        ],
        thinking: { type: "disabled" },
        temperature: 0.25,
        max_tokens: 1500,
        stream: false,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      return Response.json({ error: payload?.error?.message || payload?.message || "AI diagnosis failed." }, { status: response.status });
    }
    const answer = payload?.choices?.[0]?.message?.content;
    if (!answer) return Response.json({ error: "The AI provider returned an empty diagnosis." }, { status: 502 });
    return Response.json({ caseId, answer, model: payload?.model || llm.model, provider: llm.provider, generatedAt: new Date().toISOString() });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Diagnosis service unavailable." }, { status: 502 });
  }
}

export function onRequestGet() {
  return Response.json({ service: "GRADE-Agent AI diagnosis", status: "ready" });
}
