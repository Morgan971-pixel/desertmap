"""
DesertMap — Gradio app for HuggingFace Spaces
Predicts food desert status across 72,531 U.S. census tracts and
audits the model for redlining-era racial bias.
"""

import pathlib
from collections import defaultdict

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

# ── Paths — works from app/ locally and from root on HF Spaces ───────────────
_HERE = pathlib.Path(__file__).parent
ROOT = _HERE if not (_HERE / "outputs").exists() else _HERE
if not (ROOT / "outputs" / "tract_predictions_shap.parquet").exists():
    ROOT = _HERE.parent

PARQUET_PATH  = ROOT / "outputs" / "tract_predictions_shap.parquet"
CENTROID_PATH = ROOT / "data"    / "raw" / "CenPop2010_Mean_TR.txt"
HOLC_PATH     = ROOT / "data"    / "raw" / "holc_tract_crosswalk.csv"

FEATURE_LABELS = {
    "MedianFamilyIncome": "Median Family Income",
    "PovertyRate":        "Poverty Rate",
    "pct_nhblack10":      "% Black Population",
    "pct_hisp10":         "% Hispanic Population",
    "pct_nhwhite10":      "% White Population",
    "pct_hunv10":         "% No Vehicle",
    "pct_snap16":         "% SNAP Enrolled",
    "Pop2010":            "Total Population (2010)",
    "Urban":              "Urban Tract",
}

VIEW_OPTIONS = [
    "All tracts",
    "Predicted food deserts only",
    "True positives (correctly flagged)",
    "False positives (incorrectly flagged)",
]


# ── Data loading (runs once at startup) ───────────────────────────────────────
def _load_df() -> pd.DataFrame:
    preds = pd.read_parquet(PARQUET_PATH)
    cents = pd.read_csv(CENTROID_PATH)
    cents["CensusTract"] = (
        cents["STATEFP"].astype(str).str.zfill(2)
        + cents["COUNTYFP"].astype(str).str.zfill(3)
        + cents["TRACTCE"].astype(str).str.zfill(6)
    ).astype(int)
    df = preds.merge(
        cents[["CensusTract", "LATITUDE", "LONGITUDE"]],
        on="CensusTract", how="left",
    ).dropna(subset=["LATITUDE", "LONGITUDE"])
    df["correct"] = (df["predicted_label"] == df["LILATracts_1And10"]).astype(int)
    return df


def _holc_rates(df: pd.DataFrame) -> pd.Series:
    crosswalk = pd.read_csv(HOLC_PATH)
    merged = crosswalk.merge(
        df[["CensusTract", "predicted_label"]], on="CensusTract", how="inner"
    )
    return merged.groupby("holc_grade")["predicted_label"].mean().reindex(["A", "B", "C", "D"])


def _global_shap(df: pd.DataFrame):
    totals: dict = defaultdict(float)
    for col in ["top1_feature", "top2_feature", "top3_feature"]:
        shap_col = col.replace("feature", "shap")
        for feat, val in zip(df[col], df[shap_col].abs()):
            totals[feat] += float(val)
    s = pd.Series(totals).sort_values()
    s.index = [FEATURE_LABELS.get(f, f) for f in s.index]
    return s, s / s.max()


DF         = _load_df()
RATES      = _holc_rates(DF)
HERO_RATIO = (RATES["C"] + RATES["D"]) / (RATES["A"] + RATES["B"])
SHAP_S, SHAP_NORM = _global_shap(DF)


# ── Chart builders ────────────────────────────────────────────────────────────
def _filter_df(view: str, min_prob: float) -> pd.DataFrame:
    filt = DF[DF["prediction_probability"] >= min_prob]
    if view == "Predicted food deserts only":
        filt = filt[filt["predicted_label"] == 1]
    elif view == "True positives (correctly flagged)":
        filt = filt[(filt["predicted_label"] == 1) & (filt["LILATracts_1And10"] == 1)]
    elif view == "False positives (incorrectly flagged)":
        filt = filt[(filt["predicted_label"] == 1) & (filt["LILATracts_1And10"] == 0)]
    return filt


def map_figure(view: str, min_prob: float) -> go.Figure:
    filt = _filter_df(view, min_prob)
    fig = go.Figure(go.Scattermapbox(
        lat=filt["LATITUDE"].tolist(),
        lon=filt["LONGITUDE"].tolist(),
        mode="markers",
        marker=dict(
            size=5,
            color=filt["prediction_probability"].tolist(),
            colorscale=[[0, "#3191d0"], [0.5, "#a855f7"], [1, "#f97316"]],
            cmin=0, cmax=1,
            showscale=True,
            colorbar=dict(
                title=dict(text="P(food desert)", font=dict(color="#8b949e", size=11)),
                thickness=10, len=0.45,
                tickfont=dict(color="#8b949e", size=10),
                bgcolor="#0d1117",
            ),
            opacity=0.75,
        ),
        customdata=filt[["CensusTract", "predicted_label", "LILATracts_1And10", "top1_feature"]].values,
        hovertemplate=(
            "<b>Tract %{customdata[0]}</b><br>"
            "P(food desert): <b>%{marker.color:.3f}</b><br>"
            "Predicted: %{customdata[1]} | Actual: %{customdata[2]}<br>"
            "Top driver: %{customdata[3]}<extra></extra>"
        ),
    ))
    fig.update_layout(
        mapbox=dict(style="carto-darkmatter", center=dict(lat=38.5, lon=-96.5), zoom=3.2),
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0d1117",
        uirevision="map",
    )
    return fig


def holc_chart() -> go.Figure:
    grade_colors = {"A": "#22c55e", "B": "#3b82f6", "C": "#f59e0b", "D": "#ef4444"}
    cd = (RATES["C"] + RATES["D"]) / 2 * 100
    ab = (RATES["A"] + RATES["B"]) / 2 * 100
    fig = go.Figure(go.Bar(
        x=RATES.index.tolist(),
        y=(RATES.values * 100).tolist(),
        marker_color=[grade_colors[g] for g in RATES.index],
        text=[f"{v*100:.1f}%" for v in RATES.values],
        textposition="outside",
        textfont=dict(color="#e6edf3", size=13),
        width=0.55,
    ))
    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=30, b=40),
        xaxis=dict(title="HOLC Grade (A = Best, D = Hazardous)", color="#8b949e",
                   tickfont=dict(size=14, color="#e6edf3"), gridcolor="#21262d"),
        yaxis=dict(title="% predicted food desert", color="#8b949e",
                   gridcolor="#21262d", range=[0, max(RATES.values) * 130], ticksuffix="%"),
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        showlegend=False,
        annotations=[dict(
            x=1.5, y=max(RATES.values) * 120,
            text=f"<b>C+D tracts: {cd:.1f}%</b><br>vs A+B: {ab:.1f}%",
            showarrow=False, font=dict(color="#ef4444", size=11),
            bgcolor="rgba(239,68,68,0.1)", bordercolor="#ef4444",
            borderwidth=1, borderpad=6,
        )],
    )
    return fig


def shap_global_chart() -> go.Figure:
    colors = [f"rgba(249,115,22,{0.4 + 0.6 * v})" for v in SHAP_NORM.values]
    fig = go.Figure(go.Bar(
        x=SHAP_S.values, y=SHAP_S.index, orientation="h",
        marker_color=colors,
        text=[f"{v/1000:.1f}k" for v in SHAP_S.values],
        textposition="outside",
        textfont=dict(color="#8b949e", size=10),
    ))
    fig.update_layout(
        height=340, margin=dict(l=0, r=160, t=10, b=10),
        xaxis=dict(title="Cumulative |SHAP| across all tracts", color="#8b949e",
                   gridcolor="#21262d", showticklabels=False),
        yaxis=dict(color="#e6edf3", tickfont=dict(size=11)),
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        showlegend=False,
    )
    return fig


# ── Tract detail (text lookup) ────────────────────────────────────────────────
def tract_detail(tract_id_str: str):
    try:
        tract_id = int(str(tract_id_str).strip().replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return "<p style='color:#8b949e;padding:1rem;font-family:Inter,sans-serif'>Enter a census tract ID.</p>", None

    rows = DF[DF["CensusTract"] == tract_id]
    if rows.empty:
        return (
            f"<p style='color:#ef4444;padding:1rem;font-family:Inter,sans-serif'>"
            f"Tract {tract_id} not found. Try one from the map tooltip.</p>",
            None,
        )

    row  = rows.iloc[0]
    actual  = int(row["LILATracts_1And10"])
    pred    = int(row["predicted_label"])
    prob    = float(row["prediction_probability"])
    correct = actual == pred

    def _tag(text, color):
        return (
            f"<span style=\"background:rgba(0,0,0,0.3);color:{color};"
            f"border:1px solid {color};border-radius:6px;"
            f"padding:0.15rem 0.55rem;font-size:0.82rem\">{text}</span>"
        )

    actual_tag  = _tag("Food Desert" if actual else "Not Food Desert",
                       "#ef4444" if actual else "#22c55e")
    pred_tag    = _tag("Food Desert" if pred else "Not Food Desert",
                       "#ef4444" if pred else "#22c55e")
    outcome_tag = _tag("Correct" if correct else "Incorrect",
                       "#22c55e" if correct else "#ef4444")

    html = f"""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:14px;
                padding:1.5rem 2rem;margin-top:0.5rem;font-family:Inter,sans-serif">
        <div style="font-size:1.1rem;font-weight:700;color:#e6edf3;margin-bottom:0.75rem">
            Census Tract {tract_id:,}
        </div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem">
            Actual: {actual_tag} &nbsp; Predicted: {pred_tag} &nbsp; {outcome_tag}
        </div>
        <table style="width:100%;font-size:0.9rem;border-collapse:collapse;color:#c9d1d9">
            <tr><td style="color:#8b949e;padding:0.3rem 0">Prediction probability</td>
                <td style="color:#f97316;font-weight:700;text-align:right">{prob:.4f}</td></tr>
            <tr><td style="color:#8b949e;padding:0.3rem 0">% Black population</td>
                <td style="text-align:right">{float(row['pct_nhblack10']):.1f}%</td></tr>
            <tr><td style="color:#8b949e;padding:0.3rem 0">% Hispanic population</td>
                <td style="text-align:right">{float(row['pct_hisp10']):.1f}%</td></tr>
            <tr><td style="color:#8b949e;padding:0.3rem 0">% White population</td>
                <td style="text-align:right">{float(row['pct_nhwhite10']):.1f}%</td></tr>
            <tr><td style="color:#8b949e;padding:0.3rem 0">Median family income</td>
                <td style="text-align:right">${float(row['MedianFamilyIncome']):,.0f}</td></tr>
            <tr><td style="color:#8b949e;padding:0.3rem 0">Poverty rate</td>
                <td style="text-align:right">{float(row['PovertyRate']):.1f}%</td></tr>
        </table>
    </div>
    """

    features = [FEATURE_LABELS.get(row[f"top{i}_feature"], row[f"top{i}_feature"]) for i in (1, 2, 3)]
    values   = [float(row[f"top{i}_shap"]) for i in (1, 2, 3)]
    colors   = ["#ef4444" if v > 0 else "#3b82f6" for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=features, orientation="h",
        marker_color=colors,
        text=[f"{v:+.3f}" for v in values],
        textposition="outside",
        textfont=dict(color="#e6edf3", size=12),
    ))
    fig.add_vline(x=0, line_width=1, line_color="#484f58")
    fig.update_layout(
        height=220, margin=dict(l=0, r=60, t=30, b=10),
        title=dict(text="Why did the model predict this?",
                   font=dict(color="#8b949e", size=12), x=0),
        xaxis=dict(title="SHAP value", color="#8b949e", gridcolor="#21262d",
                   zerolinecolor="#30363d"),
        yaxis=dict(autorange="reversed", color="#e6edf3", tickfont=dict(size=11)),
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        showlegend=False,
    )
    return html, fig


def update_map(view: str, min_prob: float):
    filt = _filter_df(view, min_prob)
    count_html = (
        f"<div style='padding-top:1.5rem;color:#8b949e;font-size:0.85rem;"
        f"font-family:Inter,sans-serif'>{len(filt):,} of {len(DF):,} tracts shown</div>"
    )
    return map_figure(view, min_prob), count_html


# ── Static HTML blocks ────────────────────────────────────────────────────────
_HERO = f"""
<div style="background:linear-gradient(140deg,#0d1117 0%,#0f1d3a 60%,#190f2e 100%);
            border-bottom:3px solid #f97316;padding:4rem 2rem 3rem;
            text-align:center;font-family:Inter,-apple-system,sans-serif">
    <p style="font-size:0.78rem;letter-spacing:0.22em;text-transform:uppercase;
              color:#f97316;font-weight:700;margin-bottom:1rem">
        AI4ALL Ignite &middot; DesertMap &middot; Machine Learning &amp; Fairness Audit
    </p>
    <h1 style="font-size:clamp(2rem,5vw,3.5rem);font-weight:900;color:#fff;
               line-height:1.08;margin:0 0 0.8rem">
        19 Million Americans<br>Live in Food Deserts
    </h1>
    <p style="font-size:1rem;color:#8b949e;max-width:600px;margin:0 auto 2rem;line-height:1.65">
        We built a machine learning model to predict which neighborhoods qualify as food deserts.
        We discovered it had silently learned the geography of 1930s racial discrimination,
        without ever being shown that data.
    </p>
    <div style="display:flex;justify-content:center;flex-wrap:wrap;gap:0.75rem">
        <div style="background:rgba(22,27,34,0.85);border:1px solid #30363d;
                    border-radius:999px;padding:0.6rem 1.6rem;white-space:nowrap">
            <strong style="color:#f97316;font-size:1.3rem;font-weight:900">72,531</strong>
            <span style="color:#8b949e;font-size:0.88rem;margin-left:0.5rem">census tracts analyzed</span>
        </div>
        <div style="background:rgba(22,27,34,0.85);border:1px solid #30363d;
                    border-radius:999px;padding:0.6rem 1.6rem;white-space:nowrap">
            <strong style="color:#f97316;font-size:1.3rem;font-weight:900">16.4%</strong>
            <span style="color:#8b949e;font-size:0.88rem;margin-left:0.5rem">qualify as food deserts</span>
        </div>
        <div style="background:rgba(22,27,34,0.85);border:1px solid #ef4444;
                    border-radius:999px;padding:0.6rem 1.6rem;white-space:nowrap">
            <strong style="color:#ef4444;font-size:1.3rem;font-weight:900">{HERO_RATIO:.2f}&times;</strong>
            <span style="color:#8b949e;font-size:0.88rem;margin-left:0.5rem">HOLC redlining disparity</span>
        </div>
    </div>
</div>
"""

_BIAS_METRICS = [
    ("#f97316", f"{HERO_RATIO:.2f}×", "HOLC Disparity",
     f"C/D-graded tracts are {HERO_RATIO:.2f}× more likely to be predicted food deserts than A/B-graded tracts"),
    ("#ef4444", "5.9×", "Misclassification Is Unequal",
     "False positive rate in the highest-Black-share quartile is 5.9× that of the lowest quartile"),
    ("#a855f7", "33.6%", "When Race Changes, Predictions Change",
     "33.6% of food desert predictions flipped when racial composition was reset to the national median"),
    ("#3b82f6", "−2.2 pts", "Race Carries Independent Signal",
     "Removing % Black and % Hispanic drops F1 by 2.2 points — racial features add signal beyond income alone"),
]

_BIAS_CARDS = "".join(
    f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:14px;
                    padding:1.5rem;text-align:center;flex:1;min-width:180px">
            <div style="font-size:2rem;font-weight:900;color:{color};margin-bottom:0.3rem">{val}</div>
            <div style="font-size:0.75rem;font-weight:700;color:#8b949e;text-transform:uppercase;
                        letter-spacing:0.1em;margin-bottom:0.6rem">{label}</div>
            <div style="font-size:0.83rem;color:#c9d1d9;line-height:1.5">{desc}</div>
        </div>"""
    for color, val, label, desc in _BIAS_METRICS
)

_BIAS_HEADER = f"""
<div style="font-family:Inter,sans-serif;padding:1rem 0">
    <h2 style="color:#e6edf3;font-size:1.5rem;margin:0 0 0.4rem">
        The Model Remembered Something It Was Never Shown
    </h2>
    <p style="font-size:1rem;font-style:italic;color:#8b949e;
               border-left:3px solid #f97316;padding-left:1rem;margin:0 0 1.5rem">
        "AI trained on present data inherits past policy.
        Responsible development detects this. Deployment without auditing does not."
    </p>
    <p style="color:#c9d1d9;font-size:0.95rem;line-height:1.75;max-width:800px;margin-bottom:1.5rem">
        The model was never shown HOLC redlining maps. After training on modern socioeconomic data,
        its predictions were overlaid on 1930s federal neighborhood grades.
        Four independent tests confirm the same pattern.
    </p>
    <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:2rem">
        {_BIAS_CARDS}
    </div>
    <h3 style="color:#e6edf3;font-size:1.1rem;margin:1.5rem 0 0.5rem">
        Food Desert Prediction Rate by HOLC Grade
    </h3>
</div>
"""

_LIMITATIONS = """
<div style="background:#161b22;border:1px solid #30363d;border-radius:14px;
            padding:1.5rem 2rem;font-family:Inter,sans-serif;margin-top:1rem">
    <p style="font-size:0.75rem;letter-spacing:0.15em;text-transform:uppercase;
              color:#8b949e;font-weight:700;margin:0 0 0.75rem">Limitations &amp; Interpretation</p>
    <p style="font-size:0.92rem;color:#c9d1d9;line-height:1.75;margin:0 0 0.75rem">
        <strong style="color:#e6edf3">The confounding variable challenge:</strong>
        Redlined areas became low-income areas, and low-income areas have poor food access.
        The counterfactual test addresses this directly &mdash; 33.6% of predictions changed
        when only racial composition was reset, holding income and poverty constant.
        If the pattern were purely income geography, removing race should not move predictions.
    </p>
    <p style="font-size:0.92rem;color:#c9d1d9;line-height:1.75;margin:0">
        This is observational work. Causation is not established. The finding is that the pattern
        exists across four independent tests and racial features carry independent signal beyond
        income and poverty &mdash; sufficient reason to audit before any deployment affecting
        food access decisions.
    </p>
</div>
"""

_MODEL_FEATURES = "".join(
    f"""<span style="background:#0d1117;border:1px solid #30363d;border-radius:6px;
                     padding:0.2rem 0.5rem;font-size:0.8rem;color:#c9d1d9">{f}</span>"""
    for f in FEATURE_LABELS.values()
)

_MODEL_SECTION = f"""
<div style="font-family:Inter,sans-serif;padding:1rem 0">
    <h2 style="color:#e6edf3;font-size:1.5rem;margin:0 0 0.75rem">What We Built</h2>
    <p style="color:#c9d1d9;font-size:0.95rem;line-height:1.75;max-width:760px;margin:0 0 1.5rem">
        A <strong style="color:#e6edf3">Random Forest classifier</strong> trained on the
        USDA Food Access Research Atlas 2019 &mdash; 72,531 U.S. census tracts, 9 modern
        socioeconomic features, no historical redlining data. F1 is the primary metric
        given the 5:1 class imbalance.
    </p>
    <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:2rem">
        <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
                    padding:1.2rem 1.5rem;min-width:260px">
            <div style="font-size:0.75rem;color:#8b949e;text-transform:uppercase;
                        letter-spacing:0.12em;font-weight:700;margin-bottom:0.75rem">
                Performance vs. Baseline
            </div>
            <table style="width:100%;font-size:0.88rem;border-collapse:collapse;color:#c9d1d9">
                <tr style="color:#8b949e;font-size:0.78rem">
                    <td>Model</td>
                    <td style="text-align:right">F1</td>
                    <td style="text-align:right">Prec.</td>
                    <td style="text-align:right">Recall</td>
                    <td style="text-align:right">AUC</td>
                </tr>
                <tr style="color:#8b949e">
                    <td style="padding:0.4rem 0">Logistic Regression</td>
                    <td style="text-align:right">0.438</td>
                    <td style="text-align:right">0.302</td>
                    <td style="text-align:right">0.800</td>
                    <td style="text-align:right">0.838</td>
                </tr>
                <tr style="font-weight:700;color:#e6edf3;border-top:1px solid #30363d">
                    <td style="padding:0.4rem 0">Random Forest &#10003;</td>
                    <td style="text-align:right;color:#f97316">0.525</td>
                    <td style="text-align:right">0.416</td>
                    <td style="text-align:right">0.710</td>
                    <td style="text-align:right">0.886</td>
                </tr>
            </table>
        </div>
        <div style="background:#161b22;border:1px solid #3b82f6;border-radius:12px;
                    padding:1.2rem 1.5rem;min-width:240px;flex:1">
            <div style="font-size:0.75rem;color:#3b82f6;text-transform:uppercase;
                        letter-spacing:0.12em;font-weight:700;margin-bottom:0.75rem">
                9 Training Features
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:0.4rem">
                {_MODEL_FEATURES}
            </div>
            <p style="font-size:0.8rem;color:#484f58;margin:0.75rem 0 0;line-height:1.5">
                No HOLC data. No ZIP codes. No neighborhood names.
            </p>
        </div>
    </div>
    <h2 style="color:#e6edf3;font-size:1.5rem;margin:0 0 0.5rem">
        Global Feature Importance (SHAP)
    </h2>
    <p style="color:#c9d1d9;font-size:0.9rem;line-height:1.75;max-width:760px;margin:0 0 1rem">
        SHAP applied via TreeExplainer on 2,000 representative test tracts. Median family income
        and poverty rate dominate. Racial composition features appear in the top five &mdash;
        carrying independent predictive signal beyond income alone.
    </p>
</div>
"""

_FOOTER = """
<div style="text-align:center;font-size:0.82rem;color:#484f58;padding:2rem 0 1rem;
            font-family:Inter,sans-serif;border-top:1px solid #21262d;margin-top:2rem">
    DesertMap &middot; AI4ALL Ignite Accelerator &middot; 2026 &middot;
    <a href="https://github.com/Morgan971-pixel/desertmap" target="_blank"
       style="color:#8b949e;text-decoration:none">GitHub</a>
    &middot; Data: USDA ERS 2019 &middot; HOLC crosswalk: Mapping Inequality v3
</div>
"""

_MAP_LEGEND = """
<p style="font-size:0.83rem;color:#8b949e;margin:0.4rem 0 1.5rem;font-family:Inter,sans-serif">
    <span style="color:#3191d0">&#9679;</span> Low probability &nbsp;&nbsp;
    <span style="color:#a855f7">&#9679;</span> Medium &nbsp;&nbsp;
    <span style="color:#f97316">&#9679;</span> High probability &nbsp;&mdash;&nbsp;
    hover a dot for tract details &middot; use dropdown and slider to filter
</p>
"""

_TRACT_HINT = """
<p style="font-size:0.88rem;color:#8b949e;margin:0 0 0.5rem;font-family:Inter,sans-serif">
    <strong style="color:#e6edf3">Tract Explorer</strong> &mdash;
    hover any dot on the map to see its census tract ID, then type it here.
</p>
"""


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');

body, .gradio-container, .gr-prose {
    font-family: 'Inter', -apple-system, sans-serif !important;
    background: #0d1117 !important;
    color: #e6edf3 !important;
}
.gradio-container { max-width: 1400px !important; margin: 0 auto !important; }

/* tabs */
.tab-nav button {
    background: transparent !important;
    color: #8b949e !important;
    border-bottom: 2px solid transparent !important;
    font-weight: 600 !important;
    transition: color 0.15s, border-color 0.15s;
}
.tab-nav button.selected {
    color: #f97316 !important;
    border-bottom-color: #f97316 !important;
}

/* inputs */
input, select, textarea {
    background: #161b22 !important;
    border-color: #30363d !important;
    color: #e6edf3 !important;
}
label { color: #8b949e !important; font-size: 0.85rem !important; }

/* plot containers */
.js-plotly-plot .plotly, .plot-container { background: transparent !important; }

/* blocks */
.gr-block, .gr-box { background: transparent !important; border: none !important; }
.gr-form { background: transparent !important; }

/* button */
.gr-button-primary {
    background: #f97316 !important;
    border-color: #f97316 !important;
    color: #1a0900 !important;
    font-weight: 700 !important;
}

footer, .footer { display: none !important; }
"""


# ── Build the Gradio app ──────────────────────────────────────────────────────
with gr.Blocks(
    title="DesertMap — Food Desert Predictions & Bias Audit",
    css=CSS,
    analytics_enabled=False,
) as demo:

    gr.HTML(_HERO)

    with gr.Tabs():

        # ────────────────────────────────────────────────────────────────────
        # Tab 1 — Map
        # ────────────────────────────────────────────────────────────────────
        with gr.Tab("Interactive Map"):
            with gr.Row():
                view_dd = gr.Dropdown(
                    choices=VIEW_OPTIONS, value="All tracts",
                    label="Show", scale=2,
                )
                prob_slider = gr.Slider(
                    minimum=0.0, maximum=1.0, value=0.0, step=0.01,
                    label="Min prediction probability", scale=3,
                )
                count_display = gr.HTML(
                    f"<div style='padding-top:1.5rem;color:#8b949e;font-size:0.85rem;"
                    f"font-family:Inter,sans-serif'>{len(DF):,} of {len(DF):,} tracts shown</div>",
                    scale=1,
                )

            map_plot = gr.Plot(value=map_figure("All tracts", 0.0), show_label=False)
            gr.HTML(_MAP_LEGEND)

            gr.HTML("<hr style='border:none;border-top:1px solid #21262d;margin:0.5rem 0'>")
            gr.HTML(_TRACT_HINT)

            with gr.Row():
                tract_input = gr.Textbox(
                    label="Census Tract ID",
                    placeholder="e.g. 6037204200 (Los Angeles County)",
                    scale=4,
                )
                tract_btn = gr.Button("Look up", variant="primary", scale=1)

            with gr.Row():
                tract_html_out  = gr.HTML()
                shap_detail_out = gr.Plot(show_label=False)

            view_dd.change(update_map,    [view_dd, prob_slider], [map_plot, count_display])
            prob_slider.change(update_map, [view_dd, prob_slider], [map_plot, count_display])
            tract_btn.click(tract_detail,  [tract_input], [tract_html_out, shap_detail_out])
            tract_input.submit(tract_detail, [tract_input], [tract_html_out, shap_detail_out])

        # ────────────────────────────────────────────────────────────────────
        # Tab 2 — Model & Explainability
        # ────────────────────────────────────────────────────────────────────
        with gr.Tab("Model & Explainability"):
            gr.HTML(_MODEL_SECTION)
            gr.Plot(value=shap_global_chart(), show_label=False)

        # ────────────────────────────────────────────────────────────────────
        # Tab 3 — Bias Audit
        # ────────────────────────────────────────────────────────────────────
        with gr.Tab("Bias Audit"):
            gr.HTML(_BIAS_HEADER)
            gr.Plot(value=holc_chart(), show_label=False)
            gr.HTML(_LIMITATIONS)

    gr.HTML(_FOOTER)


if __name__ == "__main__":
    demo.launch()
