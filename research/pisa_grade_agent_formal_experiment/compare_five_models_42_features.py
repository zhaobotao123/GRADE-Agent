from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyreadstat
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNetCV, RidgeCV
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

import config
from optimize_prediction_models import (
    PARAMETER_SETS,
    make_preprocessor,
    select_features,
)
from utils_pisa import weighted_mae, weighted_r2, weighted_rmse


OUT_DIR = Path(r"D:\pisa2022\outputs_five_models_42_features")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def make_models():
    return {
        "LightGBM": lgb.LGBMRegressor(
            **PARAMETER_SETS["LGBM_regularized_2"],
            random_state=config.RANDOM_STATE,
            n_jobs=-1,
            verbose=-1,
        ),
        "RandomForest": RandomForestRegressor(**config.RF_PARAMS),
        "ExtraTrees": ExtraTreesRegressor(**config.EXTRA_TREES_PARAMS),
        "ElasticNet": ElasticNetCV(
            l1_ratio=[0.1, 0.3, 0.5, 0.7, 0.9],
            alphas=np.logspace(-3, 1, 20),
            cv=5,
            random_state=config.RANDOM_STATE,
            max_iter=10000,
            n_jobs=-1,
        ),
        "Ridge": RidgeCV(alphas=np.logspace(-3, 3, 13)),
    }


def main():
    _, meta = pyreadstat.read_sav(config.DATA_PATH, metadataonly=True)
    features, audit = select_features(meta)
    usecols = sorted(
        set(config.PV_MATH_VARS + [config.FINAL_STUDENT_WEIGHT, "CNT"] + features)
    )
    print(f"Reading {len(usecols)} columns...")
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

    indices = np.arange(len(data))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=config.TEST_SIZE,
        random_state=config.RANDOM_STATE,
    )
    train_missing = data.loc[train_idx, features].isna().mean()
    features = [name for name in features if train_missing[name] <= 0.5]
    if len(features) != 42:
        raise RuntimeError(f"Expected 42 features, found {len(features)}")

    preprocessor = make_preprocessor(data.loc[train_idx], features)
    x_train_tree = preprocessor.fit_transform(data.loc[train_idx, features])
    x_test_tree = preprocessor.transform(data.loc[test_idx, features])
    scaler = StandardScaler()
    x_train_linear = scaler.fit_transform(x_train_tree)
    x_test_linear = scaler.transform(x_test_tree)
    w_train = data.loc[train_idx, config.FINAL_STUDENT_WEIGHT].to_numpy(float)
    w_test = data.loc[test_idx, config.FINAL_STUDENT_WEIGHT].to_numpy(float)

    metadata = {
        "n": len(data),
        "train_n": len(train_idx),
        "test_n": len(test_idx),
        "feature_count": len(features),
        "transformed_feature_count": int(x_train_tree.shape[1]),
        "random_state": config.RANDOM_STATE,
        "test_size": config.TEST_SIZE,
        "features": features,
    }
    (OUT_DIR / "comparison_design.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    audit["used_in_fair_comparison"] = audit["variable"].isin(features)
    audit.to_csv(OUT_DIR / "feature_audit.csv", index=False, encoding="utf-8-sig")

    rows = []
    models = make_models()
    for pv in config.PV_MATH_VARS:
        train_valid = data.loc[train_idx, pv].notna().to_numpy()
        test_valid = data.loc[test_idx, pv].notna().to_numpy()
        y_train = data.loc[train_idx, pv].to_numpy(float)[train_valid]
        y_test = data.loc[test_idx, pv].to_numpy(float)[test_valid]
        weights_train = w_train[train_valid]
        weights_test = w_test[test_valid]

        for model_name, model in models.items():
            print(f"{pv}: {model_name}", flush=True)
            linear = model_name in {"ElasticNet", "Ridge"}
            x_train = x_train_linear[train_valid] if linear else x_train_tree[train_valid]
            x_test = x_test_linear[test_valid] if linear else x_test_tree[test_valid]
            model.fit(x_train, y_train, sample_weight=weights_train)
            prediction = model.predict(x_test)
            rows.append(
                {
                    "model": model_name,
                    "plausible_value": pv,
                    "feature_count": len(features),
                    "weighted_r2": weighted_r2(y_test, prediction, weights_test),
                    "weighted_rmse": weighted_rmse(y_test, prediction, weights_test),
                    "weighted_mae": weighted_mae(y_test, prediction, weights_test),
                    "n_test": int(test_valid.sum()),
                }
            )

    by_pv = pd.DataFrame(rows)
    by_pv.to_csv(
        OUT_DIR / "five_model_metrics_by_pv.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary = (
        by_pv.groupby("model", as_index=False)
        .agg(
            weighted_r2_mean=("weighted_r2", "mean"),
            weighted_r2_sd=("weighted_r2", "std"),
            weighted_rmse_mean=("weighted_rmse", "mean"),
            weighted_rmse_sd=("weighted_rmse", "std"),
            weighted_mae_mean=("weighted_mae", "mean"),
            weighted_mae_sd=("weighted_mae", "std"),
            plausible_values=("plausible_value", "nunique"),
        )
        .sort_values("weighted_r2_mean", ascending=False)
    )
    summary.to_csv(
        OUT_DIR / "five_model_metrics_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print("\n" + summary.to_string(index=False))


if __name__ == "__main__":
    main()
