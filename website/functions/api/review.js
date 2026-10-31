import { getLlmConfig } from "../lib/llm.js";

const SYSTEM_PROMPT = `You are the independent review layer for GRADE-Agent, an evidence-informed educational diagnostic prototype.

Review the generated report as a cautious panel combining expertise in educational measurement, causal machine learning, and school-based student support. Your job is to audit the report, not to diagnose the student.

Rules:
1. Distinguish predictive importance, SHAP attribution, and cross-fitted DML conditional-effect estimates.
2. Treat DML estimates as causal only under the stated identification assumptions. Never claim proof for an individual student.
3. Interpret negative estimates for teacher support, belonging, or school ICT as boundary-review signals because compensatory support, selection, and temporal ordering remain plausible.
4. Keep teachers and other professionals in control of consequential decisions.
5. Do not infer sensitive traits or invent facts that are absent from the case.

Return concise English with exactly these headings:
VERDICT
EVIDENCE ALIGNMENT
CAUSAL AND INTERPRETIVE BOUNDARY
ACTIONABILITY
MISSING INFORMATION
RECOMMENDED REVISION

Use plain text without Markdown symbols. Write one or two sentences under each heading and keep the entire review below 320 words.`;

const DEFAULT_REPORT = `A sustained mathematics-performance decline warrants follow-up on learning confidence, classroom conditions, and follow-through after instruction. Population-level priority signals are mathematics self-efficacy and disciplinary climate; they are not proven individual causes. Teacher support is a boundary-review signal because additional tutoring began after the decline. Recommended actions include low-stakes worked examples, a structured family review routine, and student question logging.`;

export async function onRequestPost({ request, env }) {
  const llm = getLlmConfig(env);
  if (!llm.apiKey) {
    return Response.json({ error: "The selected AI review service is not configured." }, { status: 503 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON request." }, { status: 400 });
  }

  const caseContext = String(body?.caseContext || "").slice(0, 6000);
  const report = String(body?.report || DEFAULT_REPORT).slice(0, 8000);
  const userPrompt = `Audit this GRADE-Agent output.\n\nCASE CONTEXT\n${caseContext || "Prototype case: sustained decline, low mathematics confidence, frequent classroom disruption, and teacher support introduced after the decline."}\n\nREPORT\n${report}`;

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
          { role: "user", content: userPrompt },
        ],
        thinking: { type: "disabled" },
        temperature: 0.2,
        max_tokens: 1000,
        stream: false,
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      const message = payload?.error?.message || payload?.message || "AI review failed.";
      return Response.json({ error: message }, { status: response.status });
    }

    const review = payload?.choices?.[0]?.message?.content;
    if (!review) {
      return Response.json({ error: "The AI provider returned an empty review." }, { status: 502 });
    }

    return Response.json({
      review,
      model: payload?.model || llm.model,
      provider: llm.provider,
      reviewedAt: new Date().toISOString(),
      boundary: "AI-generated review for decision support; professional verification remains required.",
    });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Review service unavailable." }, { status: 502 });
  }
}

export function onRequestGet() {
  return Response.json({
    service: "GRADE-Agent AI review",
    status: "ready",
    note: "Submit a POST request from the diagnostic report interface.",
  });
}
