from __future__ import annotations

import copy
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNetCV, RidgeCV
from sklearn.model_selection import KFold, train_test_split
from sklearn.pipeline import Pipeline

import config
from utils_pisa import (
    build_preprocessor,
    check_data_path,
    find_replicate_weights,
    generate_agent_rules,
    get_feature_names,
    infer_feature_types,
    optional_module,
    pass_sample_weight_if_possible,
    plot_dml_pooled,
    plot_top20,
    pool_dml_results,
    pool_importance,
    pool_prediction_metrics,
    read_sav_metadata,
    read_sav_selected,
    save_sample_description,
    setup_logging,
    split_found_missing,
    weighted_mae,
    weighted_r2,
    weighted_rmse,
    make_stability_check,
    write_paper_draft,
)


def make_models(logger):
    models = {
        "RandomForestRegressor": (
            RandomForestRegressor(**config.RF_PARAMS),
            False,
        ),
        "ExtraTreesRegressor": (
            ExtraTreesRegressor(**config.EXTRA_TREES_PARAMS),
            False,
        ),
        "RidgeCV": (
            RidgeCV(alphas=np.logspace(-3, 3, 13)),
            True,
        ),
        "ElasticNetCV": (
            ElasticNetCV(
                l1_ratio=[0.1, 0.3, 0.5, 0.7, 0.9],
                alphas=np.logspace(-3, 1, 20),
                cv=5,
                random_state=config.RANDOM_STATE,
                max_iter=5000,
            ),
            True,
        ),
    }
    if optional_module("lightgbm") is not None:
        from lightgbm import LGBMRegressor

        models["LGBMRegressor"] = (LGBMRegressor(**config.LGBM_PARAMS), False)
    else:
        logger.warning("lightgbm is not installed; LGBMRegressor will be skipped.")
    return models


def fit_predict_models_for_pv(
    pv: str,
    df: pd.DataFrame,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    feature_cols: list[str],
    numeric_cols: list[str],
    categorical_cols: list[str],
    weight_col: str,
    logger,
):
    metrics = []
    fitted = {}
    models = make_models(logger)

    train_mask = df.index.isin(train_idx) & df[pv].notna()
    test_mask = df.index.isin(test_idx) & df[pv].notna()
    X_train = df.loc[train_mask, feature_cols]
    y_train = df.loc[train_mask, pv]
    w_train = df.loc[train_mask, weight_col].to_numpy(float)
    X_test = df.loc[test_mask, feature_cols]
    y_test = df.loc[test_mask, pv]
    w_test = df.loc[test_mask, weight_col].to_numpy(float)

    for model_name, (model, scale_numeric) in models.items():
        try:
            logger.info("Training %s for %s", model_name, pv)
            pipe = Pipeline(
                [
                    ("preprocess", build_preprocessor(numeric_cols, categorical_cols, scale_numeric)),
                    ("model", copy.deepcopy(model)),
                ]
            )
            pipe = pass_sample_weight_if_possible(pipe, X_train, y_train, w_train)
            pred = pipe.predict(X_test)
            metrics.append(
                {
                    "plausible_value": pv,
                    "model": model_name,
                    "weighted_r2": weighted_r2(y_test.to_numpy(float), pred, w_test),
                    "weighted_rmse": weighted_rmse(y_test.to_numpy(float), pred, w_test),
                    "weighted_mae": weighted_mae(y_test.to_numpy(float), pred, w_test),
                    "train_n": int(len(X_train)),
                    "test_n": int(len(X_test)),
                }
            )
            fitted[model_name] = pipe
        except Exception as exc:
            logger.warning("Model failed for %s/%s: %s", pv, model_name, exc)
            logger.debug(traceback.format_exc())

    return pd.DataFrame(metrics), fitted, X_train, w_train


def choose_tree_model(fitted: dict[str, Pipeline]) -> tuple[str | None, Pipeline | None]:
    if "LGBMRegressor" in fitted:
        return "LGBMRegressor", fitted["LGBMRegressor"]
    if "RandomForestRegressor" in fitted:
        return "RandomForestRegressor", fitted["RandomForestRegressor"]
    return None, None


def collect_feature_importance(pv: str, model_name: str, pipe: Pipeline) -> pd.DataFrame:
    model = pipe.named_steps["model"]
    if not hasattr(model, "feature_importances_"):
        return pd.DataFrame()
    names = get_feature_names(pipe.named_steps["preprocess"])
    values = np.asarray(model.feature_importances_)
    if len(names) != len(values):
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "plausible_value": pv,
            "model": model_name,
            "feature": names,
            "importance": values,
        }
    )


def collect_shap_importance(
    pv: str,
    model_name: str,
    pipe: Pipeline,
    X_train: pd.DataFrame,
    weights: np.ndarray,
    logger,
) -> pd.DataFrame:
    if optional_module("shap") is None:
        return pd.DataFrame()
    try:
        import shap

        n = min(config.SHAP_MAX_N, len(X_train))
        prob = weights / weights.sum() if np.isfinite(weights).all() and weights.sum() > 0 else None
        sample_idx = np.random.default_rng(config.RANDOM_STATE).choice(
            np.arange(len(X_train)), size=n, replace=False, p=prob
        )
        X_sample = X_train.iloc[sample_idx]
        transformed = pipe.named_steps["preprocess"].transform(X_sample)
        names = get_feature_names(pipe.named_steps["preprocess"])
        explainer = shap.TreeExplainer(pipe.named_steps["model"])
        shap_values = explainer.shap_values(transformed)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        mean_abs = np.abs(shap_values).mean(axis=0)
        return pd.DataFrame(
            {
                "plausible_value": pv,
                "model": model_name,
                "feature": names,
                "mean_abs_shap": mean_abs,
            }
        )
    except Exception as exc:
        logger.warning("SHAP failed for %s/%s: %s", pv, model_name, exc)
        with open(Path(config.OUT_DIR) / "shap_errors.txt", "a", encoding="utf-8") as f:
            f.write(f"{pv},{model_name},{exc}\n")
        return pd.DataFrame()


def dml_learner(logger):
    if optional_module("lightgbm") is not None:
        from lightgbm import LGBMRegressor

        return LGBMRegressor(**config.LGBM_PARAMS), "LGBMRegressor"
    return RandomForestRegressor(**config.RF_PARAMS), "RandomForestRegressor"


def weighted_residualized_dml(
    data: pd.DataFrame,
    pv: str,
    treatment: str,
    x_cols: list[str],
    weight_col: str,
    cluster_col: str | None,
    logger,
) -> dict:
    d = pd.to_numeric(data[treatment], errors="coerce")
    y = pd.to_numeric(data[pv], errors="coerce")
    w = pd.to_numeric(data[weight_col], errors="coerce")
    valid = y.notna() & d.notna() & w.notna() & (w > 0)
    analysis_cols = [pv, treatment, weight_col] + x_cols
    if cluster_col and cluster_col in data.columns:
        analysis_cols.append(cluster_col)
        valid &= data[cluster_col].notna()
    sub = data.loc[valid, list(dict.fromkeys(analysis_cols))].copy()
    if len(sub) < config.MIN_DML_N:
        raise ValueError(f"too few rows after DML filtering: {len(sub)}")
    if pd.to_numeric(sub[treatment], errors="coerce").nunique(dropna=True) < config.MIN_TREATMENT_UNIQUE:
        raise ValueError("treatment has too little numeric variation")

    numeric_cols, categorical_cols = infer_feature_types(sub, x_cols)
    pre = build_preprocessor(numeric_cols, categorical_cols, scale_numeric=True)
    X = sub[x_cols]
    y_arr = pd.to_numeric(sub[pv], errors="coerce").to_numpy(float)
    d_arr = pd.to_numeric(sub[treatment], errors="coerce").to_numpy(float)
    w_arr = pd.to_numeric(sub[weight_col], errors="coerce").to_numpy(float)

    base_learner, learner_name = dml_learner(logger)
    y_hat = np.full(len(sub), np.nan, dtype=float)
    d_hat = np.full(len(sub), np.nan, dtype=float)
    folds = KFold(
        n_splits=config.DML_N_FOLDS,
        shuffle=True,
        random_state=config.RANDOM_STATE,
    )
    for train_pos, test_pos in folds.split(X):
        y_pipe = Pipeline(
            [("preprocess", copy.deepcopy(pre)), ("model", copy.deepcopy(base_learner))]
        )
        d_pipe = Pipeline(
            [("preprocess", copy.deepcopy(pre)), ("model", copy.deepcopy(base_learner))]
        )
        y_pipe = pass_sample_weight_if_possible(
            y_pipe,
            X.iloc[train_pos],
            pd.Series(y_arr[train_pos]),
            w_arr[train_pos],
        )
        d_pipe = pass_sample_weight_if_possible(
            d_pipe,
            X.iloc[train_pos],
            pd.Series(d_arr[train_pos]),
            w_arr[train_pos],
        )
        y_hat[test_pos] = y_pipe.predict(X.iloc[test_pos])
        d_hat[test_pos] = d_pipe.predict(X.iloc[test_pos])

    if not np.isfinite(y_hat).all() or not np.isfinite(d_hat).all():
        raise ValueError("cross-fitting produced non-finite nuisance predictions")

    y_res = y_arr - y_hat
    d_res = d_arr - d_hat
    denom = np.sum(w_arr * d_res * d_res)
    if denom <= 1e-12:
        raise ValueError("near-zero residualized treatment variance")
    theta = float(np.sum(w_arr * d_res * y_res) / denom)
    err = y_res - theta * d_res
    robust_meat = np.sum((w_arr**2) * (d_res**2) * (err**2))
    robust_se = float(np.sqrt(robust_meat / (denom**2)))
    robust_z = theta / robust_se if robust_se > 0 else np.nan
    robust_p = float(2 * (1 - stats.norm.cdf(abs(robust_z)))) if np.isfinite(robust_z) else np.nan

    se = robust_se
    p = robust_p
    n_clusters = np.nan
    inference = "heteroskedasticity_robust"
    if cluster_col and cluster_col in sub.columns:
        score = w_arr * d_res * err
        cluster_scores = pd.Series(score).groupby(sub[cluster_col].astype(str).reset_index(drop=True)).sum()
        n_clusters = int(cluster_scores.size)
        if n_clusters >= 2:
            correction = n_clusters / (n_clusters - 1)
            cluster_meat = float(np.sum(cluster_scores.to_numpy(float) ** 2))
            se = float(np.sqrt(correction * cluster_meat / (denom**2)))
            z = theta / se if se > 0 else np.nan
            p = float(2 * (1 - stats.norm.cdf(abs(z)))) if np.isfinite(z) else np.nan
            inference = f"school_clustered_{cluster_col}"
    return {
        "treatment": treatment,
        "plausible_value": pv,
        "coef": theta,
        "std_error": se,
        "p_value": p,
        "std_error_robust": robust_se,
        "p_value_robust": robust_p,
        "n_clusters": n_clusters,
        "inference": inference,
        "n": int(len(sub)),
        "learner": learner_name,
        "dml_method": f"weighted_cross_fitted_plr_{config.DML_N_FOLDS}fold",
    }


def run_dml_all(df, treatments, pvs, feature_cols, weight_col, out_dir, logger):
    rows = []
    errors = []
    for treatment in treatments:
        x_cols = [c for c in feature_cols if c != treatment]
        for pv in pvs:
            try:
                logger.info("Running weighted residualization DML: %s / %s", treatment, pv)
                cluster_col = "CNTSCHID" if "CNTSCHID" in df.columns else None
                rows.append(
                    weighted_residualized_dml(
                        df, pv, treatment, x_cols, weight_col, cluster_col, logger
                    )
                )
            except Exception as exc:
                logger.warning("DML failed for %s/%s: %s", treatment, pv, exc)
                errors.append({"treatment": treatment, "plausible_value": pv, "error": str(exc)})
    by_pv = pd.DataFrame(rows)
    if by_pv.empty:
        by_pv = pd.DataFrame(
            columns=[
                "treatment", "plausible_value", "coef", "std_error", "p_value",
                "std_error_robust", "p_value_robust", "n_clusters", "inference",
                "n", "learner", "dml_method",
            ]
        )
    by_pv.to_csv(out_dir / "dml_results_by_pv.csv", index=False, encoding="utf-8-sig")
    if errors:
        pd.DataFrame(errors).to_csv(out_dir / "dml_errors.csv", index=False, encoding="utf-8-sig")
    return by_pv


def main():
    out_dir = Path(config.OUT_DIR)
    logger = setup_logging(out_dir)
    logger.info("Starting formal GRADE-Agent PISA experiment.")
    logger.info("DATA_PATH=%s", config.DATA_PATH)
    logger.info("OUT_DIR=%s", config.OUT_DIR)

    if not check_data_path(config.DATA_PATH, logger):
        return

    columns, _ = read_sav_metadata(config.DATA_PATH)
    pv_found, pv_missing = split_found_missing(config.PV_MATH_VARS, columns)
    if pv_missing:
        logger.error("Missing PV variables: %s", pv_missing)
        print("Missing required plausible value variables. See run_log.txt.")
        return

    treatment_found, treatment_missing = split_found_missing(config.TREATMENT_CANDIDATES, columns)
    control_found, control_missing = split_found_missing(config.CONTROL_CANDIDATES, columns)
    weight_found = config.FINAL_STUDENT_WEIGHT in columns
    rep_weights = find_replicate_weights(columns)
    if not weight_found:
        logger.error("Student final weight W_FSTUWT not found. Formal weighted analysis cannot proceed.")
        print("W_FSTUWT not found. Please check the data file.")
        return

    missing_vars = pd.DataFrame(
        [{"variable": v, "role": "treatment"} for v in treatment_missing]
        + [{"variable": v, "role": "control"} for v in control_missing]
    )
    missing_vars.to_csv(out_dir / "missing_variables.csv", index=False, encoding="utf-8-sig")
    logger.info("Treatment variables found: %s", treatment_found)
    logger.info("Control variables found: %s", control_found)
    logger.info("Replicate weights detected: %s", len(rep_weights))

    usecols = sorted(set(pv_found + treatment_found + control_found + [config.FINAL_STUDENT_WEIGHT]))
    df = read_sav_selected(config.DATA_PATH, usecols)
    logger.info("Loaded selected data: rows=%s cols=%s", df.shape[0], df.shape[1])

    if config.COUNTRY_CODE is not None and "CNT" in df.columns:
        before = len(df)
        df = df[df["CNT"].astype(str) == str(config.COUNTRY_CODE)].copy()
        logger.info("Country filter %s: %s -> %s", config.COUNTRY_CODE, before, len(df))

    if config.MAX_N is not None and len(df) > int(config.MAX_N):
        df = df.sample(n=int(config.MAX_N), random_state=config.RANDOM_STATE).copy()
        logger.info("Sampled MAX_N=%s", config.MAX_N)

    df = df.reset_index(drop=True)
    df[config.MATH_MEAN_COL] = df[pv_found].mean(axis=1)
    df = df[df[config.FINAL_STUDENT_WEIGHT].notna() & (df[config.FINAL_STUDENT_WEIGHT] > 0)].copy()
    df = df.reset_index(drop=True)

    candidate_explanatory = [c for c in treatment_found + control_found if c in df.columns]
    missing_rate = df[pv_found + [config.MATH_MEAN_COL, config.FINAL_STUDENT_WEIGHT] + candidate_explanatory].isna().mean()
    missing_rate.reset_index().rename(columns={"index": "variable", 0: "missing_rate"}).to_csv(
        out_dir / "missing_rate.csv", index=False, encoding="utf-8-sig"
    )

    high_missing = missing_rate[(missing_rate > config.MISSING_RATE_THRESHOLD)].index.tolist()
    high_missing = [c for c in high_missing if c in candidate_explanatory]
    feature_cols = [
        c
        for c in candidate_explanatory
        if c not in high_missing
        and c not in config.NON_FEATURE_VARS
        and c != config.FINAL_STUDENT_WEIGHT
        and c not in config.PV_MATH_VARS
    ]
    treatments_for_dml = [t for t in treatment_found if t in feature_cols]

    selected = pd.DataFrame(
        {
            "variable": pv_found + [config.MATH_MEAN_COL, config.FINAL_STUDENT_WEIGHT] + feature_cols,
            "role": ["plausible_value"] * len(pv_found)
            + ["descriptive_outcome", "student_final_weight"]
            + ["treatment" if c in treatments_for_dml else "control_or_covariate" for c in feature_cols],
        }
    )
    selected.to_csv(out_dir / "selected_variables.csv", index=False, encoding="utf-8-sig")

    with open(out_dir / "preprocessing_summary.txt", "w", encoding="utf-8") as f:
        f.write("Formal GRADE-Agent PISA preprocessing summary\n")
        f.write(f"Rows after filtering: {len(df)}\n")
        f.write(f"Country filter: {config.COUNTRY_CODE}\n")
        f.write(f"PV variables: {', '.join(pv_found)}\n")
        f.write(f"Student final weight found: {config.FINAL_STUDENT_WEIGHT}\n")
        f.write(f"Replicate weights detected: {len(rep_weights)}\n")
        f.write(f"Variables dropped for missing rate > {config.MISSING_RATE_THRESHOLD}: {high_missing}\n")
        f.write("Main analysis uses W_FSTUWT. Replicate-weight inference is detected but left as an extension.\n")

    if not feature_cols:
        logger.error("No usable feature variables after filtering.")
        return

    numeric_cols, categorical_cols = infer_feature_types(df, feature_cols)
    logger.info("Feature columns=%s numeric=%s categorical=%s", len(feature_cols), len(numeric_cols), len(categorical_cols))

    all_idx = np.arange(len(df))
    train_idx, test_idx = train_test_split(all_idx, test_size=config.TEST_SIZE, random_state=config.RANDOM_STATE)

    metrics_list = []
    fi_list = []
    shap_list = []
    for pv in pv_found:
        metrics, fitted, x_train, w_train = fit_predict_models_for_pv(
            pv,
            df,
            train_idx,
            test_idx,
            feature_cols,
            numeric_cols,
            categorical_cols,
            config.FINAL_STUDENT_WEIGHT,
            logger,
        )
        if not metrics.empty:
            metrics_list.append(metrics)
        tree_name, tree_pipe = choose_tree_model(fitted)
        if tree_name and tree_pipe:
            fi = collect_feature_importance(pv, tree_name, tree_pipe)
            if not fi.empty:
                fi_list.append(fi)
            shap_df = collect_shap_importance(pv, tree_name, tree_pipe, x_train, w_train, logger)
            if not shap_df.empty:
                shap_list.append(shap_df)

    metrics_by_pv = pd.concat(metrics_list, ignore_index=True) if metrics_list else pd.DataFrame()
    metrics_by_pv.to_csv(out_dir / "weighted_model_metrics_by_pv.csv", index=False, encoding="utf-8-sig")
    metrics_pooled = pool_prediction_metrics(metrics_by_pv) if not metrics_by_pv.empty else pd.DataFrame()
    metrics_pooled.to_csv(out_dir / "weighted_model_metrics_pooled.csv", index=False, encoding="utf-8-sig")

    feature_importance_by_pv = pd.concat(fi_list, ignore_index=True) if fi_list else pd.DataFrame()
    if not feature_importance_by_pv.empty:
        feature_importance_by_pv.to_csv(out_dir / "feature_importance_by_pv.csv", index=False, encoding="utf-8-sig")
        feature_importance_pooled = pool_importance(feature_importance_by_pv, "importance")
        feature_importance_pooled.to_csv(out_dir / "feature_importance_pooled.csv", index=False, encoding="utf-8-sig")
        plot_top20(
            feature_importance_pooled,
            "importance",
            "feature",
            "Top 20 Pooled Feature Importance",
            out_dir / "feature_importance_top20.png",
        )
    else:
        feature_importance_pooled = pd.DataFrame()

    shap_by_pv = pd.concat(shap_list, ignore_index=True) if shap_list else pd.DataFrame()
    if not shap_by_pv.empty:
        shap_by_pv.to_csv(out_dir / "shap_importance_by_pv.csv", index=False, encoding="utf-8-sig")
        shap_pooled = pool_importance(shap_by_pv, "mean_abs_shap")
        shap_pooled.to_csv(out_dir / "shap_importance_pooled.csv", index=False, encoding="utf-8-sig")
        plot_top20(
            shap_pooled,
            "mean_abs_shap",
            "feature",
            "Top 20 Pooled SHAP Importance",
            out_dir / "shap_importance_top20.png",
        )
    else:
        shap_pooled = pd.DataFrame()

    dml_by_pv = run_dml_all(
        df,
        treatments_for_dml,
        pv_found,
        feature_cols,
        config.FINAL_STUDENT_WEIGHT,
        out_dir,
        logger,
    )
    dml_pooled = pool_dml_results(dml_by_pv) if not dml_by_pv.empty else pd.DataFrame()
    dml_pooled.to_csv(out_dir / "dml_results_pooled.csv", index=False, encoding="utf-8-sig")
    stability = make_stability_check(dml_by_pv, dml_pooled) if not dml_by_pv.empty else pd.DataFrame()
    stability.to_csv(out_dir / "dml_stability_check.csv", index=False, encoding="utf-8-sig")
    plot_dml_pooled(dml_pooled, out_dir / "dml_effects_pooled.png", out_dir / "dml_effects_pooled.pdf")

    rules = generate_agent_rules(dml_pooled, stability)
    rules.to_csv(out_dir / "agent_rule_mapping_formal.csv", index=False, encoding="utf-8-sig")

    save_sample_description(
        df,
        [config.MATH_MEAN_COL, config.FINAL_STUDENT_WEIGHT] + treatments_for_dml + feature_cols,
        config.COUNTRY_CODE,
        out_dir / "table_1_sample_description.csv",
    )
    metrics_pooled.to_csv(out_dir / "table_2_prediction_results.csv", index=False, encoding="utf-8-sig")
    top_source = shap_pooled if not shap_pooled.empty else feature_importance_pooled
    top_source.head(30).to_csv(out_dir / "table_3_shap_top_variables.csv", index=False, encoding="utf-8-sig")
    dml_pooled.to_csv(out_dir / "table_4_dml_pooled_results.csv", index=False, encoding="utf-8-sig")
    rules.to_csv(out_dir / "table_5_agent_rule_mapping.csv", index=False, encoding="utf-8-sig")
    write_paper_draft(out_dir / "paper_results_draft.md", metrics_pooled, dml_pooled, rules)

    logger.info("Formal experiment finished. Outputs saved to %s", out_dir)
    print(f"Formal experiment finished. Outputs saved to: {out_dir}")


if __name__ == "__main__":
    main()
