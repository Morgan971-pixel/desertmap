"""Export DesertMap's precomputed outputs to compact JSON for the static site.

Run from the repo root:  uv run python scripts/export_static_data.py
Writes site/data/tracts.json (columnar, one array per field) and site/data/summary.json.
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARQUET = ROOT / "outputs" / "tract_predictions_shap.parquet"
CENTROIDS = ROOT / "data" / "raw" / "CenPop2010_Mean_TR.txt"
CROSSWALK = ROOT / "data" / "raw" / "holc_tract_crosswalk.csv"
ATLAS = ROOT / "data" / "raw" / "FoodAccessResearchAtlasData2019.csv"
OUT_DIR = ROOT / "site" / "data"

FEATURES = [
    "MedianFamilyIncome", "PovertyRate", "pct_nhblack10", "pct_hisp10",
    "pct_nhwhite10", "pct_hunv10", "pct_snap16", "Pop2010", "Urban",
]
FEATURE_LABELS = {
    "MedianFamilyIncome": "Median Family Income",
    "PovertyRate": "Poverty Rate",
    "pct_nhblack10": "% Black Population",
    "pct_hisp10": "% Hispanic Population",
    "pct_nhwhite10": "% White Population",
    "pct_hunv10": "% Households, No Vehicle",
    "pct_snap16": "% SNAP-Enrolled Households",
    "Pop2010": "Total Population (2010)",
    "Urban": "Urban Tract (yes/no)",
}
# Figures documented in docs/fairness_audit.md and outputs/*.json.
STATIC_FINDINGS = {"fpr_disparity_q4_q1": 5.9}


def _r(series: pd.Series, nd: int) -> list:
    return [None if pd.isna(v) else round(float(v), nd) for v in series]


def load_tracts(parquet=PARQUET, centroids=CENTROIDS, atlas=ATLAS) -> pd.DataFrame:
    if not pathlib.Path(atlas).exists():
        raise FileNotFoundError(
            f"Raw USDA Food Access Research Atlas not found at {atlas}; it is required "
            "for uncapped race shares (the parquet's pct_* columns are IQR-capped)."
        )
    preds = pd.read_parquet(parquet)
    c = pd.read_csv(centroids)
    c["CensusTract"] = (
        c["STATEFP"].astype(str).str.zfill(2)
        + c["COUNTYFP"].astype(str).str.zfill(3)
        + c["TRACTCE"].astype(str).str.zfill(6)
    ).astype(int)
    df = preds.merge(c[["CensusTract", "LATITUDE", "LONGITUDE"]], on="CensusTract",
                     how="left", validate="many_to_one")
    df = df.dropna(subset=["LATITUDE", "LONGITUDE"]).reset_index(drop=True)
    n_input = len(preds)

    a = pd.read_csv(atlas, usecols=["CensusTract", "Pop2010", "TractBlack",
                                    "TractHispanic", "TractWhite"])
    pop = a["Pop2010"].where(a["Pop2010"] > 0)
    shares = ["share_black", "share_hisp", "share_white"]
    for src, dst in zip(["TractBlack", "TractHispanic", "TractWhite"], shares):
        a[dst] = (a[src] / pop * 100).clip(upper=100)
    df = df.merge(a[["CensusTract", *shares]], on="CensusTract",
                  how="left", validate="many_to_one")
    n_null = int(df[shares].isna().any(axis=1).sum())
    if n_null:
        raise ValueError(f"{n_null} tracts have null race shares after the atlas merge")
    df.attrs["n_input"] = n_input
    return df


def tracts_payload(df: pd.DataFrame) -> dict:
    idx = {f: i for i, f in enumerate(FEATURES)}
    used = set(df[["top1_feature", "top2_feature", "top3_feature"]].stack())
    unknown = used - set(FEATURES)
    if unknown:
        raise ValueError(f"Unknown SHAP features in parquet: {sorted(unknown)}")
    payload = {
        "features": FEATURES,
        "labels": [FEATURE_LABELS[f] for f in FEATURES],
        "n": int(len(df)),
        "id": df["CensusTract"].astype(int).tolist(),
        "lat": _r(df["LATITUDE"], 4),
        "lon": _r(df["LONGITUDE"], 4),
        "p": _r(df["prediction_probability"], 4),
        "pred": df["predicted_label"].astype(int).tolist(),
        "actual": df["LILATracts_1And10"].astype(int).tolist(),
        "black": _r(df["share_black"], 1),
        "hisp": _r(df["share_hisp"], 1),
        "white": _r(df["share_white"], 1),
    }
    for k in (1, 2, 3):
        payload[f"f{k}"] = [idx[f] for f in df[f"top{k}_feature"]]
        payload[f"s{k}"] = _r(df[f"top{k}_shap"], 4)
    return payload


def holc_summary(crosswalk=CROSSWALK, parquet=PARQUET) -> dict:
    # Grades E, F, blank and "C " (trailing space) are excluded on purpose to match notebook 05.
    x = pd.read_csv(crosswalk)  # grades left unstripped to match notebook 05 exactly
    preds = pd.read_parquet(parquet, columns=["CensusTract", "predicted_label"])
    m = x.merge(preds, on="CensusTract", how="inner")
    grades = ["A", "B", "C", "D"]
    m = m[m["holc_grade"].isin(grades)]
    rates = m.groupby("holc_grade")["predicted_label"].mean().reindex(grades)
    counts = m["holc_grade"].value_counts().reindex(grades)
    cd = float(m.loc[m["holc_grade"].isin(["C", "D"]), "predicted_label"].mean())
    ab = float(m.loc[m["holc_grade"].isin(["A", "B"]), "predicted_label"].mean())
    return {
        "rates": {g: float(rates[g]) for g in grades},
        "counts": {g: int(counts[g]) for g in grades},
        "cd_rate": cd,
        "ab_rate": ab,
        "ratio": cd / ab,
    }


def global_shap(df: pd.DataFrame) -> list[dict]:
    totals: dict[str, float] = {}
    for k in (1, 2, 3):
        for feat, val in zip(df[f"top{k}_feature"], df[f"top{k}_shap"].abs()):
            totals[feat] = totals.get(feat, 0.0) + float(val)
    rows = [{"feature": f, "label": FEATURE_LABELS[f], "total": t} for f, t in totals.items()]
    return sorted(rows, key=lambda r: r["total"], reverse=True)


def build_summary(df: pd.DataFrame) -> dict:
    preds = pd.read_parquet(PARQUET, columns=["LILATracts_1And10"])
    fair = json.loads((ROOT / "outputs" / "fairness_metrics.json").read_text())
    rf = json.loads((ROOT / "outputs" / "rf_metrics.json").read_text())
    lr = json.loads((ROOT / "outputs" / "baseline_metrics.json").read_text())

    def pick(m: dict) -> dict:
        return {"f1": m["F1 (food desert class)"],
                "precision": m["Precision (food desert class)"],
                "recall": m["Recall (food desert class)"],
                "roc_auc": m["ROC-AUC"]}

    return {
        "n_tracts": int(len(preds)),
        "n_mapped": int(len(df)),
        "food_desert_share": float(preds["LILATracts_1And10"].mean()),
        "holc": holc_summary(),
        "global_shap": global_shap(df),
        "metrics": {"random_forest": pick(rf), "logistic_regression": pick(lr)},
        "fairness": {
            "f1_full": fair["full_model_f1"],
            "f1_race_removed": fair["race_removed_f1"],
            "f1_delta_pts": fair["f1_delta"] * 100,
            "counterfactual_flip_rate": fair["counterfactual_flip_rate"],
            **STATIC_FINDINGS,
        },
    }


def main(out_dir: pathlib.Path = OUT_DIR) -> None:
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_tracts()
    (out_dir / "tracts.json").write_text(json.dumps(tracts_payload(df), separators=(",", ":"), allow_nan=False))
    (out_dir / "summary.json").write_text(json.dumps(build_summary(df), indent=2, allow_nan=False))
    print(f"dropped {df.attrs['n_input'] - len(df)} tracts without centroids")
    print(f"wrote {len(df):,} tracts -> {out_dir}")


if __name__ == "__main__":
    main()
