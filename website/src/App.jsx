import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpenText,
  Brain,
  CaretUp,
  ChartLineUp,
  Check,
  Circle,
  ClipboardText,
  Compass,
  Database,
  FileText,
  GraduationCap,
  Info,
  Lightbulb,
  Lock,
  Microphone,
  Paperclip,
  PaperPlaneTilt,
  ShieldCheck,
  Sparkle,
  SpinnerGap,
  Student,
  UsersThree,
  X,
} from "@phosphor-icons/react";
import "./styles.css";
import { Consultation } from "./Consultation.jsx";

const evidenceStages = [
  { label: "Predict", detail: "Weighted model comparison", icon: ChartLineUp },
  { label: "Explain", detail: "SHAP diagnostic priority", icon: Compass },
  { label: "Estimate", detail: "DML conditional effects", icon: Brain },
  { label: "Diagnose", detail: "Context-aware dialogue", icon: ClipboardText },
];

function Brand({ compact = false }) {
  return (
    <div className={`brand ${compact ? "brand--compact" : ""}`}>
      <span className="brand__mark"><GraduationCap weight="duotone" /></span>
      <span>
        <strong>GRADE-Agent</strong>
        <small>Learning support through conversation</small>
      </span>
    </div>
  );
}

function Cover({ onEnter, onEvidence }) {
  return (
    <main className="cover">
      <div className="cover__image" aria-hidden="true" />
      <div className="cover__shade" aria-hidden="true" />
      <header className="cover__nav">
        <Brand />
        <div className="cover__navActions">
          <span className="status"><span /> PISA 2022 evidence connected</span>
          <button className="iconButton iconButton--light" aria-label="Open evidence" title="Open evidence" onClick={onEvidence}>
            <Database />
          </button>
        </div>
      </header>

      <section className="cover__content">
        <div className="cover__kicker"><Sparkle weight="fill" /> A diagnostic agent that listens before it explains</div>
        <h1>GRADE-Agent</h1>
        <p className="cover__fullname">Grade-performance Reasoning, Analysis, Diagnosis and Explanation Agent</p>
        <p className="cover__lead">
          Turn predictive, explainable and causal machine learning evidence into a careful multi-turn conversation about how a student learns.
        </p>
        <div className="cover__actions">
          <button className="primaryButton" onClick={onEnter}>开始交流 <ArrowRight weight="bold" /></button>
          <button className="textButton textButton--light" onClick={onEvidence}>Explore the evidence <ArrowRight /></button>
        </div>
      </section>

      <div className="cover__notation" aria-hidden="true">
        <span>Y = theta D + g(X) + epsilon</span>
        <span>10 plausible values</span>
        <span>n = 5,760</span>
      </div>

      <section className="evidenceRibbon" aria-label="Evidence workflow">
        {evidenceStages.map(({ label, detail, icon: Icon }, index) => (
          <div className="evidenceRibbon__item" key={label}>
            <span className="evidenceRibbon__index">0{index + 1}</span>
            <Icon weight="duotone" />
            <span><strong>{label}</strong><small>{detail}</small></span>
          </div>
        ))}
      </section>
    </main>
  );
}

function EvidenceDrawer({ onClose }) {
  return (
    <div className="drawerBackdrop" role="presentation" onClick={onClose}>
      <aside className="evidenceDrawer" role="dialog" aria-modal="true" aria-label="Evidence basis" onClick={(event) => event.stopPropagation()}>
        <header>
          <div><span className="sectionEyebrow">Evidence basis</span><h2>What constrains the diagnosis</h2></div>
          <button className="iconButton" onClick={onClose} aria-label="Close evidence drawer"><X /></button>
        </header>
        <div className="evidenceDrawer__study">
          <div><strong>5,760</strong><span>Japanese students</span></div>
          <div><strong>10</strong><span>plausible values</span></div>
          <div><strong>0.501</strong><span>weighted R2</span></div>
        </div>
        <div className="evidenceDrawer__layers">
          <article><ChartLineUp /><span><strong>Predictive layer</strong><small>LightGBM led the five-model comparison on the held-out split.</small></span></article>
          <article><Compass /><span><strong>Explanatory layer</strong><small>SHAP ranks dimensions for follow-up; it does not establish effects.</small></span></article>
          <article><Brain /><span><strong>Causal ML layer</strong><small>DML estimates conditional effects under stated identification assumptions.</small></span></article>
          <article><ShieldCheck /><span><strong>Diagnostic audit</strong><small>Educational meaning and temporal context can override a literal coefficient reading.</small></span></article>
        </div>
        <figure className="evidenceDrawer__figure">
          <img src="/evidence-matrix.png" alt="Matrix comparing predictive, SHAP and DML evidence for diagnostic variables" />
          <figcaption>Evidence convergence determines priority, not any single model output.</figcaption>
        </figure>
      </aside>
    </div>
  );
}

export function App() {
  const requestedView = new URLSearchParams(window.location.search).get("view");
  const [screen, setScreen] = useState(["agent", "report", "review"].includes(requestedView) ? "agent" : "cover");
  const [evidenceOpen, setEvidenceOpen] = useState(false);

  return (
    <>
      {screen === "cover" ? <Cover onEnter={() => setScreen("agent")} onEvidence={() => setEvidenceOpen(true)} /> : <Consultation Brand={Brand} onExit={() => setScreen("cover")} onEvidence={() => setEvidenceOpen(true)} />}
      {evidenceOpen && <EvidenceDrawer onClose={() => setEvidenceOpen(false)} />}
    </>
  );
}
