from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np
import pandas as pd
import pyreadstat
import statsmodels.api as sm
from scipy.linalg import qr
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

import config


PROCESS_PVS = {
    "formulation": [f"PV{i}MPFS" for i in range(1, 11)],
    "employing": [f"PV{i}MPEM" for i in range(1, 11)],
    "interpretation": [f"PV{i}MPIN" for i in range(1, 11)],
    "reasoning": [f"PV{i}MPRE" for i in range(1, 11)],
}
BASELINE_CANDIDATES = [
    "ST004D01T", "AGE", "GRADE", "ESCS", "HOMEPOS", "ICTRES",
    "ST059Q02JA", "ST296Q01JA", "STUDYHMW", "EXPOFA", "EXPO21ST",
]


def weighted_mean(x, w):
    return float(np.average(x, weights=w))


def weighted_sd(x, w):
    mu = weighted_mean(x, w)
    return float(np.sqrt(np.average((x - mu) ** 2, weights=w)))


def weighted_z(x, w):
    sd = weighted_sd(x, w)
    return (x - weighted_mean(x, w)) / (sd if sd > 0 else 1.0)


def fit_residuals(y, x, groups):
    exog = sm.add_constant(x, has_constant="add")
    try:
        result = sm.MixedLM(y, exog, groups=groups).fit(
            reml=False, method="lbfgs", maxiter=300, disp=False
        )
        return y - np.asarray(result.fittedvalues), {
            "method": "mixedlm_random_school_intercept",
            "converged": bool(result.converged),
            "aic": float(result.aic), "bic": float(result.bic),
        }
    except Exception as exc:
        school = pd.get_dummies(pd.Series(groups), drop_first=True, dtype=float)
        exog_fe = np.column_stack([exog, school.to_numpy()])
        fitted = exog_fe @ np.linalg.lstsq(exog_fe, y, rcond=None)[0]
        return y - fitted, {
            "method": "school_fixed_effect_fallback", "converged": True,
            "aic": np.nan, "bic": np.nan, "fallback_reason": str(exc),
        }


def build_index(frame, pvs, x, groups, weights, label):
    residuals, diagnostics = [], []
    for pv in pvs:
        y = pd.to_numeric(frame[pv], errors="coerce").to_numpy(float)
        resid, info = fit_residuals(y, x, groups)
        residuals.append(resid)
        diagnostics.append({"index": label, "pv": pv, **info})
    return weighted_z(np.mean(np.column_stack(residuals), axis=1), weights), diagnostics


def main():
    rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    rcParams["axes.unicode_minus"] = False
    out = Path(config.OUT_DIR) / "mrle_extension"
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(out / "mrle_run_log.txt", encoding="utf-8"), logging.StreamHandler()],
    )
    log = logging.getLogger("mrle")
    _, meta = pyreadstat.read_sav(config.DATA_PATH, metadataonly=True)
    available = set(meta.column_names)
    baseline = [c for c in BASELINE_CANDIDATES if c in available]
    all_pvs = config.PV_MATH_VARS + [p for values in PROCESS_PVS.values() for p in values]
    missing = [p for p in all_pvs if p not in available]
    if missing:
        raise RuntimeError(f"Required plausible values are missing: {missing}")
    ids = ["CNT", "CNTSCHID", "CNTSTUID", config.FINAL_STUDENT_WEIGHT]
    usecols = ids + baseline + all_pvs
    log.info("Reading %d selected columns", len(usecols))
    frame, _ = pyreadstat.read_sav(config.DATA_PATH, usecols=usecols)
    frame = frame.loc[frame["CNT"].astype(str).str.strip() == config.COUNTRY_CODE].copy()
    frame = frame.dropna(subset=all_pvs + ["CNTSCHID", config.FINAL_STUDENT_WEIGHT])
    baseline = frame[baseline].isna().mean().loc[lambda s: s <= config.MISSING_RATE_THRESHOLD].index.tolist()
    numeric = frame[baseline].apply(pd.to_numeric, errors="coerce")
    imputed = SimpleImputer(strategy="median").fit_transform(numeric)
    varying = np.nanstd(imputed, axis=0) > 1e-10
    baseline = [name for name, keep in zip(baseline, varying) if keep]
    imputed = imputed[:, varying]
    # Retain an independent subset so the mixed-model fixed-effects design is full rank.
    _, r_matrix, pivots = qr(imputed, mode="economic", pivoting=True)
    tol = np.finfo(float).eps * max(imputed.shape) * abs(r_matrix[0, 0])
    rank = int(np.sum(np.abs(np.diag(r_matrix)) > tol))
    keep = sorted(pivots[:rank])
    baseline = [baseline[i] for i in keep]
    x = StandardScaler().fit_transform(imputed[:, keep])
    groups = frame["CNTSCHID"].astype(str).to_numpy()
    weights = pd.to_numeric(frame[config.FINAL_STUDENT_WEIGHT], errors="coerce").to_numpy(float)
    weights = np.where(np.isfinite(weights) & (weights > 0), weights, 1.0)
    log.info("Analytical sample n=%d in %d schools", len(frame), frame["CNTSCHID"].nunique())

    diagnostics = []
    mrle, info = build_index(frame, config.PV_MATH_VARS, x, groups, weights, "overall_mrle")
    diagnostics.extend(info)
    process_scores = {}
    for name, pvs in PROCESS_PVS.items():
        process_scores[name], info = build_index(frame, pvs, x, groups, weights, name)
        diagnostics.extend(info)
        log.info("Completed %s process index", name)

    math_mean = frame[config.PV_MATH_VARS].mean(axis=1).to_numpy(float)
    result = frame[ids].copy()
    result["MATH_MEAN_DESCRIPTIVE"] = math_mean
    result["MRLE"] = mrle
    for name, values in process_scores.items():
        result[f"MRLE_{name.upper()}"] = values
    q25, q75 = np.quantile(mrle, [0.25, 0.75])
    result["relative_performance_group"] = np.select(
        [mrle <= q25, mrle >= q75], ["below_expected", "above_expected"],
        default="within_expected_range",
    )
    matrix = np.column_stack(list(process_scores.values()))
    names = np.array(list(process_scores))
    result["strongest_process"] = names[np.argmax(matrix, axis=1)]
    result["weakest_process"] = names[np.argmin(matrix, axis=1)]
    result["process_gap"] = matrix.max(axis=1) - matrix.min(axis=1)
    score_median = float(np.median(math_mean))
    result["diagnostic_quadrant"] = np.select(
        [(math_mean >= score_median) & (mrle >= 0), (math_mean >= score_median) & (mrle < 0),
         (math_mean < score_median) & (mrle >= 0)],
        ["high_score_above_expected", "high_score_below_expected", "low_score_above_expected"],
        default="low_score_below_expected",
    )
    result.to_csv(out / "mrle_student_profiles.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(diagnostics).to_csv(out / "mrle_model_diagnostics_by_pv.csv", index=False, encoding="utf-8-sig")

    summary = []
    for col in ["MRLE"] + [f"MRLE_{n.upper()}" for n in process_scores]:
        v = result[col].to_numpy(float)
        summary.append({"measure": col, "n": len(v), "weighted_mean": weighted_mean(v, weights),
                        "weighted_sd": weighted_sd(v, weights), "minimum": v.min(),
                        "p25": np.quantile(v, .25), "median": np.median(v),
                        "p75": np.quantile(v, .75), "maximum": v.max()})
    pd.DataFrame(summary).to_csv(out / "mrle_summary.csv", index=False, encoding="utf-8-sig")
    for col, file in [("relative_performance_group", "mrle_group_distribution.csv"),
                      ("diagnostic_quadrant", "achievement_mrle_quadrants.csv"),
                      ("weakest_process", "weakest_process_distribution.csv")]:
        tab = result[col].value_counts().rename_axis(col).reset_index(name="n")
        tab["percent"] = tab.n / len(result) * 100
        tab.to_csv(out / file, index=False, encoding="utf-8-sig")

    colors = {"above_expected": "#83C5BE", "within_expected_range": "#FFD6A5", "below_expected": "#FFADAD"}
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    sample = np.random.default_rng(config.RANDOM_STATE).choice(len(result), min(3000, len(result)), replace=False)
    gs = result.relative_performance_group.to_numpy()[sample]
    group_labels = {"above_expected": "高于预期", "within_expected_range": "预期范围内", "below_expected": "低于预期"}
    for group in colors:
        mask = gs == group
        ax.scatter(math_mean[sample][mask], mrle[sample][mask], s=14, alpha=.5, color=colors[group], label=group_labels[group])
    ax.axhline(0, color="#555555", lw=1)
    ax.axvline(score_median, color="#555555", lw=1, ls="--")
    ax.set(xlabel="数学合理值均值（仅作描述）", ylabel="相对数学表现（MRLE）")
    ax.legend(frameon=False, ncol=3, fontsize=8, loc="upper center")
    fig.tight_layout()
    fig.savefig(out / "achievement_vs_mrle.png", dpi=300)
    fig.savefig(out / "achievement_vs_mrle.pdf")
    plt.close(fig)

    weakest = result.weakest_process.value_counts().reindex(list(process_scores), fill_value=0)
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    ax.bar(weakest.index, weakest.values / len(result) * 100,
           color=["#A8DADC", "#BDE0FE", "#CDB4DB", "#FFC8DD"])
    ax.set(ylabel="学生比例（%）", xlabel="最低相对数学过程维度")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "weakest_process_profile.png", dpi=300)
    fig.savefig(out / "weakest_process_profile.pdf")
    plt.close(fig)

    evidence = {
        "construct": "relative_mathematics_performance",
        "definition": "Standardized residual of observed mathematics performance relative to measured background and learning-opportunity conditions, adjusted for school clustering.",
        "allowed_expression": "Current performance is above or below the level expected under comparable measured conditions.",
        "prohibited_expression": "The student is intrinsically efficient or inefficient.",
        "required_boundary": "Population-calibrated evidence, not individual causal attribution or a fixed trait.",
        "baseline_variables": baseline, "n": len(result), "schools": int(frame.CNTSCHID.nunique()),
    }
    (out / "mrle_agent_evidence_object.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Completed MRLE extension at %s", out)


if __name__ == "__main__":
    main()
