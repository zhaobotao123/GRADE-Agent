// Server-only provider selection. Never import this module into the browser bundle.
export function getLlmConfig(env) {
  const provider = String(env.AI_PROVIDER || "deepseek").trim().toLowerCase();
  if (provider === "zhipu") {
    return {
      provider,
      apiKey: env.ZHIPU_API_KEY,
      endpoint: "https://open.bigmodel.cn/api/paas/v4/chat/completions",
      model: env.ZHIPU_MODEL || "glm-4.5-flash",
    };
  }
  if (provider === "deepseek") {
    return {
      provider,
      apiKey: env.DEEPSEEK_API_KEY,
      endpoint: "https://api.deepseek.com/chat/completions",
      model: env.DEEPSEEK_MODEL || "deepseek-v4-pro",
    };
  }
  return { provider, apiKey: undefined };
}
