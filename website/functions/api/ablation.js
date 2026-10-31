import { getLlmConfig } from "../lib/llm.js";

const EVIDENCE_MAP = `Population evidence map:
- MATHEFF: stable positive conditional-effect signal across 10/10 plausible values; pooled estimate 28.90.
- DISCLIM: stable positive conditional-effect signal across 10/10 plausible values; pooled estimate 13.74.
- ICTQUAL: positive direction across 10/10 plausible values, but only 6/10 estimates were individually significant and the school-clustered pooled estimate was 2.37 (p = .063); treat as weak or context-sensitive.
- TEACHSUP, BELONG, and ICTSCH: negative estimates requiring temporal and selection-boundary review.
- ESCS, HOMEPOS, ICTENQ, and BULLIED: weak or context-sensitive pooled evidence.
- ANXMAT and MATHEF21: unstable across plausible values.`;

const PREDICTIVE_MAP = `Predictive evidence map:
- SHAP and weighted prediction analyses prioritize MATHEFF, DISCLIM, ESCS, ANXMAT, and selected contextual variables.
- Predictive importance ranks variables but does not identify an adjusted effect or establish an individual cause.
- Use case information to decide whether a population-level predictive signal is relevant.`;

const OUTPUT_STRUCTURE = `Return concise English with exactly these headings:
CASE SUMMARY
PRIORITY SIGNALS
BOUNDARY-REVIEW SIGNALS
MISSING INFORMATION
COORDINATED SUPPORT PLAN
INTERPRETATION BOUNDARY

Under COORDINATED SUPPORT PLAN, give separate reversible actions for the teacher, family, and student. For every action, state TARGET SIGNAL, ACTION, TIME WINDOW, and REVIEW INDICATOR. Keep the report below 450 words.`;

const BASE_GRADE_AGENT = `You are GRADE-Agent, an evidence-informed student mathematics performance diagnostic agent.

Distinguish population-level evidence from individual case information. Do not invent facts or claim that a factor has been proven to cause this student's performance. Request missing information rather than forcing a diagnosis. Each recommended action must target a factor already discussed and must be reversible and reviewable.

Priority-selection protocol:
1. In PRIORITY SIGNALS, name exactly one primary signal first.
2. Apply this precedence order: safeguarding disclosure; conflicting sources; a documented temporary event attached to an isolated result; an explicitly observed language, support-timing, confidence, classroom, or transfer-to-independent-work signal; then information insufficiency.
3. Treat safeguarding, conflict, and isolated-event categories as hard gates. Treat an observed language context or compensatory support timing as a valid case-supported signal.
4. Information insufficiency is the primary signal only when the case is minimal or an unexplained decline has no earlier case-supported category.
5. Build the candidate set only from factors positively supported by supplied case information. Absence of evidence, adequate functioning, or an unmeasured factor does not create a candidate.`;

export const DML_BLOCK = `DML evidence is enabled.

${EVIDENCE_MAP}

Use DML stability and pooled adjusted-effect evidence only to rank factors inside the case-supported candidate set. Stable case-matched signals outrank weak or context-sensitive signals. DML may prioritize inquiry, but it must not supply an individual-level diagnosis.`;

export const CRITIC_BLOCK = `Before returning the report, act as a diagnostic critic. Verify that: (a) the primary signal follows the precedence order; (b) information insufficiency is used only as the final fallback; (c) every prioritized factor is supported by an explicit case fact; (d) population evidence has not displaced a safety, conflict, transient-event, language-context, or support-timing signal; and (e) temporal ordering, compensatory support, unsupported mechanisms, safeguarding, causal language, and action-to-signal alignment are handled. Revise every violation before returning the report.`;

export function buildGradeAgentPrompt({ useDml, useCritic }) {
  return [
    BASE_GRADE_AGENT,
    PREDICTIVE_MAP,
    useDml ? DML_BLOCK : "",
    useCritic ? CRITIC_BLOCK : "",
    OUTPUT_STRUCTURE,
  ].filter(Boolean).join("\n\n");
}

export const SYSTEM_PROMPTS = {
  single_turn_llm: `You are a general educational assistant. Read the supplied case and provide a concise assessment of likely factors and practical recommendations. Do not use an external evidence map or a structured diagnostic rule system.`,

  evidence_only_llm: `You are an educational assistant supplied with a PISA 2022 evidence map. Use it when interpreting the case, but no explicit diagnostic rules, critique step, or output constraints are available.

${EVIDENCE_MAP}`,

  grade_agent_no_dml_no_critic: buildGradeAgentPrompt({ useDml: false, useCritic: false }),
  grade_agent_no_critic: buildGradeAgentPrompt({ useDml: true, useCritic: false }),
  grade_agent_no_dml: buildGradeAgentPrompt({ useDml: false, useCritic: true }),
  full_grade_agent: buildGradeAgentPrompt({ useDml: true, useCritic: true }),
};

export async function onRequestPost({ request, env }) {
  const llm = getLlmConfig(env);
  if (!llm.apiKey) {
    return Response.json({ error: "The selected AI service is not configured." }, { status: 503 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON request." }, { status: 400 });
  }

  const system = String(body?.system || "");
  const systemPrompt = SYSTEM_PROMPTS[system];
  if (!systemPrompt) {
    return Response.json({ error: "Unknown ablation system." }, { status: 400 });
  }

  const caseId = String(body?.caseId || "unnamed-case").slice(0, 100);
  const answers = JSON.stringify(body?.answers || {}, null, 2).slice(0, 10000);
  const prompt = `Assess ${caseId}.\n\nCASE INFORMATION\n${answers}`;

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
          { role: "system", content: systemPrompt },
          { role: "user", content: prompt },
        ],
        thinking: { type: "disabled" },
        temperature: 0.4,
        max_tokens: 1500,
        stream: false,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      return Response.json(
        { error: payload?.error?.message || payload?.message || "AI generation failed." },
        { status: response.status },
      );
    }
    const report = payload?.choices?.[0]?.message?.content;
    if (!report) return Response.json({ error: "The AI provider returned an empty report." }, { status: 502 });
    return Response.json({
      caseId,
      system,
      report,
      model: payload?.model || llm.model,
      provider: llm.provider,
      generatedAt: new Date().toISOString(),
    });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Ablation service unavailable." },
      { status: 502 },
    );
  }
}

export function onRequestGet() {
  return Response.json({ service: "GRADE-Agent ablation", systems: Object.keys(SYSTEM_PROMPTS) });
}
