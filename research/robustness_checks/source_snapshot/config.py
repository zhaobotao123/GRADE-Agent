from pathlib import Path


# Default path requested in the thesis brief:
# DATA_PATH = r"D:\pisa2022\CY08MSP_STU_QQQ.sav"
#
# The local copy found in your provided folder is used as the runnable default.
DATA_PATH = "D:\\Users\\84130\\Desktop\\\u8bba\u6587\\STU_QQQ_SPSS\\CY08MSP_STU_QQQ.SAV"
OUT_DIR = r"D:\pisa2022\outputs_grade_agent_formal"

COUNTRY_CODE = "JPN"
MAX_N = None
RANDOM_STATE = 42
TEST_SIZE = 0.2

PV_MATH_VARS = [f"PV{i}MATH" for i in range(1, 11)]
MATH_MEAN_COL = "MATH_MEAN"

FINAL_STUDENT_WEIGHT = "W_FSTUWT"
REPLICATE_WEIGHT_PREFIXES = ["W_FSTURWT", "W_FSTR"]

TREATMENT_CANDIDATES = [
    "ESCS",
    "ANXMAT",
    "MATHEF21",
    "MATHEFF",
    "TEACHSUP",
    "BELONG",
    "DISCLIM",
    "HOMEPOS",
    "ICTQUAL",
    "ICTSCH",
    "ICTENQ",
    "BULLIED",
    "FEELSAFE",
    "REPEAT",
]

CONTROL_CANDIDATES = [
    "CNT",
    "CNTSCHID",
    "CNTSTUID",
    "ST004D01T",
    "AGE",
    "GRADE",
    "IMMIG",
    "LANGN",
    "HISCED",
    "PAREDINT",
    "HISEI",
    "SCHLTYPE",
    "STRATIO",
    "SCHSIZE",
    "RELATST",
    "STUBEHA",
    "SCHRISK",
]

ID_VARS = ["CNTSTUID", "CNTSCHID"]
NON_FEATURE_VARS = set(PV_MATH_VARS + [MATH_MEAN_COL, FINAL_STUDENT_WEIGHT] + ID_VARS)

MISSING_RATE_THRESHOLD = 0.5
MIN_DML_N = 200
MIN_TREATMENT_UNIQUE = 3
DML_N_FOLDS = 3
SHAP_MAX_N = 3000

RF_PARAMS = {
    "n_estimators": 300,
    "min_samples_leaf": 5,
    "n_jobs": -1,
    "random_state": RANDOM_STATE,
}

EXTRA_TREES_PARAMS = {
    "n_estimators": 500,
    "min_samples_leaf": 3,
    "max_features": 0.8,
    "n_jobs": -1,
    "random_state": RANDOM_STATE,
}

LGBM_PARAMS = {
    "n_estimators": 500,
    "learning_rate": 0.03,
    "num_leaves": 31,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
    "verbose": -1,
}

OUT_PATH = Path(OUT_DIR)
