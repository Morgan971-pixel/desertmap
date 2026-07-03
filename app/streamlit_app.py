import pathlib
from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DesertMap: Food Desert Predictions & Bias Audit",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT          = pathlib.Path(__file__).parent.parent
PARQUET_PATH  = ROOT / "outputs" / "tract_predictions_shap.parquet"
CENTROID_PATH = ROOT / "data" / "raw" / "CenPop2010_Mean_TR.txt"

FEATURE_LABELS = {
    "MedianFamilyIncome": "Median Family Income",
    "PovertyRate":        "Poverty Rate",
    "pct_nhblack10":      "% Black Population",
    "pct_hisp10":         "% Hispanic Population",
    "pct_nhwhite10":      "% White Population",
    "pct_hunv10":         "% Households, No Vehicle",
    "pct_snap16":         "% SNAP-Enrolled Households",
    "Pop2010":            "Total Population (2010)",
    "Urban":              "Urban Tract (yes/no)",
}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,600;0,700;0,900;1,400&display=swap');

html, body, [class*="css"], h1, h2, h3, p {
    font-family: 'Inter', -apple-system, sans-serif !important;
}

#MainMenu, footer, [data-testid="stToolbar"]  { visibility: hidden; }
[data-testid="collapsedControl"]              { display: none; }
[data-testid="stSidebar"]                     { display: none; }

.block-container {
    padding-top: 0 !important;
    padding-bottom: 4rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px !important;
}

/* ── Hero ──────────────────────────────────────────────────────────────────── */
.hero {
    background: linear-gradient(140deg, #0d1117 0%, #0f1d3a 60%, #190f2e 100%);
    border-bottom: 3px solid #f97316;
    padding: 5rem 2rem 4rem;
    text-align: center;
    margin: 0 -2rem 0 -2rem;
}
.hero-eyebrow {
    font-size: 0.78rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #f97316;
    font-weight: 700;
    margin-bottom: 1.2rem;
}
.hero-headline {
    font-size: clamp(2.2rem, 5vw, 3.8rem);
    font-weight: 900;
    color: #ffffff;
    line-height: 1.08;
    margin: 0 0 1rem;
}
.hero-sub {
    font-size: 1.08rem;
    color: #8b949e;
    max-width: 640px;
    margin: 0 auto 2.5rem;
    line-height: 1.65;
}
.hero-pills {
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 0.75rem;
}
.hero-pill {
    background: rgba(22,27,34,0.85);
    border: 1px solid #30363d;
    border-radius: 999px;
    padding: 0.6rem 1.6rem;
    white-space: nowrap;
}
.hero-pill strong { color: #f97316; font-size: 1.35rem; font-weight: 900; }
.hero-pill-red strong { color: #ef4444; }
.hero-pill span { color: #8b949e; font-size: 0.9rem; margin-left: 0.5rem; }

/* ── Section chrome ────────────────────────────────────────────────────────── */
.sec-label {
    font-size: 0.75rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #f97316;
    font-weight: 700;
    margin: 0 0 0.4rem;
}
.sec-div {
    height: 1px;
    background: linear-gradient(to right, #30363d, transparent);
    margin: 3.5rem 0 3rem;
}

/* ── Cards ─────────────────────────────────────────────────────────────────── */
.card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1rem;
    line-height: 1.65;
}
.card-orange { border-left: 4px solid #f97316; }
.card-blue   { border-left: 4px solid #3b82f6; }
.card-red    { border-left: 4px solid #ef4444; }
.card-green  { border-left: 4px solid #22c55e; }

/* ── Bias metric cards ─────────────────────────────────────────────────────── */
.bcard {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 14px;
    padding: 1.75rem 1.5rem;
    text-align: center;
    height: 100%;
}
.bcard-num {
    font-size: 3rem;
    font-weight: 900;
    line-height: 1;
    display: block;
    margin-bottom: 0.4rem;
}
.bcard-orange { color: #f97316; }
.bcard-red    { color: #ef4444; }
.bcard-title {
    font-size: 0.88rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #8b949e;
    display: block;
    margin-bottom: 0.75rem;
}
.bcard-desc {
    font-size: 0.88rem;
    color: #c9d1d9;
    line-height: 1.55;
    display: block;
}

/* ── Feature chips ─────────────────────────────────────────────────────────── */
.chips { display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 1.1rem 0; }
.chip {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 0.32rem 0.8rem;
    font-size: 0.85rem;
    color: #c9d1d9;
}

/* ── Table ─────────────────────────────────────────────────────────────────── */
.perf-table-wrap { overflow-x: auto; border-radius: 10px; }
.perf-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.93rem;
    background: #161b22;
    border-radius: 10px;
    border: 1px solid #30363d;
    white-space: nowrap;
}
.perf-table th {
    background: #21262d;
    color: #8b949e;
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 0.65rem 1rem;
    text-align: left;
    border-bottom: 1px solid #30363d;
}
.perf-table td {
    padding: 0.8rem 1rem;
    border-bottom: 1px solid #21262d;
    color: #e6edf3;
}
.perf-table tr:last-child td { border-bottom: none; }
.highlight-row td { color: #f97316; font-weight: 700; }
.win-badge {
    background: rgba(249,115,22,0.15);
    color: #f97316;
    border-radius: 4px;
    padding: 0.1rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 700;
    margin-left: 0.4rem;
    vertical-align: middle;
    display: inline-block;
}

/* ── Tract detail panel ────────────────────────────────────────────────────── */
.detail-panel {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 14px;
    padding: 1.5rem 2rem;
    margin-top: 1.5rem;
}
.detail-tract-id {
    font-size: 1.4rem;
    font-weight: 700;
    color: #e6edf3;
}
.detail-meta {
    font-size: 0.85rem;
    color: #8b949e;
    margin-top: 0.3rem;
}
.tag {
    display: inline-block;
    border-radius: 5px;
    padding: 0.15rem 0.6rem;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 0.35rem;
}
.tag-fd     { background: rgba(239,68,68,0.2);  color: #ef4444; }
.tag-ok     { background: rgba(34,197,94,0.2);  color: #22c55e; }
.tag-wrong  { background: rgba(249,115,22,0.2); color: #f97316; }
.tag-right  { background: rgba(34,197,94,0.2);  color: #22c55e; }

/* ── Callout quote ─────────────────────────────────────────────────────────── */
.pull-quote {
    border-left: 3px solid #f97316;
    padding: 0.75rem 1.5rem;
    margin: 1.5rem 0;
    font-size: 1.05rem;
    font-style: italic;
    color: #c9d1d9;
    line-height: 1.6;
}

/* ── Footer ────────────────────────────────────────────────────────────────── */
.footer {
    text-align: center;
    color: #8b949e;
    font-size: 0.78rem;
    padding: 2rem 0 1rem;
    border-top: 1px solid #21262d;
    margin-top: 4rem;
}
.footer a { color: #8b949e; text-decoration: underline; }
.footer a:hover { color: #c9d1d9; }

/* ── Button contrast fix ───────────────────────────────────────────────────── */
button[data-testid="stBaseButton-primary"] {
    color: #1a0900 !important;
    font-weight: 700 !important;
}

/* ── Scroll reveal ─────────────────────────────────────────────────────────── */
.reveal-up {
    opacity: 0;
    transform: translateY(38px);
    transition: opacity .65s cubic-bezier(.16,1,.3,1),
                transform .65s cubic-bezier(.16,1,.3,1);
}
.reveal-left {
    opacity: 0;
    transform: translateX(-38px);
    transition: opacity .65s cubic-bezier(.16,1,.3,1),
                transform .65s cubic-bezier(.16,1,.3,1);
}
.reveal-right {
    opacity: 0;
    transform: translateX(38px);
    transition: opacity .65s cubic-bezier(.16,1,.3,1),
                transform .65s cubic-bezier(.16,1,.3,1);
}
.reveal-scale {
    opacity: 0;
    transform: scale(.92);
    transition: opacity .55s cubic-bezier(.16,1,.3,1),
                transform .55s cubic-bezier(.16,1,.3,1);
}
.revealed { opacity: 1 !important; transform: none !important; }
.d1 { transition-delay: .08s }
.d2 { transition-delay: .18s }
.d3 { transition-delay: .28s }
.d4 { transition-delay: .38s }

/* counter target — starts invisible, revealed by JS */
.counter { display: inline-block; }
</style>
""", unsafe_allow_html=True)


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    preds = pd.read_parquet(PARQUET_PATH)

    centroids = pd.read_csv(CENTROID_PATH)
    centroids["CensusTract"] = (
        centroids["STATEFP"].astype(str).str.zfill(2)
        + centroids["COUNTYFP"].astype(str).str.zfill(3)
        + centroids["TRACTCE"].astype(str).str.zfill(6)
    ).astype(int)

    df = preds.merge(
        centroids[["CensusTract", "LATITUDE", "LONGITUDE"]],
        on="CensusTract",
        how="left",
    ).dropna(subset=["LATITUDE", "LONGITUDE"])

    prob = df["prediction_probability"].values.astype(float)
    r = (49  + prob * (214 - 49 )).astype(int)
    g = (160 + prob * (39  - 160)).astype(int)
    b = (208 + prob * (40  - 208)).astype(int)
    df["color"] = [[int(rv), int(gv), int(bv), 200] for rv, gv, bv in zip(r, g, b)]
    df["correct"] = (df["predicted_label"] == df["LILATracts_1And10"]).astype(int)
    return df


@st.cache_data
def holc_rates():
    crosswalk = pd.read_csv(ROOT / "data" / "raw" / "holc_tract_crosswalk.csv")
    preds = pd.read_parquet(PARQUET_PATH, columns=["CensusTract", "predicted_label"])
    merged = crosswalk.merge(preds, on="CensusTract", how="inner")
    rates = merged.groupby("holc_grade")["predicted_label"].mean().reindex(["A", "B", "C", "D"])
    return rates


def holc_bar_chart(rates: pd.Series) -> go.Figure:
    grade_colors = {"A": "#22c55e", "B": "#3b82f6", "C": "#f59e0b", "D": "#ef4444"}
    colors = [grade_colors[g] for g in rates.index]
    fig = go.Figure(go.Bar(
        x=rates.index.tolist(),
        y=(rates.values * 100).tolist(),
        marker_color=colors,
        text=[f"{v*100:.1f}%" for v in rates.values],
        textposition="outside",
        textfont=dict(color="#e6edf3", size=13, family="Inter, sans-serif"),
        width=0.55,
    ))
    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=30, b=40),
        xaxis=dict(
            title="HOLC Grade (A = Best, D = Hazardous)",
            color="#8b949e",
            tickfont=dict(size=14, color="#e6edf3"),
            gridcolor="#21262d",
        ),
        yaxis=dict(
            title="% predicted food desert",
            color="#8b949e",
            gridcolor="#21262d",
            range=[0, max(rates.values) * 130],
            ticksuffix="%",
        ),
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        showlegend=False,
        font=dict(family="Inter, sans-serif"),
        annotations=[
            dict(
                x=1.5, y=max(rates.values) * 120,
                text=f"<b>C+D tracts: {(rates['C']+rates['D'])/2*100:.1f}%</b><br>vs A+B tracts: {(rates['A']+rates['B'])/2*100:.1f}%",
                showarrow=False,
                font=dict(color="#ef4444", size=11),
                align="center",
                bgcolor="rgba(239,68,68,0.1)",
                bordercolor="#ef4444",
                borderwidth=1,
                borderpad=6,
            )
        ],
    )
    return fig


@st.cache_data
def global_shap_proxy(_df: pd.DataFrame):
    totals: dict = defaultdict(float)
    for col in ["top1_feature", "top2_feature", "top3_feature"]:
        shap_col = col.replace("feature", "shap")
        for feat, val in zip(_df[col], _df[shap_col].abs()):
            totals[feat] += float(val)
    s = pd.Series(totals).sort_values()
    s.index = [FEATURE_LABELS.get(f, f) for f in s.index]
    norm = s / s.max()
    return s, norm


# ── Helpers ───────────────────────────────────────────────────────────────────
def divider():
    st.markdown('<div class="sec-div reveal-up"></div>', unsafe_allow_html=True)


def section_label(text: str):
    st.markdown(f'<p class="sec-label reveal-up">{text}</p>', unsafe_allow_html=True)


def scroll_reveal_js():
    st.components.v1.html("""
    <script>
    (function () {
        var _seenCounters = new Set();

        function init() {
            var doc  = window.parent.document;
            var root = doc.querySelector('section.stMain');
            if (!root) { setTimeout(init, 300); return; }

            var targets  = Array.from(doc.querySelectorAll(
                '.reveal-up, .reveal-left, .reveal-right, .reveal-scale'
            ));
            if (!targets.length) { setTimeout(init, 300); return; }

            var counters = Array.from(doc.querySelectorAll('[data-count]'));

            // Check element visibility using getBoundingClientRect relative to root
            function inView(el, fraction) {
                var er = el.getBoundingClientRect();
                var rr = root.getBoundingClientRect();
                var visTop    = Math.max(er.top, rr.top);
                var visBottom = Math.min(er.bottom, rr.bottom - 40);
                var visible   = Math.max(0, visBottom - visTop);
                var height    = er.bottom - er.top || 1;
                return visible / height >= (fraction || 0.1);
            }

            function sweep() {
                targets = targets.filter(function (el) {
                    if (inView(el, 0.1)) {
                        el.classList.add('revealed');
                        return false;
                    }
                    return true;
                });
                counters = counters.filter(function (el) {
                    if (!_seenCounters.has(el) && inView(el, 0.5)) {
                        _seenCounters.add(el);
                        animateCount(el);
                        return false;
                    }
                    return !_seenCounters.has(el);
                });
            }

            sweep();
            root.addEventListener('scroll', sweep, { passive: true });
        }

        function animateCount(el) {
            var target   = parseFloat(el.dataset.count);
            var suffix   = el.dataset.suffix  || '';
            var prefix   = el.dataset.prefix  || '';
            var decimals = parseInt(el.dataset.decimals || '0', 10);
            var duration = 1400;
            var start    = performance.now();

            function tick(now) {
                var p = Math.min((now - start) / duration, 1);
                var e = 1 - Math.pow(1 - p, 3);
                var v = target * e;
                if (decimals > 0) {
                    el.textContent = prefix + v.toFixed(decimals) + suffix;
                } else if (target >= 1000) {
                    el.textContent = prefix + Math.round(v).toLocaleString() + suffix;
                } else {
                    el.textContent = prefix + Math.round(v) + suffix;
                }
                if (p < 1) requestAnimationFrame(tick);
            }
            requestAnimationFrame(tick);
        }

        setTimeout(init, 1200);
    })();
    </script>
    """, height=0)


def shap_bar(row) -> go.Figure:
    features = [
        FEATURE_LABELS.get(row["top1_feature"], row["top1_feature"]),
        FEATURE_LABELS.get(row["top2_feature"], row["top2_feature"]),
        FEATURE_LABELS.get(row["top3_feature"], row["top3_feature"]),
    ]
    values = [float(row["top1_shap"]), float(row["top2_shap"]), float(row["top3_shap"])]
    colors = ["#ef4444" if v > 0 else "#3b82f6" for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=features, orientation="h",
        marker_color=colors,
        text=[f"{v:+.3f}" for v in values],
        textposition="outside",
        textfont=dict(color="#e6edf3", size=11),
    ))
    fig.add_vline(x=0, line_width=1, line_color="#484f58")
    fig.update_layout(
        height=185, margin=dict(l=0, r=40, t=8, b=8),
        xaxis=dict(title="SHAP value", color="#8b949e", gridcolor="#21262d", zerolinecolor="#30363d"),
        yaxis=dict(autorange="reversed", color="#e6edf3", tickfont=dict(size=11)),
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        showlegend=False, font=dict(family="Inter, sans-serif"),
    )
    return fig


def global_shap_chart(s: pd.Series, norm: pd.Series) -> go.Figure:
    colors = [f"rgba(249,115,22,{0.4 + 0.6 * v})" for v in norm.values]
    fig = go.Figure(go.Bar(
        x=s.values, y=s.index, orientation="h",
        marker_color=colors,
        text=[f"{v/1000:.1f}k" for v in s.values],
        textposition="outside",
        textfont=dict(color="#8b949e", size=10),
    ))
    fig.update_layout(
        height=340, margin=dict(l=0, r=160, t=10, b=10),
        xaxis=dict(title="Cumulative |SHAP| across all tracts", color="#8b949e",
                   gridcolor="#21262d", showticklabels=False),
        yaxis=dict(color="#e6edf3", tickfont=dict(size=11)),
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        showlegend=False, font=dict(family="Inter, sans-serif"),
    )
    return fig


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    df = load_data()
    shap_s, shap_norm = global_shap_proxy(df)
    _rates_hero = holc_rates()
    _hero_ratio = (_rates_hero["C"] + _rates_hero["D"]) / (_rates_hero["A"] + _rates_hero["B"])

    # ════════════════════════════════════════════════════════════════════════
    # HERO
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class="hero">
        <p class="hero-eyebrow">AI4ALL Ignite &nbsp;·&nbsp; DesertMap &nbsp;·&nbsp; Machine Learning &amp; Fairness Audit</p>
        <h1 class="hero-headline">19 Million Americans<br>Live in Food Deserts</h1>
        <p class="hero-sub">
            We built a machine learning model to predict which neighborhoods qualify as food deserts.
            We discovered it had silently learned the geography of 1930s racial discrimination,
            without ever being shown that data.
        </p>
        <div class="hero-pills">
            <div class="hero-pill reveal-scale d1">
                <strong><span class="counter" data-count="72531" data-suffix="">0</span></strong>
                <span>census tracts analyzed</span>
            </div>
            <div class="hero-pill reveal-scale d2">
                <strong><span class="counter" data-count="16.4" data-suffix="%" data-decimals="1">0%</span></strong>
                <span>qualify as food deserts</span>
            </div>
            <div class="hero-pill hero-pill-red reveal-scale d3">
                <strong><span class="counter" data-count="{_hero_ratio:.2f}" data-suffix="×" data-decimals="2">0×</span></strong>
                <span>HOLC redlining disparity detected</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — WHAT IS A FOOD DESERT?
    # ════════════════════════════════════════════════════════════════════════
    section_label("Context")
    st.markdown("## What Is a Food Desert?")

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown("""
        <div class="card card-orange reveal-up">
            <p style="font-size:0.78rem;letter-spacing:0.15em;text-transform:uppercase;
                      color:#f97316;font-weight:700;margin:0 0 0.6rem">
                The USDA Definition
            </p>
            <p style="font-size:1rem;line-height:1.7;color:#c9d1d9;margin:0">
                A <strong style="color:#e6edf3">food desert</strong> is a census tract where residents
                have both <strong style="color:#e6edf3">low income</strong> and
                <strong style="color:#e6edf3">low access to a grocery store</strong>: the nearest
                supermarket is more than 1 mile away in an urban area, or more than 10 miles away
                in a rural area.
            </p>
        </div>
        <div style="margin-top:1rem;color:#c9d1d9;font-size:0.95rem;line-height:1.75">
            <p>
                Research links food deserts to higher rates of obesity, type 2 diabetes, and
                cardiovascular disease. They are concentrated in communities that have historically
                faced disinvestment and discrimination, not distributed at random.
            </p>
            <p>
                We trained a machine learning model to predict which tracts qualify, then audited
                it for racial bias using four independent methods.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="card reveal-scale d1" style="margin-bottom:0.75rem">
            <span style="font-size:2.4rem;font-weight:900;color:#f97316">
                <span class="counter" data-count="19" data-suffix="M">0M</span>
            </span>
            <span style="display:block;font-size:0.9rem;color:#8b949e;margin-top:0.2rem">
                Americans live in food deserts (about 1 in 17)
            </span>
        </div>
        <div class="card reveal-scale d2">
            <span style="font-size:2.4rem;font-weight:900;color:#f97316">
                <span class="counter" data-count="72531" data-suffix="">0</span>
            </span>
            <span style="display:block;font-size:0.9rem;color:#8b949e;margin-top:0.2rem">
                census tracts in this analysis, covering the entire U.S.
            </span>
        </div>
        """, unsafe_allow_html=True)

    divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — WHAT WE BUILT
    # ════════════════════════════════════════════════════════════════════════
    section_label("The Model")
    st.markdown("## What We Built")

    st.markdown("""
    <p style="font-size:1rem;color:#c9d1d9;line-height:1.75;max-width:760px;margin-bottom:1.5rem">
        We used the <strong style="color:#e6edf3">USDA Food Access Research Atlas 2019</strong>,
        a dataset covering every census tract in the United States, to train a
        <strong style="color:#e6edf3">Random Forest</strong> classifier. We then audited its
        predictions for racial bias using four independent methods.
    </p>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        st.markdown("""
        <div class="card card-blue reveal-left">
            <p style="font-size:0.78rem;letter-spacing:0.15em;text-transform:uppercase;
                      color:#3b82f6;font-weight:700;margin:0 0 0.75rem">
                The 9 Features We Used
            </p>
            <div class="chips">
                <span class="chip">Median Family Income</span>
                <span class="chip">Poverty Rate</span>
                <span class="chip">% Black Population</span>
                <span class="chip">% Hispanic Population</span>
                <span class="chip">% White Population</span>
                <span class="chip">% No Vehicle</span>
                <span class="chip">% SNAP Enrolled</span>
                <span class="chip">Population (2010)</span>
                <span class="chip">Urban / Rural</span>
            </div>
            <p style="font-size:0.85rem;color:#484f58;margin:1.25rem 0 0;line-height:1.6">
                No HOLC redlining data, no ZIP codes, no neighborhood names.
                The model sees only modern socioeconomic and demographic statistics.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class="card reveal-right d1" style="margin-bottom:0.75rem">
            <p style="font-size:0.78rem;letter-spacing:0.15em;text-transform:uppercase;
                      color:#8b949e;font-weight:700;margin:0 0 0.5rem">
                What is a Random Forest?
            </p>
            <p style="font-size:0.93rem;color:#c9d1d9;margin:0;line-height:1.65">
                A Random Forest is an ensemble of many decision trees: imagine
                200 experts each voting on "food desert or not," then taking the
                majority vote. It handles complex, non-linear patterns and is
                robust against outliers.
            </p>
        </div>
        <div class="card reveal-right d2" style="margin-bottom:0.75rem">
            <p style="font-size:0.78rem;letter-spacing:0.15em;text-transform:uppercase;
                      color:#8b949e;font-weight:700;margin:0 0 0.5rem">
                What is SHAP?
            </p>
            <p style="font-size:0.93rem;color:#c9d1d9;margin:0;line-height:1.65">
                SHAP (SHapley Additive exPlanations) assigns each feature a
                numerical score for every individual prediction, answering
                "how much did poverty rate push this tract toward 'food desert'?"
                It makes every prediction auditable, tract by tract.
            </p>
        </div>
        <div class="card reveal-right d3">
            <p style="font-size:0.78rem;letter-spacing:0.15em;text-transform:uppercase;
                      color:#8b949e;font-weight:700;margin:0 0 0.5rem">
                80/20 Train / Test Split
            </p>
            <p style="font-size:0.93rem;color:#c9d1d9;margin:0;line-height:1.65">
                58,024 tracts trained the model. The remaining 14,507 were held
                out as an unseen test set; the model never sees these during
                training, so results on them reflect real-world performance.
            </p>
        </div>
        """, unsafe_allow_html=True)

    divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — RESULTS
    # ════════════════════════════════════════════════════════════════════════
    section_label("Results")
    st.markdown("## Model Performance")

    r1, r2 = st.columns([5, 4], gap="large")

    with r1:
        st.markdown("""
        <p style="font-size:0.95rem;color:#c9d1d9;line-height:1.75;margin-bottom:1rem">
            The Random Forest outperforms a Logistic Regression baseline on all four metrics.
            <strong style="color:#e6edf3">F1 score</strong> balances precision (not crying wolf)
            and recall (not missing actual food deserts), the most important single number
            given the 5:1 class imbalance.
        </p>
        <div class="perf-table-wrap reveal-up">
        <table class="perf-table">
            <thead>
                <tr>
                    <th>Model</th>
                    <th>F1</th>
                    <th>Prec.</th>
                    <th>Recall</th>
                    <th>ROC-AUC</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Logistic Regression</td>
                    <td>0.438</td><td>0.302</td><td>0.800</td><td>0.838</td>
                </tr>
                <tr class="highlight-row">
                    <td>Random Forest &nbsp;<span class="win-badge">BEST</span></td>
                    <td>0.525</td><td>0.416</td><td>0.710</td><td>0.886</td>
                </tr>
            </tbody>
        </table>
        </div>
        """, unsafe_allow_html=True)

    with r2:
        st.markdown("""
        <p style="font-size:0.78rem;letter-spacing:0.15em;text-transform:uppercase;
                  color:#8b949e;font-weight:700;margin:0 0 0.5rem">
            What drives predictions globally?
        </p>
        <p style="font-size:0.88rem;color:#8b949e;margin:0 0 0.75rem;line-height:1.5">
            Cumulative SHAP importance across all 72,531 tracts; longer bar = stronger global driver.
        </p>
        """, unsafe_allow_html=True)
        st.plotly_chart(global_shap_chart(shap_s, shap_norm),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown("""
        <p style="font-size:0.88rem;color:#8b949e;line-height:1.55">
            <strong style="color:#e6edf3">Median family income</strong> and
            <strong style="color:#e6edf3">poverty rate</strong> dominate, but
            <strong style="color:#f97316">racial composition features appear in the top five</strong>,
            carrying independent predictive signal beyond what socioeconomic factors explain.
        </p>
        """, unsafe_allow_html=True)

    divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 4 — THE MAP
    # ════════════════════════════════════════════════════════════════════════
    section_label("Explore")
    st.markdown("## Explore All 72,531 Census Tracts")
    st.markdown("""
    <p style="font-size:0.95rem;color:#8b949e;line-height:1.65;margin-bottom:1.25rem">
        Each dot is one census tract.
        <span style="color:#31a0d0;font-weight:600">Blue</span> = low predicted probability.
        <span style="color:#d62728;font-weight:600">Red</span> = high predicted probability.
        Click any dot for the model's tract-level explanation.
    </p>
    """, unsafe_allow_html=True)

    if "map_loaded" not in st.session_state:
        st.session_state["map_loaded"] = False

    if not st.session_state["map_loaded"]:
        if st.button("Load interactive map", type="primary"):
            st.session_state["map_loaded"] = True
            st.rerun()
        st.markdown(
            "<p style='font-size:0.85rem;color:#8b949e;margin-top:0.5rem'>"
            "72,531 census tracts — loads the full dataset into your browser.</p>",
            unsafe_allow_html=True,
        )
    else:
        # Inline filters
        f1, f2, f3, f4 = st.columns([2, 2, 1, 1])
        with f1:
            view_opt = st.selectbox(
                "Show",
                ["All tracts", "Predicted food deserts", "True positives (correctly flagged)",
                 "False positives (incorrectly flagged)"],
                label_visibility="collapsed",
            )
        with f2:
            min_prob = st.slider("Min probability", 0.0, 1.0, 0.0, 0.01,
                                 label_visibility="collapsed",
                                 format="%.2f",
                                 help="Filter to tracts with prediction probability above this threshold")
        with f3:
            st.markdown(
                "<div style='padding-top:0.5rem;font-size:0.85rem;color:#8b949e'>"
                "probability threshold</div>",
                unsafe_allow_html=True,
            )
        with f4:
            st.markdown(
                f"<div style='padding-top:0.4rem;text-align:right;font-size:0.88rem;color:#8b949e'>"
                f">= <strong style='color:#f97316'>{min_prob:.2f}</strong></div>",
                unsafe_allow_html=True,
            )

        # Apply filters
        filtered = df[df["prediction_probability"] >= min_prob]
        if view_opt == "Predicted food deserts":
            filtered = filtered[filtered["predicted_label"] == 1]
        elif view_opt == "True positives (correctly flagged)":
            filtered = filtered[(filtered["predicted_label"] == 1) & (filtered["LILATracts_1And10"] == 1)]
        elif view_opt == "False positives (incorrectly flagged)":
            filtered = filtered[(filtered["predicted_label"] == 1) & (filtered["LILATracts_1And10"] == 0)]

        # Map
        tooltip = {
            "html": (
                "<div style='font-family:Inter,sans-serif;font-size:13px;'>"
                "<strong>Tract {CensusTract}</strong><br>"
                "Probability: <strong>{prediction_probability:.3f}</strong><br>"
                "Predicted: {predicted_label} &nbsp;|&nbsp; Actual: {LILATracts_1And10}<br>"
                "Top driver: <em>{top1_feature}</em>"
                "</div>"
            ),
            "style": {
                "backgroundColor": "#161b22",
                "color": "#e6edf3",
                "border": "1px solid #30363d",
                "borderRadius": "8px",
                "padding": "8px 12px",
            },
        }

        layer = pdk.Layer(
            "ScatterplotLayer",
            id="tracts",
            data=filtered,
            get_position=["LONGITUDE", "LATITUDE"],
            get_fill_color="color",
            get_radius=4000,
            radius_min_pixels=1,
            radius_max_pixels=9,
            pickable=True,
            auto_highlight=True,
        )

        view = pdk.ViewState(latitude=38.5, longitude=-96.5, zoom=3.4, pitch=0)

        event = st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                tooltip=tooltip,
                map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
            ),
            on_select="rerun",
            selection_mode="single-object",
            use_container_width=True,
            height=540,
        )

        # Tract count badge
        st.markdown(
            f"<p style='font-size:0.82rem;color:#484f58;margin-top:0.4rem'>"
            f"Showing {len(filtered):,} of {len(df):,} tracts</p>",
            unsafe_allow_html=True,
        )

        # Tract detail panel
        selected_rows = []
        if event and hasattr(event, "selection") and event.selection:
            objs = event.selection.get("objects", {})
            selected_rows = objs.get("tracts", [])

        if selected_rows:
            row = pd.Series(selected_rows[0])
            actual = int(row["LILATracts_1And10"])
            pred   = int(row["predicted_label"])
            prob   = float(row["prediction_probability"])
            correct = actual == pred

            actual_tag = (
                '<span class="tag tag-fd">Food Desert</span>' if actual == 1
                else '<span class="tag tag-ok">Not Food Desert</span>'
            )
            pred_tag = (
                '<span class="tag tag-fd">Food Desert</span>' if pred == 1
                else '<span class="tag tag-ok">Not Food Desert</span>'
            )
            outcome_tag = (
                '<span class="tag tag-right">Correct</span>' if correct
                else '<span class="tag tag-wrong">Incorrect</span>'
            )

            d1, d2 = st.columns([1, 2], gap="large")

            with d1:
                st.markdown(f"""
                <div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:1.5rem 2rem;margin-top:1.5rem">
                <div class="detail-tract-id">Census Tract {int(row['CensusTract'])}</div>
                <div class="detail-meta" style="margin-bottom:1rem">
                    Actual: {actual_tag}&nbsp; Predicted: {pred_tag}&nbsp; {outcome_tag}
                </div>
                <table style="width:100%;font-size:0.9rem;border-collapse:collapse">
                    <tr>
                        <td style="color:#8b949e;padding:0.3rem 0">Prediction probability</td>
                        <td style="color:#f97316;font-weight:700;text-align:right">{prob:.4f}</td>
                    </tr>
                    <tr>
                        <td style="color:#8b949e;padding:0.3rem 0">% Black population</td>
                        <td style="color:#e6edf3;text-align:right">{float(row['pct_nhblack10']):.1f}%</td>
                    </tr>
                    <tr>
                        <td style="color:#8b949e;padding:0.3rem 0">% Hispanic population</td>
                        <td style="color:#e6edf3;text-align:right">{float(row['pct_hisp10']):.1f}%</td>
                    </tr>
                    <tr>
                        <td style="color:#8b949e;padding:0.3rem 0">% White population</td>
                        <td style="color:#e6edf3;text-align:right">{float(row['pct_nhwhite10']):.1f}%</td>
                    </tr>
                </table>
                </div>
                """, unsafe_allow_html=True)

            with d2:
                st.markdown("""
                <div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:1.5rem 2rem;margin-top:1.5rem">
                <p style="font-size:0.78rem;letter-spacing:0.15em;text-transform:uppercase;
                          color:#8b949e;font-weight:700;margin:0 0 0.3rem">
                    Why did the model predict this?
                </p>
                <p style="font-size:0.88rem;color:#8b949e;margin:0 0 0.5rem;line-height:1.5">
                    <span style="color:#ef4444">Red bars</span> push toward "food desert."
                    <span style="color:#3b82f6">Blue bars</span> push away from it.
                    Longer = stronger influence.
                </p>
                </div>
                """, unsafe_allow_html=True)
                st.plotly_chart(shap_bar(row), use_container_width=True,
                                config={"displayModeBar": False})

        else:
            st.markdown("""
            <p style="font-size:0.88rem;color:#8b949e;margin-top:0.5rem;text-align:center">
                Click any dot on the map to see the model's tract-level explanation.
            </p>
            """, unsafe_allow_html=True)

    divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 5 — THE HOLC FINDING
    # ════════════════════════════════════════════════════════════════════════
    section_label("The Finding")
    st.markdown("## The Model Remembered Something It Was Never Shown")

    st.markdown("""
    <div class="pull-quote reveal-left">
        "AI trained on present data inherits past policy. Responsible development detects this.
        Deployment without auditing does not."
    </div>
    <p style="font-size:1rem;color:#c9d1d9;line-height:1.8;max-width:800px;margin-bottom:2rem">
        Between 1935 and 1940, the federal Home Owners' Loan Corporation (HOLC) graded neighborhoods
        in over 200 U.S. cities. <strong style="color:#e6edf3">Grade A ("Best")</strong> went to
        predominantly white, affluent areas. <strong style="color:#ef4444">Grade D ("Hazardous")</strong>
        was assigned almost exclusively to Black and immigrant communities, blocking them from mortgage
        lending and investment for decades.
        <br><br>
        These grades shaped where grocery stores opened, where roads were built, and which communities
        received public investment. Our model was trained on <em>modern</em> data and never saw a single
        HOLC grade. When we overlaid its predictions on the 1930s maps, a stark pattern emerged.
    </p>
    """, unsafe_allow_html=True)

    # 4 bias metric cards — compute HOLC ratio live from data
    rates = holc_rates()
    cd_rate = (rates["C"] + rates["D"]) / 2 * 100
    ab_rate = (rates["A"] + rates["B"]) / 2 * 100
    holc_ratio = cd_rate / ab_rate

    b1, b2, b3, b4 = st.columns(4, gap="medium")
    cards = [
        (f"{holc_ratio:.2f}", "bcard-orange", "HOLC Redlining Disparity",
         f"C- or D-graded tracts are {holc_ratio:.2f}x more likely to be predicted food deserts "
         f"than A- or B-graded tracts ({cd_rate:.1f}% vs. {ab_rate:.1f}%).",
         "d1", f"{holc_ratio:.2f}", "x", "2"),
        ("5.9", "bcard-red", "Misclassification Is Unequal",
         "The model incorrectly flags high-Black-population tracts as food deserts at 5.9x "
         "the rate of low-Black-population tracts. (False positive rate disparity.)",
         "d2", "5.9", "x", "1"),
        ("33.6", "bcard-red", "When Race Changes, Predictions Change",
         "When racial composition features are reset to the national median, holding all else "
         "constant, 33.6% of food desert predictions flip to not a food desert. "
         "(Counterfactual probe.)",
         "d3", "33.6", "%", "1"),
        ("-2.2", "bcard-orange", "Race Carries Independent Signal",
         "Removing % Black and % Hispanic cuts F1 by 2.2 points, confirming racial features "
         "carry predictive signal beyond income and poverty rate. (F1 ablation.)",
         "d4", "2.2", " pts", "1"),
    ]
    for col, (num, num_cls, title, desc, delay, count_val, suffix, decimals) in zip([b1, b2, b3, b4], cards):
        with col:
            prefix = "-" if num.startswith("-") else ""
            st.markdown(f"""
            <div class="bcard reveal-up {delay}">
                <span class="bcard-title">{title}</span>
                <span class="bcard-num {num_cls}">
                    <span class="counter" data-count="{count_val}" data-suffix="{suffix}"
                          data-prefix="{prefix}" data-decimals="{decimals}">
                        {prefix}0{suffix}
                    </span>
                </span>
                <span class="bcard-desc">{desc}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    rates = holc_rates()
    st.plotly_chart(holc_bar_chart(rates), use_container_width=True,
                    config={"displayModeBar": False})

    divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 6 — WHY IT MATTERS
    # ════════════════════════════════════════════════════════════════════════
    section_label("Impact")
    st.markdown("## What Auditing Changes")

    st.markdown("""
    <p style="font-size:1rem;color:#c9d1d9;line-height:1.8;max-width:800px;margin-bottom:1.5rem">
        A model with F1 of 0.525 looks adequate in aggregate. The bias audit reveals what that
        number conceals: errors are not distributed at random. Communities that most need accurate
        identification are disproportionately misclassified.
    </p>
    """, unsafe_allow_html=True)

    w1, w2 = st.columns(2, gap="large")
    with w1:
        st.markdown("""
        <div class="card card-red reveal-left">
            <p style="font-size:0.78rem;letter-spacing:0.15em;text-transform:uppercase;
                      color:#ef4444;font-weight:700;margin:0 0 0.75rem">
                Without Auditing
            </p>
            <ul style="font-size:0.93rem;color:#c9d1d9;line-height:1.8;padding-left:1.2rem;margin:0">
                <li>5.9x FPR disparity is invisible to the deployer</li>
                <li>HOLC pattern goes undetected</li>
                <li>Racial composition drives predictions silently</li>
                <li>Deployment operationalizes historical discrimination</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with w2:
        st.markdown("""
        <div class="card card-green reveal-right">
            <p style="font-size:0.78rem;letter-spacing:0.15em;text-transform:uppercase;
                      color:#22c55e;font-weight:700;margin:0 0 0.75rem">
                With Auditing
            </p>
            <ul style="font-size:0.93rem;color:#c9d1d9;line-height:1.8;padding-left:1.2rem;margin:0">
                <li>5.9x FPR disparity surfaced and documented</li>
                <li>HOLC odds ratio of 1.57x measured and reported</li>
                <li>SHAP makes every prediction auditable, tract by tract</li>
                <li>Mitigations identified: equalized-odds calibration, adversarial debiasing</li>
                <li>Model becomes evidence of the problem, not an accelerant of it</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Methodology details"):
        st.markdown("""
        **Data source:** USDA Food Access Research Atlas 2019 (72,531 census tracts, national scope)

        **Target variable:** `LILATracts_1And10`: the federally recognized food desert definition
        (low income AND low access at the 1-mile urban / 10-mile rural threshold)

        **Train/test split:** 80% training (58,024 tracts), 20% holdout (14,507 tracts),
        stratified by target variable, random seed 42

        **Model:** Random Forest: 200 trees, max depth 20, class-balanced weighting to address 5:1 imbalance

        **SHAP:** TreeExplainer applied to a 2,000-tract representative subsample of the test set;
        `check_additivity=False` for computational efficiency; results are statistically representative

        **HOLC crosswalk:** Mapping Inequality v3 (Nelson et al., 2023), spatial join to 2010 census
        tract boundaries, used exclusively as a post-prediction grouping variable, not a training feature

        **Fairness audit methods:** (1) race-removed model delta, (2) quartile false positive rate analysis,
        (3) counterfactual racial composition probe, (4) HOLC post-prediction overlay
        """)

    with st.expander("Limitations & interpretation"):
        st.markdown("""
        **The confounding variable challenge**

        A reasonable objection: redlined areas became low-income areas, and low-income areas have poor
        food access. The overlap with HOLC maps might reflect income concentration rather than race.

        The counterfactual test addresses this directly. Racial composition features were reset to the
        national median while holding income, poverty rate, and all other features constant for every
        tract in the test set. **33.6% of predictions changed.** If the pattern were purely income
        geography, removing race should not move individual predictions.

        The causal chain argument does not escape the objection either. Saying "it is just income
        geography" requires explaining why that income geography aligns with 90-year-old federal grading
        maps — which is the redlining story, not an alternative to it.

        **What this study can and cannot claim**

        This is observational work. Causation is not established. The finding is that (1) the pattern
        exists across four independent tests, (2) racial composition carries independent predictive
        signal beyond income and poverty, and (3) that is sufficient reason to audit before any
        deployment affecting food access decisions. Responsible deployment does not require resolving
        the causation question. It requires disclosing the disparity.
        """)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="footer reveal-up">
        DesertMap &nbsp;·&nbsp; AI4ALL Ignite Accelerator &nbsp;·&nbsp; 2026 &nbsp;·&nbsp;
        <a href="https://github.com/Morgan971-pixel/desertmap" target="_blank">GitHub</a>
        &nbsp;·&nbsp;
        Data: USDA Economic Research Service 2019 &nbsp;·&nbsp;
        HOLC crosswalk: Mapping Inequality v3 (Nelson et al., 2023)
    </div>
    """, unsafe_allow_html=True)

    if "js_injected" not in st.session_state:
        st.session_state["js_injected"] = True
        scroll_reveal_js()


if __name__ == "__main__":
    main()
