"""Join check after the parallel steps: all of them must describe the same model.

Notebook 04, notebook 05 and scripts/tract_shap.py each refit the tuned forest
from outputs/rf_best_params.json. This confirms they agree, so the site
(parquet) and the audit (fairness_metrics.json) report one model.

    uv run python scripts/check_consistency.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"


def load(name: str) -> dict:
    return json.loads((OUT / name).read_text())


def main() -> int:
    nb04 = load("rf_metrics.json")
    nb05 = load("fairness_metrics.json")
    shp = load("tract_shap_meta.json")

    f1 = {"nb04": nb04["F1 (food desert class)"], "nb05": nb05["full_model_f1"], "tract_shap": shp["test_f1"]}
    auc = {"nb04": nb04["ROC-AUC"], "nb05": nb05["full_model_roc_auc"], "tract_shap": shp["test_roc_auc"]}

    # HOLC rate ratio recomputed from the parquet must equal notebook 05's.
    preds = pd.read_parquet(OUT / "tract_predictions_shap.parquet", columns=["CensusTract", "predicted_label"])
    holc = pd.read_csv(ROOT / "data" / "raw" / "holc_tract_crosswalk.csv")
    holc = holc[holc["holc_grade"].isin(["A", "B", "C", "D"])]
    m = preds.merge(holc, on="CensusTract", how="inner")
    cd = m.loc[m["holc_grade"].isin(["C", "D"]), "predicted_label"].mean()
    ab = m.loc[m["holc_grade"].isin(["A", "B"]), "predicted_label"].mean()
    ratio = {"nb05": nb05["holc_rate_ratio"], "parquet": cd / ab}

    failed = []
    for name, vals in (("test F1", f1), ("test ROC-AUC", auc), ("HOLC rate ratio", ratio)):
        v = list(vals.values())
        ok = np.allclose(v, v[0], rtol=0, atol=1e-9)
        print(f"{'OK  ' if ok else 'FAIL'} {name}: " + ", ".join(f"{k}={x:.4f}" for k, x in vals.items()))
        if not ok:
            failed.append(name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
