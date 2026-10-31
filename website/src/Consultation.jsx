import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Check, Circle, ClipboardText, Database, GraduationCap, Info, Lock, PaperPlaneTilt, SpinnerGap } from "@phosphor-icons/react";

const domains = [
  ["trajectory", "学习表现的变化", "Changes in performance"], ["confidence", "做题时的信心与方法", "Confidence and approach"],
  ["classroom", "课堂情况", "Classroom circumstances"], ["support_timing", "已经获得的帮助", "Help already received"],
  ["context_safety", "近期变化与安全", "Recent changes and safety"],
];
export function Consultation({ Brand, onExit, onEvidence }) {
  const [messages, setMessages] = useState([]), [turn, setTurn] = useState(null);
  const [draft, setDraft] = useState(""), [loading, setLoading] = useState(false), [error, setError] = useState("");
  const pending = useRef(null), bottom = useRef(null), thread = useRef([]);
  const latest = [...messages].reverse().find(m => m.role === "user");
  const cn = !latest || /[\u3400-\u9fff]/.test(latest.content);
  const t = (zh, en) => cn ? zh : en;
  const confirmed = turn?.coverage?.confirmed || [];
  useEffect(() => { bottom.current?.scrollIntoView({ block: "nearest" }); }, [messages, loading]);
  useEffect(() => () => pending.current?.abort(), []);

  async function requestTurn(history) {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller; setLoading(true); setError("");
    try {
      const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages: history.map(({role,content}) => ({role,content})) }), signal: controller.signal });
      const payload = await response.json();
      if (!response.ok) throw new Error(cn ? (payload.errorCode === "MODEL_QUOTA_UNAVAILABLE" ? "模型账户暂无可用额度或资源包，暂时无法继续回复。你提供的信息仍在本次对话中。" : response.status === 429 ? "当前模型服务比较繁忙，请稍等后重试；你刚才的描述仍在对话中。" : payload.errorCode === "MODEL_NOT_CONFIGURED" ? "当前交流服务尚未配置完成，请稍后再试。" : "暂时没有收到完整回复，请重试；你刚才的描述仍在对话中。") : (payload.error || "The service is unavailable. Please retry."));
      if (typeof payload.reply !== "string" || !payload.reply.trim()) throw new Error(t("回复未完整生成，请重试。", "No complete reply was received. Please retry."));
      if (pending.current !== controller || controller.signal.aborted) return;
      const next = [...history, { role: "assistant", content: payload.reply, phase: payload.phase }];
      thread.current = next; setMessages(next); setTurn(payload);
    } catch (e) {
      if (!controller.signal.aborted && pending.current === controller) setError(e.message || t("连接失败，请重试。", "Connection failed. Please retry."));
    } finally {
      if (pending.current === controller) { pending.current = null; setLoading(false); }
    }
  }
  function send(value = draft) {
    const content = value.trim(); if (!content || pending.current) return;
    // An unanswered turn must be retried or explicitly continued, not duplicated.
    const history = [...thread.current, { role: "user", content }]; thread.current = history;
    setMessages(history); setDraft(""); requestTurn(history);
  }
  function reset() {
    pending.current?.abort(); pending.current = null; thread.current = [];
    setMessages([]); setTurn(null); setDraft(""); setError(""); setLoading(false);
  }
  function stop() {
    pending.current?.abort(); pending.current = null; setLoading(false);
    setError(t("已停止等待回复，你的描述已保留，可以重试或继续补充。", "Stopped waiting. Your message is preserved; retry or add more information."));
  }
  return <main className="agentPage">
    <header className="appTopbar"><Brand compact /><div><span className="status status--dark"><span />{t("学习支持交流 · 研究原型", "Learning-support conversation · prototype")}</span><button className="textButton" onClick={reset}>{t("新交流", "New chat")}</button><button className="iconButton" onClick={onEvidence} aria-label={t("查看研究背景", "Research background")} title={t("查看研究背景", "Research background")}><Database /></button></div></header>
    <div className="consultationGrid">
      <aside className="consultationRail">
        <div className="caseIdentity"><span className="sectionEyebrow">{t("正在交流", "Current conversation")}</span><h1>{t("一起了解学习情况", "Understanding the learning situation")}</h1><p>{t("从你观察到的事情说起就好", "Begin with what you have noticed")}</p></div>
        <div className="domainList" aria-label={t("交流涉及的方面，不是评分", "Conversation topics, not scores")}>
          {domains.map(([key,zh,en]) => { const done = confirmed.includes(key), active = turn?.phase === "question" && turn?.questionFocus === key;
            return <div key={key} className={`domainItem domainItem--${done ? "confirmed" : active ? "active" : "missing"}`}><span className="domainItem__icon">{done ? <Check weight="bold" /> : active ? <span /> : <Circle />}</span><div><strong>{t(zh,en)}</strong><small>{done ? t("已谈到", "Discussed") : active ? t("当前问题", "Current question") : t("按需要了解", "Explore if relevant")}</small></div></div>;
          })}
        </div>
        <div className="consultationRail__bottom"><button className="railAction" onClick={reset}><ClipboardText />{t("开始新的交流", "New conversation")}</button><button className="railAction" onClick={onExit}><ArrowLeft />{t("返回首页", "Return to home")}</button></div>
      </aside>
      <section className="conversationCanvas">
        <header className="sufficiencyHeader"><div><strong>{t("先了解，再一起梳理", "Understand first, then reflect together")}</strong><span>{t("每次问一个关键问题，不必一次讲全", "One useful question at a time")}</span></div></header>
        <div className="conversationThread" aria-live="polite" aria-busy={loading}>
          {!messages.length && <div className="conversationWelcome"><span className="conversationWelcome__mark"><GraduationCap weight="duotone" /></span><span className="sectionEyebrow">{t("从最近的变化开始", "Begin with recent changes")}</span><h2>{t("孩子最近的数学学习怎么样？", "How has the student's mathematics learning been going?")}</h2><p>{t("可以说说最近的成绩、做题时的表现，或让你担心的事情。我会根据你的描述继续问，了解后用一小段话帮你梳理值得关注的方面和可以先做的事。", "Tell me about recent results, how the student approaches problems, or what concerns you. I will follow up and then offer a short, practical summary.")}</p></div>}
          {messages.map((m,i) => <article key={i} className={`dialogueTurn dialogueTurn--${m.role}${m.phase === "summary" ? " dialogueTurn--summary" : ""}`}>
            {m.role === "assistant" && <span className="dialogueAvatar"><GraduationCap weight="duotone" /></span>}
            <div className="dialogueBubble"><header><strong>{m.role === "user" ? t("你", "You") : "GRADE-Agent"}</strong><time>{m.role === "user" ? t("你的描述", "Your observations") : m.phase === "summary" ? t("初步梳理", "Initial summary") : m.phase === "safety_escalation" ? t("先关注安全", "Safety first") : t("进一步了解", "Follow-up")}</time></header><p>{m.content}</p></div>
          </article>)}
          {loading && <div className="agentThinking"><SpinnerGap /><span>{t("正在结合你提供的情况思考…", "Thinking about what you have shared…")}</span></div>}
          <div ref={bottom} />
        </div>
        <footer className="composerArea">
          {error && <div className="composerError" role="alert"><Info /><span>{error}</span><button type="button" className="textButton" onClick={() => requestTurn(thread.current)} disabled={loading}>{t("重试这次回复", "Retry this reply")}</button></div>}
          <p className="oneQuestionNote">{turn?.phase === "summary" ? t("这只是根据目前信息作的初步梳理。你可以补充情况，或继续聊聊建议如何落实。", "This is a provisional summary. Add information or ask how to carry out a suggestion.") : t("按你知道的回答就好，不清楚的也可以直接说。", "Answer in your own words; it is fine not to know.")}</p>
          <div className="composer"><textarea value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }} placeholder={t("说说你的观察，或补充新的情况…", "Share your observations or add new information…")} rows="3" aria-label={t("输入你的观察或补充", "Your observations or additional information")} /><div className="composerTools"><small>{t("Shift + Enter 换行", "Shift + Enter for a new line")}</small><button className="sendButton" onClick={() => send()} disabled={!draft.trim() || loading} aria-label={t("发送", "Send message")}><PaperPlaneTilt weight="fill" /></button></div></div>
          {loading ? <div className="suggestedReplies"><button type="button" onClick={stop}>{t("停止本次回复", "Stop this reply")}</button></div> : messages.length > 0 && <div className="suggestedReplies">
            <button type="button" onClick={() => send(t("请根据目前我提供的信息，用一小段话梳理值得关注的方面，以及可以先尝试的做法。不清楚的地方请保留判断。", "Please briefly summarize what deserves attention and what to try first, using only what I have shared and keeping unknowns open."))}>{t("先帮我梳理一下", "Summarize so far")}</button>
            <button type="button" onClick={() => send(turn?.phase === "summary" ? t("你刚才提到的建议，能举一个具体的做法吗？", "Could you give a practical example of the suggestion you just made?") : t("你还需要了解什么？请接着我刚才说的情况问。", "What else would help you understand this? Please follow up on what I have shared."))}>{turn?.phase === "summary" ? t("具体可以怎么做", "How can I try this?") : t("继续了解情况", "Continue the conversation")}</button>
          </div>}
        </footer>
      </section>
      <aside className="sessionSummary"><header><div><span className="sectionEyebrow">{t("交流提示", "Conversation notes")}</span><h2>{turn?.phase === "summary" ? t("可以继续补充", "Keep the conversation going") : t("不急着下结论", "No need to rush to a conclusion")}</h2></div></header><p className="summaryIntro">{t("最终梳理直接出现在对话里，不另生成报告。", "The summary appears in the conversation, not in a separate report.")}</p><section className="summarySection"><h3><Check />{t("你最近提到的情况", "Your recent observations")}</h3>{messages.filter(m => m.role === "user").length ? <ul>{messages.filter(m => m.role === "user").slice(-2).map((m,i) => <li key={i}>{m.content}</li>)}</ul> : <p className="summaryEmpty">{t("这里会记录你在交流中提供的信息。", "Your observations will appear here.")}</p>}</section><section className="summaryBoundary"><Lock /><div><strong>{t("一起核实，而不是确定归因", "Explore, rather than assume a cause")}</strong><p>{t("建议依据你提供的情况，不能确定成绩变化的原因。有安全或健康方面的担忧，应及时寻求相应专业人员帮助。", "Suggestions depend on what you share and do not establish a cause. Seek appropriate professional help for safety or health concerns.")}</p></div></section></aside>
    </div>
  </main>;
}
