"""Per-tract predictions and SHAP values for the static site.

Fits the tuned Random Forest from outputs/rf_best_params.json on the same
train split as notebook 04, then explains every tract with TreeSHAP
(tree_path_dependent, no background data). For a scikit-learn random forest
these values plus the base value add up to predict_proba, which is checked.

Runs independently of the notebooks, so it can run alongside them.

    uv run python scripts/tract_shap.py --jobs 6          # full run
    uv run python scripts/tract_shap.py --limit 300       # timing only, writes nothing
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np
import pandas as pd
import shap
import sklearn
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed" / "modeling_data_clean.csv"
PARAMS = ROOT / "outputs" / "rf_best_params.json"
PARQUET = ROOT / "outputs" / "tract_predictions_shap.parquet"
META = ROOT / "outputs" / "tract_shap_meta.json"

FEATURES = [
    "MedianFamilyIncome", "PovertyRate", "pct_nhblack10", "pct_hisp10",
    "pct_nhwhite10", "pct_hunv10", "pct_snap16", "Pop2010", "Urban",
]
TARGET = "LILATracts_1And10"
TRACT = "CensusTract"
RANDOM_STATE = 42


def positive_class(values) -> np.ndarray:
    """SHAP values for class 1, whatever shape this shap version returns."""
    if isinstance(values, list):
        values = values[1]
    values = np.asarray(values)
    return values[..., 1] if values.ndim == 3 else values


def floor_thresholds_to_float32(explainer) -> None:
    """Match scikit-learn's float32 split routing (see notebook 04, Section 5)."""
    t = explainer.model.thresholds
    t32 = t.astype(np.float32)
    above = t32.astype(np.float64) > t
    t32[above] = np.nextafter(t32[above], np.float32(-np.inf))
    explainer.model.thresholds = t32.astype(np.float64)


def explain(explainer, rows: pd.DataFrame) -> np.ndarray:
    return positive_class(explainer.shap_values(rows, check_additivity=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4, help="worker processes for SHAP")
    ap.add_argument("--limit", type=int, default=0, help="time N rows on one core, write nothing")
    args = ap.parse_args()

    df = pd.read_csv(DATA)
    X, y = df[FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE)

    record = json.loads(PARAMS.read_text())
    if record["random_state"] != RANDOM_STATE:
        raise ValueError("rf_best_params.json uses a different random_state")
    rf = RandomForestClassifier(**record["best_params"], random_state=RANDOM_STATE, n_jobs=args.jobs)
    rf.fit(X_train, y_train)

    explainer = shap.TreeExplainer(rf)  # tree_path_dependent
    floor_thresholds_to_float32(explainer)
    base = float(np.ravel(explainer.expected_value)[-1])

    if args.limit:
        rows = X.iloc[: args.limit]
        t0 = time.perf_counter()
        sv = explain(explainer, rows)
        secs = time.perf_counter() - t0
        gap = np.abs(base + sv.sum(1) - rf.predict_proba(rows)[:, 1]).max()
        per_row = secs / len(rows)
        print(f"{len(rows)} rows on 1 core: {secs:.1f} s ({per_row * 1000:.1f} ms/row), additivity gap {gap:.1e}")
        for jobs in (4, 6, 8):
            print(f"  projected full run with {jobs} workers: {per_row * len(X) / jobs / 60:.1f} min")
        return

    proba = rf.predict_proba(X)[:, 1]
    t0 = time.perf_counter()
    chunks = np.array_split(np.arange(len(X)), args.jobs * 4)
    parts = Parallel(n_jobs=args.jobs)(delayed(explain)(explainer, X.iloc[c]) for c in chunks)
    sv = np.concatenate(parts)
    secs = time.perf_counter() - t0

    gap = float(np.abs(base + sv.sum(1) - proba).max())
    if gap > 1e-6:
        raise ValueError(f"SHAP values do not add up to predict_proba (max gap {gap:.2e})")

    names = np.array(FEATURES)
    top = np.argsort(-np.abs(sv), axis=1)[:, :3]
    top_vals = np.take_along_axis(sv, top, axis=1)
    out = pd.DataFrame({
        TRACT: df[TRACT],
        "predicted_label": rf.predict(X),
        "prediction_probability": proba,
        **{f"top{k + 1}_feature": names[top[:, k]] for k in range(3)},
        **{f"top{k + 1}_shap": top_vals[:, k] for k in range(3)},
        "pct_nhblack10": df["pct_nhblack10"],
        "pct_hisp10": df["pct_hisp10"],
        "pct_nhwhite10": df["pct_nhwhite10"],
        TARGET: y,
    })
    # Same column order as the parquet notebook 04 used to write.
    out = out[[TRACT, "predicted_label", "prediction_probability",
               "top1_feature", "top1_shap", "top2_feature", "top2_shap",
               "top3_feature", "top3_shap", "pct_nhblack10", "pct_hisp10",
               "pct_nhwhite10", TARGET]]
    out.to_parquet(PARQUET, index=False)

    meta = {
        "test_f1": float(f1_score(y_test, rf.predict(X_test))),
        "test_roc_auc": float(roc_auc_score(y_test, rf.predict_proba(X_test)[:, 1])),
        "n_rows": int(len(out)),
        "prob_min": float(proba.min()),
        "prob_max": float(proba.max()),
        "base_value": base,
        "additivity_gap": gap,
        "shap_seconds": round(secs, 1),
        "jobs": args.jobs,
        "feature_perturbation": "tree_path_dependent",
        "shap_version": shap.__version__,
        "sklearn_version": sklearn.__version__,
    }
    META.write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
