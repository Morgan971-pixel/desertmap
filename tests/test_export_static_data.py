import json
import math
import pathlib

import pytest

import export_static_data as ex

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAIR = json.loads((ROOT / "outputs" / "fairness_metrics.json").read_text())


@pytest.fixture(scope="module")
def tracts():
    return ex.load_tracts()


def test_load_tracts_keeps_almost_all_rows_and_has_coords(tracts):
    assert len(tracts) == 72_506
    assert tracts["LATITUDE"].notna().all()
    assert tracts["LONGITUDE"].notna().all()


def test_payload_is_columnar_and_aligned(tracts):
    p = ex.tracts_payload(tracts)
    cols = ["id", "lat", "lon", "p", "pred", "actual",
            "f1", "s1", "f2", "s2", "f3", "s3", "black", "hisp", "white"]
    assert p["n"] == len(tracts)
    for c in cols:
        assert len(p[c]) == p["n"], c
    assert all(0 <= i < len(p["features"]) for i in p["f1"] + p["f2"] + p["f3"])


def test_probabilities_and_labels_in_range(tracts):
    p = ex.tracts_payload(tracts)
    assert min(p["p"]) >= 0 and max(p["p"]) <= 1
    assert set(p["pred"]) <= {0, 1} and set(p["actual"]) <= {0, 1}


def test_probabilities_are_raw_predict_proba(tracts):
    # An older parquet held sigmoid-squashed scores stuck inside [0.1192, 0.8806].
    p = ex.tracts_payload(tracts)
    assert min(p["p"]) < 0.12
    assert max(p["p"]) > 0.88


def test_probabilities_and_shap_rounded_once_to_display_precision(tracts):
    p = ex.tracts_payload(tracts)
    for key in ("p", "s1", "s2", "s3"):
        assert all(v == round(v, 3) for v in p[key][:5000]), key


def test_race_shares_are_uncapped(tracts):
    p = ex.tracts_payload(tracts)
    assert max(v for v in p["black"] if v is not None) > 90   # capped model input maxes at 35.4
    assert max(v for v in p["black"] if v is not None) <= 100


def test_race_shares_align_with_model_inputs_where_uncapped(tracts):
    # pct_nhblack10 = TractBlack / pop * 100, then IQR-capped; below the cap the two must agree.
    below = tracts[tracts["pct_nhblack10"] < tracts["pct_nhblack10"].max()]
    close = ((below["share_black"] - below["pct_nhblack10"]).abs() <= 0.5).mean()
    assert len(below) > 50_000
    assert close >= 0.99


def test_missing_atlas_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="atlas"):
        ex.load_tracts(atlas=tmp_path / "nope.csv")


def test_holc_ratio_matches_notebook():
    s = ex.holc_summary()
    assert math.isclose(s["ratio"], FAIR["holc_rate_ratio"], rel_tol=1e-9)
    assert FAIR["holc_odds_ratio"] == FAIR["holc_rate_ratio"]  # legacy key, same value
    assert math.isclose(s["cd_rate"], FAIR["holc_cd_pred_rate"], rel_tol=1e-9)
    assert math.isclose(s["ab_rate"], FAIR["holc_ab_pred_rate"], rel_tol=1e-9)
    assert list(s["rates"]) == ["A", "B", "C", "D"]
    assert s["ratio_test"] == FAIR["holc_rate_ratio_test"]
    assert s["label_cd_rate"] == FAIR["holc_label_cd_rate"]
    assert s["label_ab_rate"] == FAIR["holc_label_ab_rate"]
    assert s["label_ratio"] == FAIR["holc_label_rate_ratio"]


def test_summary_fpr_disparity_comes_from_notebook(tracts):
    f = ex.build_summary(tracts)["fairness"]
    assert f["fpr_disparity_q4_q1"] == FAIR["fpr_disparity_q4_q1"]
    assert f["fpr_q1"] == FAIR["fpr_q1"]
    assert f["fpr_q4"] == FAIR["fpr_q4"]
    assert math.isclose(f["fpr_q4"] / f["fpr_q1"], f["fpr_disparity_q4_q1"], rel_tol=1e-9)


def test_global_shap_sorted_descending_with_labels(tracts):
    g = ex.global_shap(tracts)
    totals = [row["total"] for row in g]
    assert totals == sorted(totals, reverse=True)
    assert {row["feature"] for row in g} <= set(ex.FEATURES)
    assert all(row["label"] for row in g)


def test_summary_food_desert_share_is_data_derived(tracts):
    s = ex.build_summary(tracts)
    assert math.isclose(s["food_desert_share"], 0.1281, abs_tol=0.0005)
    assert s["n_tracts"] == 72_531


def test_written_tracts_file_is_small(tmp_path):
    ex.main(out_dir=tmp_path)
    size_mb = (tmp_path / "tracts.json").stat().st_size / 1e6
    assert size_mb < 8
    json.loads((tmp_path / "tracts.json").read_text())
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert set(summary) == {"n_tracts", "n_mapped", "food_desert_share", "holc",
                            "global_shap", "metrics", "fairness"}
    assert "fpr_disparity_q4_q1" in summary["fairness"]
