import assert from "node:assert/strict";
import { getLlmConfig } from "../functions/lib/llm.js";
import { onRequestPost as chat } from "../functions/api/chat.js";
import { onRequestPost as review } from "../functions/api/review.js";
import { onRequestPost as diagnose } from "../functions/api/diagnose.js";
import { onRequestPost as ablation } from "../functions/api/ablation.js";

const zhipu = { AI_PROVIDER: "zhipu", ZHIPU_API_KEY: "test-zhipu-only", DEEPSEEK_API_KEY: "test-deepseek-only" };
assert.equal(getLlmConfig(zhipu).model, "glm-4.5-flash");
assert.equal(getLlmConfig({ DEEPSEEK_API_KEY: "legacy" }).provider, "deepseek");
assert.equal(getLlmConfig({ AI_PROVIDER: "zhipu", DEEPSEEK_API_KEY: "wrong-provider" }).apiKey, undefined);
assert.equal(getLlmConfig({ AI_PROVIDER: "unknown", DEEPSEEK_API_KEY: "unused" }).apiKey, undefined);
const request = (body) => new Request("https://example.invalid/api/test", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});
const fixture = {
  phase: "question", reply: "When did the decline begin?", questionFocus: "trajectory",
  coverage: { confirmed: [], missing: ["Achievement trajectory"], readyForAssessment: false },
  suggestedReplies: [], assessment: null,
};
const originalFetch = globalThis.fetch;
let calls = 0;
globalThis.fetch = async (url, options) => {
  calls++;
  assert.equal(url, "https://open.bigmodel.cn/api/paas/v4/chat/completions");
  assert.equal(options.headers.Authorization, "Bearer test-zhipu-only");
  const body = JSON.parse(options.body);
  assert.equal(body.model, "glm-4.5-flash");
  assert.ok(body.messages.length >= 2);
  return Response.json({ model: "glm-4.5-flash", choices: [{ finish_reason: "stop", message: { content: JSON.stringify(fixture) } }] });
};
try {
  for (const [handler, body] of [
    [chat, { messages: [{ role: "user", content: "My child is finding mathematics harder." }] }],
    [review, { report: "A provisional learning-support report." }],
    [diagnose, { answers: { concern: "Mathematics performance" } }],
    [ablation, { system: "full_grade_agent", answers: { concern: "Mathematics performance" } }],
  ]) {
    const response = await handler({ request: request(body), env: zhipu });
    assert.equal(response.status, 200);
    const result = await response.json();
    assert.equal(result.model, "glm-4.5-flash");
    assert.equal(result.provider, "zhipu");
    assert.ok(!JSON.stringify(result).includes("test-zhipu-only"));
    const unavailable = await handler({ request: request(body), env: { AI_PROVIDER: "zhipu", DEEPSEEK_API_KEY: "wrong-provider" } });
    assert.equal(unavailable.status, 503);
  }
  assert.equal(calls, 4);
  console.log("Provider routing passed: all four routes, default rollback and cross-provider credential isolation.");
} finally {
  globalThis.fetch = originalFetch;
}
