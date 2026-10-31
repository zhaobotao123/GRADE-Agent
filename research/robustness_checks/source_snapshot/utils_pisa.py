from __future__ import annotations

import importlib.util
import logging
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def optional_module(name: str) -> Any | None:
    if importlib.util.find_spec(name) is None:
        return None
    return __import__(name)


def setup_logging(out_dir: Path) -> logging.Logger:
    out_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("grade_agent_formal")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    run_handler = logging.FileHandler(out_dir / "run_log.txt", mode="w", encoding="utf-8")
    run_handler.setFormatter(formatter)
    error_handler = logging.FileHandler(out_dir / "error_log.txt", mode="w", encoding="utf-8")
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.addHandler(run_handler)
    logger.addHandler(error_handler)
    logger.addHandler(stream_handler)
    return logger


def check_data_path(data_path: str, logger: logging.Logger) -> bool:
    path = Path(data_path)
    if path.exists():
        return True
    msg = (
        f"Data file not found: {data_path}\n"
        "Please modify DATA_PATH in config.py to the actual PISA student .sav file path."
    )
    logger.error(msg)
    print(msg)
    return False


def read_sav_metadata(data_path: str) -> tuple[list[str], Any]:
    pyreadstat = optional_module("pyreadstat")
    if pyreadstat is None:
        raise ImportError("pyreadstat is required. Please run: pip install -r requirements.txt")
    _, meta = pyreadstat.read_sav(data_path, metadataonly=True)
    return list(meta.column_names), meta


def read_sav_selected(data_path: str, usecols: list[str]) -> pd.DataFrame:
    pyreadstat = optional_module("pyreadstat")
    df, _ = pyreadstat.read_sav(
        data_path,
        usecols=usecols,
        apply_value_formats=False,
        user_missing=False,
    )
    return df


def split_found_missing(candidates: list[str], columns: list[str]) -> tuple[list[str], list[str]]:
    colset = set(columns)
    return [x for x in candidates if x in colset], [x for x in candidates if x not in colset]


def find_replicate_weights(columns: list[str]) -> list[str]:
    direct = [f"W_FSTURWT{i}" for i in range(1, 81) if f"W_FSTURWT{i}" in columns]
    if direct:
        return direct
    alt = [f"W_FSTR{i}" for i in range(1, 81) if f"W_FSTR{i}" in columns]
    if alt:
        return alt
    return [
        col
        for col in columns
        if col.upper().startswith("W_FST") and ("RWT" in col.upper() or "REP" in col.upper())
    ]


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    mask = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if mask.sum() == 0:
        return float("nan")
    return float(np.average(values[mask], weights=weights[mask]))


def weighted_rmse(y_true: np.ndarray, y_pred: np.ndarray, weights: np.ndarray) -> float:
    err2 = (np.asarray(y_true) - np.asarray(y_pred)) ** 2
    return math.sqrt(weighted_mean(err2, np.asarray(weights)))


def weighted_mae(y_true: np.ndarray, y_pred: np.ndarray, weights: np.ndarray) -> float:
    err = np.abs(np.asarray(y_true) - np.asarray(y_pred))
    return weighted_mean(err, np.asarray(weights))


def weighted_r2(y_true: np.ndarray, y_pred: np.ndarray, weights: np.ndarray) -> float:
    y = np.asarray(y_true)
    pred = np.asarray(y_pred)
    w = np.asarray(weights)
    mask = np.isfinite(y) & np.isfinite(pred) & np.isfinite(w) & (w > 0)
    if mask.sum() == 0:
        return float("nan")
    y_bar = np.average(y[mask], weights=w[mask])
    ss_res = np.sum(w[mask] * (y[mask] - pred[mask]) ** 2)
    ss_tot = np.sum(w[mask] * (y[mask] - y_bar) ** 2)
    return float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")


def infer_feature_types(df: pd.DataFrame, feature_cols: list[str]) -> tuple[list[str], list[str]]:
    numeric_cols: list[str] = []
    categorical_cols: list[str] = []
    for col in feature_cols:
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col]):
            categorical_cols.append(col)
        elif df[col].nunique(dropna=True) <= 12:
            categorical_cols.append(col)
        else:
            numeric_cols.append(col)
    return numeric_cols, categorical_cols


def make_onehot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False, min_frequency=20)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_preprocessor(
    numeric_cols: list[str],
    categorical_cols: list[str],
    scale_numeric: bool = False,
) -> ColumnTransformer:
    numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", make_onehot_encoder()),
        ]
    )
    return ColumnTransformer(
        [
            ("num", Pipeline(numeric_steps), numeric_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def get_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    names: list[str] = []
    for name, transformer, cols in preprocessor.transformers_:
        if name == "remainder" or transformer == "drop":
            continue
        last = transformer.steps[-1][1] if isinstance(transformer, Pipeline) else transformer
        if hasattr(last, "get_feature_names_out"):
            try:
                names.extend(list(last.get_feature_names_out(cols)))
            except TypeError:
                names.extend(list(last.get_feature_names_out()))
        else:
            names.extend(list(cols))
    return names


def pass_sample_weight_if_possible(pipe: Pipeline, X: pd.DataFrame, y: pd.Series, weights: np.ndarray) -> Pipeline:
    try:
        pipe.fit(X, y, model__sample_weight=weights)
    except TypeError:
        pipe.fit(X, y)
    return pipe


def pool_prediction_metrics(metrics_by_pv: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, group in metrics_by_pv.groupby("model"):
        rows.append(
            {
                "model": model,
                "weighted_r2_mean": group["weighted_r2"].mean(),
                "weighted_r2_sd": group["weighted_r2"].std(ddof=1),
                "weighted_rmse_mean": group["weighted_rmse"].mean(),
                "weighted_rmse_sd": group["weighted_rmse"].std(ddof=1),
                "weighted_mae_mean": group["weighted_mae"].mean(),
                "weighted_mae_sd": group["weighted_mae"].std(ddof=1),
                "pv_count": group["plausible_value"].nunique(),
            }
        )
    return pd.DataFrame(rows).sort_values("weighted_rmse_mean")


def pool_importance(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["feature", value_col, "pv_count"])
    pooled = (
        df.groupby("feature", as_index=False)
        .agg(**{value_col: (value_col, "mean"), "pv_count": ("plausible_value", "nunique")})
        .sort_values(value_col, ascending=False)
    )
    return pooled


def pool_dml_results(dml_by_pv: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for treatment, group in dml_by_pv.groupby("treatment"):
        g = group.dropna(subset=["coef", "std_error"])
        m = len(g)
        if m == 0:
            continue
        coef = g["coef"].to_numpy(float)
        se = g["std_error"].to_numpy(float)
        theta_bar = float(np.mean(coef))
        within_var = float(np.mean(se**2))
        between_var = float(np.var(coef, ddof=1)) if m > 1 else 0.0
        total_var = within_var + (1.0 + 1.0 / m) * between_var
        pooled_se = math.sqrt(total_var) if total_var >= 0 else float("nan")
        z = theta_bar / pooled_se if pooled_se and np.isfinite(pooled_se) else float("nan")
        p_value = float(2 * (1 - stats.norm.cdf(abs(z)))) if np.isfinite(z) else float("nan")
        signs = np.sign(coef[np.abs(coef) > 1e-12])
        direction_consistent = bool(len(signs) > 0 and np.all(signs == signs[0]))
        sig_count = int((g["p_value"] < 0.05).sum())
        if direction_consistent and p_value < 0.05:
            stability_note = "stable_adjusted_signal"
        elif not direction_consistent:
            stability_note = "unstable_across_pv"
        else:
            stability_note = "weak_or_context_sensitive_signal"
        rows.append(
            {
                "treatment": treatment,
                "coef_pooled": theta_bar,
                "std_error_pooled": pooled_se,
                "p_value_pooled": p_value,
                "within_var": within_var,
                "between_var": between_var,
                "n_mean": float(g["n"].mean()),
                "signal_direction": "positive" if theta_bar > 0 else "negative" if theta_bar < 0 else "zero",
                "pv_count": m,
                "significant_pv_count": sig_count,
                "direction_consistent": direction_consistent,
                "stability_note": stability_note,
            }
        )
    return pd.DataFrame(rows).sort_values("p_value_pooled")


def make_stability_check(dml_by_pv: pd.DataFrame, pooled: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pooled_lookup = pooled.set_index("treatment").to_dict("index") if not pooled.empty else {}
    for treatment, group in dml_by_pv.groupby("treatment"):
        coefs = group["coef"].to_numpy(float)
        signs = np.sign(coefs[np.isfinite(coefs) & (np.abs(coefs) > 1e-12)])
        direction_consistent = bool(len(signs) > 0 and np.all(signs == signs[0]))
        sig_count = int((group["p_value"] < 0.05).sum())
        pooled_row = pooled_lookup.get(treatment, {})
        pooled_p = pooled_row.get("p_value_pooled", np.nan)
        if direction_consistent and pd.notna(pooled_p) and pooled_p < 0.05:
            stability_label = "stable_adjusted_signal"
        elif not direction_consistent:
            stability_label = "unstable_across_pv"
        else:
            stability_label = "weak_or_context_sensitive_signal"
        rows.append(
            {
                "treatment": treatment,
                "pv_count": group["plausible_value"].nunique(),
                "direction_consistent": direction_consistent,
                "significant_pv_count": sig_count,
                "pooled_p_value": pooled_p,
                "stability_label": stability_label,
            }
        )
    return pd.DataFrame(rows)


def plot_top20(df: pd.DataFrame, value_col: str, label_col: str, title: str, output_path: Path) -> None:
    if df.empty:
        return
    top = df.head(20).iloc[::-1]
    plt.figure(figsize=(10, 7))
    plt.barh(top[label_col].astype(str), top[value_col], color="#3b6ea8")
    plt.xlabel(value_col)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def plot_dml_pooled(pooled: pd.DataFrame, png_path: Path, pdf_path: Path) -> None:
    if pooled.empty:
        return
    df = pooled.copy()
    df["ci_low"] = df["coef_pooled"] - 1.96 * df["std_error_pooled"]
    df["ci_high"] = df["coef_pooled"] + 1.96 * df["std_error_pooled"]
    df = df.sort_values("coef_pooled")
    y = np.arange(len(df))
    plt.figure(figsize=(9, max(5, len(df) * 0.42 + 2)))
    plt.errorbar(
        df["coef_pooled"],
        y,
        xerr=[df["coef_pooled"] - df["ci_low"], df["ci_high"] - df["coef_pooled"]],
        fmt="o",
        color="#1f4e79",
        ecolor="#333333",
        elinewidth=1.2,
        capsize=4,
    )
    plt.axvline(0, color="#888888", linestyle="--", linewidth=1)
    plt.yticks(y, df["treatment"])
    plt.xlabel("Pooled adjusted effect estimate with 95% CI")
    plt.title("DML Pooled Adjusted Effects Across Plausible Values")
    plt.tight_layout()
    plt.savefig(png_path, dpi=240)
    plt.savefig(pdf_path)
    plt.close()


def generate_agent_rules(pooled: pd.DataFrame, stability: pd.DataFrame) -> pd.DataFrame:
    if pooled.empty:
        return pd.DataFrame()
    stab = stability.set_index("treatment").to_dict("index") if not stability.empty else {}
    rows = []
    for _, row in pooled.iterrows():
        treatment = row["treatment"]
        stable = stab.get(treatment, {}).get("direction_consistent", False)
        coef = row["coef_pooled"]
        p = row["p_value_pooled"]
        if p < 0.05 and coef > 0 and stable:
            signal_type = "stable_positive_adjusted_signal"
            diagnostic_meaning = "潜在保护性诊断信号"
            agent_rule = "作为潜在保护性诊断信号，追问该因素是否稳定存在，并结合学生学习情境解释。"
            report_expression = "在控制学生个体、家庭背景和学校环境等协变量后，该因素与数学表现呈稳定正向调整关联，可作为学习支持中的潜在保护性信号。"
        elif p < 0.05 and coef < 0 and stable:
            signal_type = "stable_negative_adjusted_signal"
            diagnostic_meaning = "潜在风险诊断信号"
            agent_rule = "作为潜在风险诊断信号，优先追问该因素的具体表现、持续时间和可干预空间。"
            report_expression = "在控制学生个体、家庭背景和学校环境等协变量后，该因素与数学表现呈稳定负向调整关联，可作为学业风险诊断中的重点关注信号。"
        elif p < 0.05 and not stable:
            signal_type = "statistically_significant_but_unstable_signal"
            diagnostic_meaning = "统计显著但稳定性不足"
            agent_rule = "不直接作为主要原因，需要继续追问具体学习情境，并在报告中加入解释边界。"
            report_expression = "该因素在总体估计中呈现一定调整关联，但在不同 plausible values 下稳定性不足，诊断中应谨慎使用。"
        else:
            signal_type = "weak_or_context_sensitive_signal"
            diagnostic_meaning = "弱信号或情境敏感信号"
            agent_rule = "仅作为辅助诊断信息，不直接作为主要原因，需要结合更多学生情境信息判断。"
            report_expression = "该因素在当前模型设定下未表现出稳定调整效应，诊断中应谨慎解释，仅作为辅助信息使用。"
        rows.append(
            {
                "treatment": treatment,
                "coef_pooled": coef,
                "std_error_pooled": row["std_error_pooled"],
                "p_value_pooled": p,
                "signal_type": signal_type,
                "diagnostic_meaning": diagnostic_meaning,
                "agent_rule": agent_rule,
                "report_expression": report_expression,
            }
        )
    return pd.DataFrame(rows)


def save_sample_description(
    df: pd.DataFrame,
    variables: list[str],
    country_code: str | None,
    out_path: Path,
) -> None:
    rows = []
    for col in variables:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().sum() > 0:
            mean = s.mean()
            sd = s.std()
        else:
            mean = np.nan
            sd = np.nan
        rows.append(
            {
                "variable": col,
                "country_filter": country_code if country_code is not None else "all",
                "n_non_missing": int(df[col].notna().sum()),
                "n_total": int(len(df)),
                "mean_if_numeric": mean,
                "sd_if_numeric": sd,
                "missing_rate": float(df[col].isna().mean()),
            }
        )
    pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8-sig")


def write_paper_draft(
    out_path: Path,
    metrics_pooled: pd.DataFrame,
    dml_pooled: pd.DataFrame,
    rule_map: pd.DataFrame,
) -> None:
    best_model_text = "尚无可用模型结果"
    if not metrics_pooled.empty:
        best = metrics_pooled.iloc[0]
        best_model_text = (
            f"跨 plausible values 汇总后，{best['model']} 的加权 RMSE 均值较低"
            f"（weighted RMSE mean = {best['weighted_rmse_mean']:.3f}），可作为主要预测模型候选。"
        )

    dml_text = "DML 汇总结果尚未生成。"
    if not dml_pooled.empty:
        sig_n = int((dml_pooled["p_value_pooled"] < 0.05).sum())
        dml_text = f"跨 plausible values 汇总后，共有 {sig_n} 个候选因素在当前设定下呈现统计显著的调整关联。"

    rule_text = "智能体规则映射尚未生成。"
    if not rule_map.empty:
        rule_text = f"根据汇总 DML 结果和稳定性检查，已生成 {len(rule_map)} 条 GRADE-Agent 诊断规则映射草案。"

    content = f"""# GRADE-Agent 正式实验结果草稿

## 数据预处理

本研究使用 PISA 2022 学生问卷数据，先读取 SPSS 元数据并检查候选变量、数学 plausible values、学生最终权重和重复权重是否存在。预处理阶段仅读取必要变量，将 SPSS 声明的缺失值尽可能转换为缺失，并删除缺失率超过阈值的候选解释变量。ID、权重和 plausible values 不作为普通预测特征进入模型。

## 预测模型结果

对 PV1MATH 至 PV10MATH 分别训练预测模型，并使用同一组训练/测试索引进行比较。模型评价使用学生最终权重计算加权 R2、加权 RMSE 和加权 MAE。{best_model_text}

## 模型解释结果

研究优先选择预测表现较好的树模型进行解释，输出跨 plausible values 汇总的特征重要性；若 SHAP 可用，则进一步输出跨 PV 汇总的 SHAP 重要性。相关变量可作为 GRADE-Agent 追问顺序和诊断关注点的预测证据来源。

## DML 调整效应结果

本研究对每个候选 treatment 和每个 plausible value 分别估计 DML 调整效应，并使用 Rubin-style pooling 对 10 个 plausible values 的系数和标准误进行汇总。{dml_text}

需要强调的是，PISA 是横截面观测数据，DML 结果不应表述为严格因果证明。本文将其解释为在控制高维协变量后的调整效应或 evidence-informed diagnostic signals。

## GRADE-Agent 规则映射

{rule_text} 规则将因素划分为稳定正向调整信号、稳定负向调整信号、统计显著但稳定性不足信号，以及弱信号或情境敏感信号。GRADE-Agent 使用这些规则辅助多轮诊断追问，但不替代教师和教育专家判断。

## 解释边界

所有结论均应使用“调整效应”“调整关联”“诊断信号”等表述。正式论文中可进一步扩展重复权重推断、学校问卷合并、多国家比较和低表现学生分类任务。
"""
    out_path.write_text(content, encoding="utf-8")
