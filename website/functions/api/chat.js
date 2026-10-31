import { getLlmConfig } from "../lib/llm.js";
import { buildKnowledgePrompt, KNOWLEDGE_METADATA } from "../lib/knowledge.js";
import { CONVERSATION_PROMPT, CONVERSATION_VERSION, cleanMessages, hasAffirmativeSafetyConcern, safetyTurn, parseTurn } from "../lib/conversation.js";
const json = (body, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
export async function onRequestPost({ request, env }) {
  let body, messages;
  try { body = await request.json(); messages = cleanMessages(body?.messages); }
  catch (error) { return json({ error: error.message || "Invalid conversation request." }, 400); }
  if (!messages.length || messages.at(-1).role !== "user") return json({ error: "A user message is required." }, 400);
  if (hasAffirmativeSafetyConcern(messages)) return json({ ...safetyTurn(messages), provider: "local-safeguard", model: null, guardrailVersion: CONVERSATION_VERSION });
  const llm = getLlmConfig(env);
  if (!llm.apiKey) return json({ error: "The selected AI conversation service is not configured.", errorCode: "MODEL_NOT_CONFIGURED" }, 503);
  let correction = "";
  // UI history contains display text; preserve it inside the model's JSON
  // envelope so subsequent turns do not imitate a plain-text response format.
  const modelMessages = messages.map(message => message.role === 'assistant'
    ? {role:'assistant',content:JSON.stringify({phase:/[?？]/.test(message.content)?'question':'summary',reply:message.content})}
    : message);
  try {
    for (let attempt = 0; attempt < 2; attempt++) {
      const response = await fetch(llm.endpoint, { method: "POST", signal: AbortSignal.timeout(45000), headers: { Authorization: `Bearer ${llm.apiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({ model: llm.model, messages: [{ role: "system", content: buildKnowledgePrompt(CONVERSATION_PROMPT) + correction }, ...modelMessages], response_format: { type: "json_object" }, thinking: { type: "disabled" }, temperature: attempt ? 0 : 0.25, max_tokens: 1400, stream: false }) });
      const payload = await response.json();
      if (!response.ok) {
        if (String(payload?.error?.code) === "1113") return json({ error: "The model account has no available balance or resource package.", errorCode: "MODEL_QUOTA_UNAVAILABLE" }, 503);
        return json({ error: "The conversation service is temporarily unavailable. Please retry; your observations remain in this session." }, response.status === 429 ? 429 : 502);
      }
      const choice = payload?.choices?.[0];
      try {
        if (choice?.finish_reason !== "stop") throw new Error("Reply incomplete; return shorter complete JSON.");
        const turn = parseTurn(choice?.message?.content, messages);
        return json({ ...turn, model: payload.model || llm.model, provider: llm.provider, guardrailVersion: CONVERSATION_VERSION, knowledge: KNOWLEDGE_METADATA, generatedAt: new Date().toISOString() });
      } catch (error) {
        console.warn('Conversation output validation failed', JSON.stringify({finish:choice?.finish_reason,contentLength:choice?.message?.content?.length,error:error.message}));
        if (env.LOCAL_CONVERSATION_DEBUG === '1') console.warn('Conversation contract:', JSON.stringify({finish:choice?.finish_reason,contentLength:choice?.message?.content?.length,error:error.message}));
        correction = "\nThe previous output failed the contract: " + error.message + " Return a complete corrected conversational turn, not a report or generic example.";
      }
    }
    return json({ error: "The service could not form a complete conversational reply. Please retry." }, 502);
  } catch { return json({ error: "The conversation service could not be reached. Please retry; your observations are still visible." }, 502); }
}
export function onRequestGet() { return json({ service: "GRADE-Agent conversational learning support", status: "ready", guardrailVersion: CONVERSATION_VERSION, knowledge: KNOWLEDGE_METADATA }); }
