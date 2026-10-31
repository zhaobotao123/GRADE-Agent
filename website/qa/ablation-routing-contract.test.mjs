import assert from "node:assert/strict";
import { CRITIC_BLOCK, DML_BLOCK, SYSTEM_PROMPTS } from "../functions/api/ablation.js";

const full = SYSTEM_PROMPTS.full_grade_agent;
const noCritic = SYSTEM_PROMPTS.grade_agent_no_critic;
const noDml = SYSTEM_PROMPTS.grade_agent_no_dml;
const neither = SYSTEM_PROMPTS.grade_agent_no_dml_no_critic;
const dmlOnly = SYSTEM_PROMPTS.grade_agent_no_critic;

for (const required of [
  /safeguarding disclosure/i,
  /conflicting sources/i,
  /documented temporary event/i,
  /information insufficiency/i,
  /hard gates/i,
  /candidate set only from factors positively supported/i,
  /must not supply an individual-level diagnosis/i,
  /information insufficiency is used only as the final fallback/i,
]) {
  assert.match(full, required, `Full-system routing omits: ${required}`);
}

for (const inheritedBoundary of [
  "safeguarding disclosure",
  "conflicting sources",
  "documented temporary event",
  "information insufficiency",
]) {
  assert.match(
    noCritic,
    new RegExp(inheritedBoundary, "i"),
    `No-critic routing omits shared boundary rule: ${inheritedBoundary}`,
  );
}

assert.match(full, /act as a diagnostic critic/i);
assert.match(noDml, /act as a diagnostic critic/i);
assert.doesNotMatch(noDml, /stable positive conditional-effect signal/i);
assert.doesNotMatch(neither, /act as a diagnostic critic/i);
assert.doesNotMatch(neither, /stable positive conditional-effect signal/i);
assert.match(dmlOnly, /DML evidence is enabled/i);

const stripFactorBlocks = (prompt) => prompt
  .replace(`\n\n${DML_BLOCK}`, "")
  .replace(`\n\n${CRITIC_BLOCK}`, "");
for (const prompt of [neither, dmlOnly, noDml, full]) {
  assert.equal(
    stripFactorBlocks(prompt),
    neither,
    "Factorial prompts differ outside the optional DML and critic blocks.",
  );
}
assert.match(full, /population evidence has not displaced a safety, conflict, transient-event/i);
assert.doesNotMatch(
  full,
  /Rank candidates by case-information match, then DML stability class/,
  "The obsolete DML-first routing rule reappeared.",
);

console.log("Ablation routing contract passed.");
