from __future__ import annotations

from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyreadstat
from sklearn.model_selection import KFold, train_test_split

import config
from optimize_prediction_models import (
    OUT_DIR,
    PARAMETER_SETS,
    make_preprocessor,
    select_features,
)
from utils_pisa import weighted_mae, weighted_r2, weighted_rmse


def fit_and_score(params, x_train, y_train, w_train, x_valid, y_valid, w_valid):
    model = lgb.LGBMRegressor(
        **params,
        random_state=config.RANDOM_STATE,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(x_train, y_train, sample_weight=w_train)
    prediction = model.predict(x_valid)
    return {
        "weighted_r2": weighted_r2(y_valid, prediction, w_valid),
        "weighted_rmse": weighted_rmse(y_valid, prediction, w_valid),
        "weighted_mae": weighted_mae(y_valid, prediction, w_valid),
    }


def main():
    _, meta = pyreadstat.read_sav(config.DATA_PATH, metadataonly=True)
    features, _ = select_features(meta)
    usecols = sorted(
        set(config.PV_MATH_VARS + [config.FINAL_STUDENT_WEIGHT, "CNT"] + features)
    )
    data, _ = pyreadstat.read_sav(
        config.DATA_PATH,
        usecols=usecols,
        apply_value_formats=False,
        user_missing=False,
    )
    data = data[data["CNT"].astype(str) == "JPN"].reset_index(drop=True)
    data = data[
        data[config.FINAL_STUDENT_WEIGHT].notna()
        & (data[config.FINAL_STUDENT_WEIGHT] > 0)
    ].reset_index(drop=True)
    data["MATH_MEAN"] = data[config.PV_MATH_VARS].mean(axis=1)

    all_indices = np.arange(len(data))
    train_indices, test_indices = train_test_split(
        all_indices,
        test_size=config.TEST_SIZE,
        random_state=config.RANDOM_STATE,
    )
    train_missing = data.loc[train_indices, features].isna().mean()
    features = [feature for feature in features if train_missing[feature] <= 0.5]

    folds = KFold(n_splits=5, shuffle=True, random_state=config.RANDOM_STATE)
    cv_rows = []
    for model_name, params in PARAMETER_SETS.items():
        print(f"CV: {model_name}")
        for fold_number, (fold_train_pos, fold_valid_pos) in enumerate(
            folds.split(train_indices), start=1
        ):
            fold_train = train_indices[fold_train_pos]
            fold_valid = train_indices[fold_valid_pos]
            preprocessor = make_preprocessor(data.loc[train_indices], features)
            x_train = preprocessor.fit_transform(data.loc[fold_train, features])
            x_valid = preprocessor.transform(data.loc[fold_valid, features])
            score = fit_and_score(
                params,
                x_train,
                data.loc[fold_train, "MATH_MEAN"].to_numpy(float),
                data.loc[fold_train, config.FINAL_STUDENT_WEIGHT].to_numpy(float),
                x_valid,
                data.loc[fold_valid, "MATH_MEAN"].to_numpy(float),
                data.loc[fold_valid, config.FINAL_STUDENT_WEIGHT].to_numpy(float),
            )
            cv_rows.append({"model": model_name, "fold": fold_number, **score})

    cv = pd.DataFrame(cv_rows)
    cv.to_csv(OUT_DIR / "training_cv_metrics.csv", index=False, encoding="utf-8-sig")
    cv_summary = (
        cv.groupby("model", as_index=False)
        .agg(
            cv_r2_mean=("weighted_r2", "mean"),
            cv_r2_sd=("weighted_r2", "std"),
            cv_rmse_mean=("weighted_rmse", "mean"),
            cv_mae_mean=("weighted_mae", "mean"),
        )
        .sort_values("cv_r2_mean", ascending=False)
    )
    cv_summary.to_csv(
        OUT_DIR / "training_cv_summary.csv", index=False, encoding="utf-8-sig"
    )
    selected_model = str(cv_summary.iloc[0]["model"])
    selected_params = PARAMETER_SETS[selected_model]
    print(cv_summary.to_string(index=False))
    print(f"Selected from training CV: {selected_model}")

    preprocessor = make_preprocessor(data.loc[train_indices], features)
    x_train = preprocessor.fit_transform(data.loc[train_indices, features])
    x_test = preprocessor.transform(data.loc[test_indices, features])
    w_train = data.loc[train_indices, config.FINAL_STUDENT_WEIGHT].to_numpy(float)
    w_test = data.loc[test_indices, config.FINAL_STUDENT_WEIGHT].to_numpy(float)

    test_rows = []
    outcomes = ["MATH_MEAN"] + config.PV_MATH_VARS
    for outcome in outcomes:
        train_valid = data.loc[train_indices, outcome].notna().to_numpy()
        test_valid = data.loc[test_indices, outcome].notna().to_numpy()
        score = fit_and_score(
            selected_params,
            x_train[train_valid],
            data.loc[train_indices, outcome].to_numpy(float)[train_valid],
            w_train[train_valid],
            x_test[test_valid],
            data.loc[test_indices, outcome].to_numpy(float)[test_valid],
            w_test[test_valid],
        )
        test_rows.append(
            {
                "selected_model": selected_model,
                "outcome": outcome,
                "feature_count": len(features),
                **score,
            }
        )
    test = pd.DataFrame(test_rows)
    test.to_csv(
        OUT_DIR / "heldout_test_metrics_cv_selected.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pv_summary = (
        test[test["outcome"].str.startswith("PV")]
        .agg(
            {
                "weighted_r2": ["mean", "std"],
                "weighted_rmse": ["mean", "std"],
                "weighted_mae": ["mean", "std"],
            }
        )
    )
    print(test.to_string(index=False))
    print(pv_summary.to_string())


if __name__ == "__main__":
    main()
