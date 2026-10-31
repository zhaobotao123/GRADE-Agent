from __future__ import annotations

from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyreadstat
import shap
from sklearn.model_selection import train_test_split

import config
from optimize_prediction_models import make_preprocessor, select_features


OUT = Path(r"D:\pisa2022\outputs_final_shap_42_features")
OUT.mkdir(parents=True, exist_ok=True)

FINAL_PARAMS = {
    "n_estimators": 1000,
    "learning_rate": 0.015,
    "num_leaves": 16,
    "max_depth": 6,
    "min_child_samples": 25,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "reg_alpha": 0.1,
    "reg_lambda": 2.0,
}


def original_feature(transformed_name: str, features: list[str]) -> str:
    if transformed_name in features:
        return transformed_name
    matches = [f for f in features if transformed_name.startswith(f + "_")]
    if not matches:
        raise ValueError(f"Cannot map transformed feature: {transformed_name}")
    return max(matches, key=len)


def main():
    _, meta = pyreadstat.read_sav(config.DATA_PATH, metadataonly=True)
    features, _ = select_features(meta)
    usecols = sorted(set(
        config.PV_MATH_VARS + [config.FINAL_STUDENT_WEIGHT, "CNT"] + features
    ))
    print(f"Reading {len(usecols)} columns...", flush=True)
    data, _ = pyreadstat.read_sav(
        config.DATA_PATH,
        usecols=usecols,
        apply_value_formats=False,
        user_missing=False,
    )
    data = data[data["CNT"].astype(str) == config.COUNTRY_CODE].reset_index(drop=True)
    data = data[
        data[config.FINAL_STUDENT_WEIGHT].notna()
        & (data[config.FINAL_STUDENT_WEIGHT] > 0)
    ].reset_index(drop=True)
    all_idx = np.arange(len(data))
    train_idx, _ = train_test_split(
        all_idx, test_size=config.TEST_SIZE, random_state=config.RANDOM_STATE
    )
    missing = data.loc[train_idx, features].isna().mean()
    features = [f for f in features if missing[f] <= .5]
    if len(features) != 42:
        raise RuntimeError(f"Expected 42 features, got {len(features)}")

    preprocessor = make_preprocessor(data.loc[train_idx], features)
    x_train = preprocessor.fit_transform(data.loc[train_idx, features])
    transformed_names = list(preprocessor.get_feature_names_out())
    mapped_names = [original_feature(name, features) for name in transformed_names]
    weights_all = data.loc[train_idx, config.FINAL_STUDENT_WEIGHT].to_numpy(float)
    rng = np.random.default_rng(config.RANDOM_STATE)
    rows = []

    for pv_number, pv in enumerate(config.PV_MATH_VARS, start=1):
        print(f"{pv}: fit final LightGBM and compute SHAP", flush=True)
        valid = data.loc[train_idx, pv].notna().to_numpy()
        valid_positions = np.flatnonzero(valid)
        sample_size = min(config.SHAP_MAX_N, len(valid_positions))
        sample_positions = rng.choice(
            valid_positions, size=sample_size, replace=False
        )
        model = lgb.LGBMRegressor(
            **FINAL_PARAMS,
            random_state=config.RANDOM_STATE,
            n_jobs=-1,
            verbose=-1,
        )
        model.fit(
            x_train[valid],
            data.loc[train_idx, pv].to_numpy(float)[valid],
            sample_weight=weights_all[valid],
        )
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(x_train[sample_positions])
        if isinstance(values, list):
            values = values[0]
        values = np.asarray(values)
        weighted_abs = np.average(
            np.abs(values),
            axis=0,
            weights=weights_all[sample_positions],
        )
        transformed = pd.DataFrame({
            "transformed_feature": transformed_names,
            "feature": mapped_names,
            "mean_abs_shap": weighted_abs,
        })
        aggregated = (
            transformed.groupby("feature", as_index=False)["mean_abs_shap"].sum()
        )
        aggregated["plausible_value"] = pv
        aggregated["sample_n"] = sample_size
        rows.append(aggregated)

    by_pv = pd.concat(rows, ignore_index=True)
    by_pv.to_csv(OUT / "shap_importance_by_pv.csv", index=False)
    pooled = (
        by_pv.groupby("feature", as_index=False)
        .agg(
            mean_abs_shap=("mean_abs_shap", "mean"),
            sd_abs_shap=("mean_abs_shap", "std"),
            plausible_values=("plausible_value", "nunique"),
        )
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    pooled["rank"] = np.arange(1, len(pooled) + 1)
    pooled.to_csv(OUT / "shap_importance_pooled.csv", index=False)
    pooled.head(20).to_csv(OUT / "shap_importance_top20.csv", index=False)
    print("\n" + pooled.head(20).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
