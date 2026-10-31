from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyreadstat
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNetCV, RidgeCV
from sklearn.model_selection import KFold, train_test_split
from sklearn.preprocessing import StandardScaler

import config
from optimize_prediction_models import make_preprocessor, select_features
from utils_pisa import weighted_mae, weighted_r2, weighted_rmse


OUT = Path(r"D:\pisa2022\outputs_five_models_tuned_42_features")
OUT.mkdir(parents=True, exist_ok=True)


LGBM_CANDIDATES = [
    {"n_estimators": 700, "learning_rate": .025, "num_leaves": 20,
     "max_depth": 7, "min_child_samples": 25, "subsample": .9,
     "colsample_bytree": .9, "reg_alpha": .1, "reg_lambda": 2.0},
    {"n_estimators": 900, "learning_rate": .018, "num_leaves": 20,
     "max_depth": 7, "min_child_samples": 25, "subsample": .9,
     "colsample_bytree": .9, "reg_alpha": .1, "reg_lambda": 2.0},
    {"n_estimators": 800, "learning_rate": .02, "num_leaves": 24,
     "max_depth": 7, "min_child_samples": 30, "subsample": .9,
     "colsample_bytree": .85, "reg_alpha": .2, "reg_lambda": 3.0},
    {"n_estimators": 1000, "learning_rate": .015, "num_leaves": 16,
     "max_depth": 6, "min_child_samples": 25, "subsample": .9,
     "colsample_bytree": .9, "reg_alpha": .1, "reg_lambda": 2.0},
    {"n_estimators": 650, "learning_rate": .025, "num_leaves": 28,
     "max_depth": 8, "min_child_samples": 35, "subsample": .85,
     "colsample_bytree": .85, "reg_alpha": .3, "reg_lambda": 3.0},
]

RF_CANDIDATES = [
    {"n_estimators": 500, "min_samples_leaf": leaf, "max_features": max_features}
    for leaf, max_features in [(2, .7), (3, .8), (5, 1.0), (8, .8), (10, .6)]
]

ET_CANDIDATES = [
    {"n_estimators": 600, "min_samples_leaf": leaf, "max_features": max_features}
    for leaf, max_features in [(1, .8), (2, .8), (3, .8), (5, 1.0), (7, .7)]
]


def build_model(model, params=None):
    params = params or {}
    if model == "LightGBM":
        return lgb.LGBMRegressor(
            **params, random_state=config.RANDOM_STATE, n_jobs=-1, verbose=-1
        )
    if model == "RandomForest":
        return RandomForestRegressor(
            **params, random_state=config.RANDOM_STATE, n_jobs=-1
        )
    if model == "ExtraTrees":
        return ExtraTreesRegressor(
            **params, random_state=config.RANDOM_STATE, n_jobs=-1
        )
    if model == "ElasticNet":
        return ElasticNetCV(
            l1_ratio=[.05, .1, .3, .5, .7, .9, .95],
            alphas=np.logspace(-4, 2, 40),
            cv=5,
            max_iter=15000,
            random_state=config.RANDOM_STATE,
            n_jobs=-1,
        )
    if model == "Ridge":
        return RidgeCV(alphas=np.logspace(-4, 4, 33))
    raise ValueError(model)


def candidates():
    return {
        "LightGBM": LGBM_CANDIDATES,
        "RandomForest": RF_CANDIDATES,
        "ExtraTrees": ET_CANDIDATES,
        "ElasticNet": [{}],
        "Ridge": [{}],
    }


def main():
    _, meta = pyreadstat.read_sav(config.DATA_PATH, metadataonly=True)
    features, _ = select_features(meta)
    usecols = sorted(set(
        config.PV_MATH_VARS + [config.FINAL_STUDENT_WEIGHT, "CNT"] + features
    ))
    print(f"Reading {len(usecols)} columns...", flush=True)
    data, _ = pyreadstat.read_sav(
        config.DATA_PATH, usecols=usecols,
        apply_value_formats=False, user_missing=False,
    )
    data = data[data["CNT"].astype(str) == config.COUNTRY_CODE].reset_index(drop=True)
    data = data[
        data[config.FINAL_STUDENT_WEIGHT].notna()
        & (data[config.FINAL_STUDENT_WEIGHT] > 0)
    ].reset_index(drop=True)
    data["MATH_MEAN"] = data[config.PV_MATH_VARS].mean(axis=1)

    all_idx = np.arange(len(data))
    train_idx, test_idx = train_test_split(
        all_idx, test_size=config.TEST_SIZE, random_state=config.RANDOM_STATE
    )
    missing = data.loc[train_idx, features].isna().mean()
    features = [f for f in features if missing[f] <= .5]
    if len(features) != 42:
        raise RuntimeError(f"Expected 42 features, got {len(features)}")

    folds = list(KFold(
        n_splits=3, shuffle=True, random_state=config.RANDOM_STATE
    ).split(train_idx))
    transformed = []
    for fold_train_pos, fold_valid_pos in folds:
        fold_train = train_idx[fold_train_pos]
        fold_valid = train_idx[fold_valid_pos]
        prep = make_preprocessor(data.loc[fold_train], features)
        x_train = prep.fit_transform(data.loc[fold_train, features])
        x_valid = prep.transform(data.loc[fold_valid, features])
        scaler = StandardScaler()
        transformed.append({
            "train_idx": fold_train,
            "valid_idx": fold_valid,
            "tree_train": x_train,
            "tree_valid": x_valid,
            "linear_train": scaler.fit_transform(x_train),
            "linear_valid": scaler.transform(x_valid),
        })

    cv_rows = []
    for model_name, parameter_sets in candidates().items():
        for candidate_id, params in enumerate(parameter_sets, start=1):
            print(f"CV {model_name} candidate {candidate_id}", flush=True)
            for fold_id, fold in enumerate(transformed, start=1):
                linear = model_name in {"ElasticNet", "Ridge"}
                x_train = fold["linear_train"] if linear else fold["tree_train"]
                x_valid = fold["linear_valid"] if linear else fold["tree_valid"]
                tr = fold["train_idx"]
                va = fold["valid_idx"]
                y_train = data.loc[tr, "MATH_MEAN"].to_numpy(float)
                y_valid = data.loc[va, "MATH_MEAN"].to_numpy(float)
                w_train = data.loc[tr, config.FINAL_STUDENT_WEIGHT].to_numpy(float)
                w_valid = data.loc[va, config.FINAL_STUDENT_WEIGHT].to_numpy(float)
                fitted = build_model(model_name, params)
                fitted.fit(x_train, y_train, sample_weight=w_train)
                pred = fitted.predict(x_valid)
                cv_rows.append({
                    "model": model_name,
                    "candidate_id": candidate_id,
                    "fold": fold_id,
                    "params": json.dumps(params, sort_keys=True),
                    "weighted_r2": weighted_r2(y_valid, pred, w_valid),
                    "weighted_rmse": weighted_rmse(y_valid, pred, w_valid),
                    "weighted_mae": weighted_mae(y_valid, pred, w_valid),
                })

    cv = pd.DataFrame(cv_rows)
    cv.to_csv(OUT / "training_cv_all_candidates.csv", index=False)
    cv_summary = (
        cv.groupby(["model", "candidate_id", "params"], as_index=False)
        .agg(
            cv_r2_mean=("weighted_r2", "mean"),
            cv_r2_sd=("weighted_r2", "std"),
            cv_rmse_mean=("weighted_rmse", "mean"),
            cv_mae_mean=("weighted_mae", "mean"),
        )
    )
    selected = (
        cv_summary.sort_values(["model", "cv_r2_mean"], ascending=[True, False])
        .groupby("model", as_index=False).first()
    )
    cv_summary.to_csv(OUT / "training_cv_candidate_summary.csv", index=False)
    selected.to_csv(OUT / "training_cv_selected_models.csv", index=False)
    print("\nSelected on training CV:\n" + selected.to_string(index=False), flush=True)

    prep = make_preprocessor(data.loc[train_idx], features)
    x_train_tree = prep.fit_transform(data.loc[train_idx, features])
    x_test_tree = prep.transform(data.loc[test_idx, features])
    scaler = StandardScaler()
    x_train_linear = scaler.fit_transform(x_train_tree)
    x_test_linear = scaler.transform(x_test_tree)
    w_train_all = data.loc[train_idx, config.FINAL_STUDENT_WEIGHT].to_numpy(float)
    w_test_all = data.loc[test_idx, config.FINAL_STUDENT_WEIGHT].to_numpy(float)

    test_rows = []
    for _, selection in selected.iterrows():
        model_name = selection["model"]
        params = json.loads(selection["params"])
        linear = model_name in {"ElasticNet", "Ridge"}
        for pv in config.PV_MATH_VARS:
            print(f"TEST {model_name} {pv}", flush=True)
            train_valid = data.loc[train_idx, pv].notna().to_numpy()
            test_valid = data.loc[test_idx, pv].notna().to_numpy()
            x_train = (
                x_train_linear[train_valid] if linear else x_train_tree[train_valid]
            )
            x_test = (
                x_test_linear[test_valid] if linear else x_test_tree[test_valid]
            )
            y_train = data.loc[train_idx, pv].to_numpy(float)[train_valid]
            y_test = data.loc[test_idx, pv].to_numpy(float)[test_valid]
            w_train = w_train_all[train_valid]
            w_test = w_test_all[test_valid]
            fitted = build_model(model_name, params)
            fitted.fit(x_train, y_train, sample_weight=w_train)
            pred = fitted.predict(x_test)
            test_rows.append({
                "model": model_name,
                "plausible_value": pv,
                "weighted_r2": weighted_r2(y_test, pred, w_test),
                "weighted_rmse": weighted_rmse(y_test, pred, w_test),
                "weighted_mae": weighted_mae(y_test, pred, w_test),
            })

    test = pd.DataFrame(test_rows)
    test.to_csv(OUT / "tuned_five_model_metrics_by_pv.csv", index=False)
    summary = (
        test.groupby("model", as_index=False)
        .agg(
            weighted_r2_mean=("weighted_r2", "mean"),
            weighted_r2_sd=("weighted_r2", "std"),
            weighted_rmse_mean=("weighted_rmse", "mean"),
            weighted_rmse_sd=("weighted_rmse", "std"),
            weighted_mae_mean=("weighted_mae", "mean"),
            weighted_mae_sd=("weighted_mae", "std"),
        )
        .sort_values("weighted_r2_mean", ascending=False)
    )
    summary.to_csv(OUT / "tuned_five_model_metrics_summary.csv", index=False)
    print("\nHeld-out test:\n" + summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
