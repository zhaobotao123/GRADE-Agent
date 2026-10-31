from __future__ import annotations

import json
import re
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyreadstat
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

import config
from utils_pisa import weighted_mae, weighted_r2, weighted_rmse


OUT_DIR = Path(r"D:\pisa2022\outputs_prediction_optimization")
OUT_DIR.mkdir(parents=True, exist_ok=True)

EXCLUDED_PREFIXES = (
    "PV",
    "W_",
    "SENWT",
    "VER_",
    "BOOKID",
)
EXCLUDED_EXACT = {
    "CNTSCHID",
    "CNTSTUID",
    "CNTRYID",
    "CYC",
    "NatCen",
    "STRATUM",
    "SUBNATIO",
}

PARAMETER_SETS = {
    "LGBM_baseline": dict(
        n_estimators=500,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_alpha=0.0,
        reg_lambda=0.0,
    ),
    "LGBM_regularized_1": dict(
        n_estimators=900,
        learning_rate=0.02,
        num_leaves=31,
        min_child_samples=30,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.2,
        reg_lambda=1.0,
    ),
    "LGBM_regularized_2": dict(
        n_estimators=700,
        learning_rate=0.025,
        num_leaves=20,
        max_depth=7,
        min_child_samples=25,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_alpha=0.1,
        reg_lambda=2.0,
    ),
    "LGBM_wider": dict(
        n_estimators=650,
        learning_rate=0.025,
        num_leaves=48,
        max_depth=9,
        min_child_samples=35,
        subsample=0.85,
        colsample_bytree=0.8,
        reg_alpha=0.5,
        reg_lambda=2.0,
    ),
    "LGBM_conservative": dict(
        n_estimators=800,
        learning_rate=0.02,
        num_leaves=15,
        max_depth=6,
        min_child_samples=40,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_alpha=0.2,
        reg_lambda=3.0,
    ),
}


def select_features(meta) -> tuple[list[str], pd.DataFrame]:
    rows = []
    selected = []
    for name in meta.column_names:
        label = meta.column_names_to_labels.get(name, "") or ""
        measure = meta.variable_measure.get(name, "")
        readstat_type = meta.readstat_variable_types.get(name, "")
        excluded = (
            name in EXCLUDED_EXACT
            or name == config.FINAL_STUDENT_WEIGHT
            or name in config.PV_MATH_VARS
            or name.startswith(EXCLUDED_PREFIXES)
        )
        include = (
            not excluded
            and readstat_type == "double"
            and (
                measure == "scale"
                or name in config.CONTROL_CANDIDATES
                or name in config.TREATMENT_CANDIDATES
            )
        )
        # Raw item batteries are deliberately excluded; only scale variables and
        # prespecified controls are eligible for the expanded predictor set.
        if include and not re.match(r"^(PA|SC|IC|WB|ST)\d{3}Q", name):
            selected.append(name)
        rows.append(
            {
                "variable": name,
                "label": label,
                "measure": measure,
                "readstat_type": readstat_type,
                "selected": include and not re.match(r"^(PA|SC|IC|WB|ST)\d{3}Q", name),
            }
        )
    return selected, pd.DataFrame(rows)


def make_preprocessor(df: pd.DataFrame, features: list[str]) -> ColumnTransformer:
    numeric = []
    categorical = []
    for column in features:
        if df[column].nunique(dropna=True) <= 12:
            categorical.append(column)
        else:
            numeric.append(column)
    return ColumnTransformer(
        [
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="median"))]),
                numeric,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(
                                handle_unknown="ignore",
                                sparse_output=False,
                                min_frequency=20,
                            ),
                        ),
                    ]
                ),
                categorical,
            ),
        ],
        verbose_feature_names_out=False,
    )


def main() -> None:
    _, meta = pyreadstat.read_sav(config.DATA_PATH, metadataonly=True)
    expanded_features, audit = select_features(meta)
    required = sorted(
        set(
            config.PV_MATH_VARS
            + [config.FINAL_STUDENT_WEIGHT, "CNT"]
            + expanded_features
        )
    )
    print(f"Reading {len(required)} selected columns from SAV...")
    data, _ = pyreadstat.read_sav(
        config.DATA_PATH,
        usecols=required,
        apply_value_formats=False,
        user_missing=False,
    )
    data = data[data["CNT"].astype(str) == "JPN"].reset_index(drop=True)
    data = data[
        data[config.FINAL_STUDENT_WEIGHT].notna()
        & (data[config.FINAL_STUDENT_WEIGHT] > 0)
    ].reset_index(drop=True)

    missing = data[expanded_features].isna().mean()
    expanded_features = [
        feature for feature in expanded_features if missing[feature] <= 0.5
    ]
    audit["missing_rate_jpn"] = audit["variable"].map(missing)
    audit["used_after_missing_filter"] = audit["variable"].isin(expanded_features)
    audit.to_csv(OUT_DIR / "feature_audit.csv", index=False, encoding="utf-8-sig")

    original_features = [
        feature
        for feature in config.TREATMENT_CANDIDATES + config.CONTROL_CANDIDATES
        if feature in data.columns
        and feature not in config.NON_FEATURE_VARS
        and feature != config.FINAL_STUDENT_WEIGHT
        and data[feature].isna().mean() <= 0.5
    ]
    feature_sets = {
        "original_restricted": original_features,
        "expanded_scales": expanded_features,
    }
    (OUT_DIR / "feature_sets.json").write_text(
        json.dumps(feature_sets, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    indices = np.arange(len(data))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=config.TEST_SIZE,
        random_state=config.RANDOM_STATE,
    )
    results = []

    for feature_set_name, features in feature_sets.items():
        print(f"Feature set {feature_set_name}: {len(features)} variables")
        preprocessor = make_preprocessor(data, features)
        x_train = preprocessor.fit_transform(data.loc[train_idx, features])
        x_test = preprocessor.transform(data.loc[test_idx, features])
        w_train = data.loc[train_idx, config.FINAL_STUDENT_WEIGHT].to_numpy(float)
        w_test = data.loc[test_idx, config.FINAL_STUDENT_WEIGHT].to_numpy(float)

        for model_name, params in PARAMETER_SETS.items():
            # Tuning is only meaningful for the expanded set; retain one exact
            # baseline on the restricted set to verify the original experiment.
            if feature_set_name == "original_restricted" and model_name != "LGBM_baseline":
                continue
            print(f"  {model_name}")
            for pv in config.PV_MATH_VARS:
                train_valid = data.loc[train_idx, pv].notna().to_numpy()
                test_valid = data.loc[test_idx, pv].notna().to_numpy()
                model = lgb.LGBMRegressor(
                    **params,
                    random_state=config.RANDOM_STATE,
                    n_jobs=-1,
                    verbose=-1,
                )
                model.fit(
                    x_train[train_valid],
                    data.loc[train_idx, pv].to_numpy(float)[train_valid],
                    sample_weight=w_train[train_valid],
                )
                prediction = model.predict(x_test[test_valid])
                truth = data.loc[test_idx, pv].to_numpy(float)[test_valid]
                weights = w_test[test_valid]
                results.append(
                    {
                        "feature_set": feature_set_name,
                        "model": model_name,
                        "plausible_value": pv,
                        "weighted_r2": weighted_r2(truth, prediction, weights),
                        "weighted_rmse": weighted_rmse(truth, prediction, weights),
                        "weighted_mae": weighted_mae(truth, prediction, weights),
                        "feature_count": len(features),
                        "train_n": int(train_valid.sum()),
                        "test_n": int(test_valid.sum()),
                    }
                )

    detailed = pd.DataFrame(results)
    detailed.to_csv(
        OUT_DIR / "prediction_metrics_by_pv.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary = (
        detailed.groupby(["feature_set", "model", "feature_count"], as_index=False)
        .agg(
            weighted_r2_mean=("weighted_r2", "mean"),
            weighted_r2_sd=("weighted_r2", "std"),
            weighted_rmse_mean=("weighted_rmse", "mean"),
            weighted_rmse_sd=("weighted_rmse", "std"),
            weighted_mae_mean=("weighted_mae", "mean"),
            weighted_mae_sd=("weighted_mae", "std"),
            pv_count=("plausible_value", "nunique"),
        )
        .sort_values("weighted_r2_mean", ascending=False)
    )
    summary.to_csv(
        OUT_DIR / "prediction_metrics_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
