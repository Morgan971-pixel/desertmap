# Slide Deck Outline — DesertMap Midpoint Proposal
# 7 slides, 10-minute presentation format

---

## Slide 1 — Title
**Title:** DesertMap: Predicting Food Desert Status and Auditing for Redlining-Era Bias
**Subtitle:** AI4ALL Ignite — Week 7 Midpoint Proposal
**Visual:** Choropleth map of the United States shaded by food desert prediction rate, warm-to-cool gradient

---

## Slide 2 — The Problem
**Heading:** 19 Million Americans Live in Food Deserts

**Three-column layout:**
- Column 1: "16.4% of U.S. census tracts qualify as food deserts under USDA's federal standard"
- Column 2: "Food access disparities correlate strongly with race, income, and historical redlining"
- Column 3: "Policy interventions require knowing WHERE — and knowing whether existing tools are fair"

**Visual:** Side-by-side bar chart — food desert rate by income quartile vs. by racial composition quartile (use actual EDA figures from 01_demographic_quartile_preview.png)

---

## Slide 3 — Research Question
**Heading:** Two Questions in One

**Large centered text (split):**
"Can we predict which census tracts are food deserts from modern socioeconomic data?"
+
"Does the model reproduce 1930s HOLC redlining grades it was never shown?"

**Sub-text:** Target variable: LILATracts_1And10 | 72,531 U.S. census tracts | 9 features | No HOLC in training

**Visual:** Diagram showing two-phase methodology — left box (Train on modern data) → right box (Audit against HOLC grades) with an arrow labeled "no HOLC grades cross this line"

---

## Slide 4 — Dataset and Methodology
**Heading:** USDA Food Access Research Atlas 2019

**Left panel — Dataset facts:**
- 72,531 census tracts, national scope
- 9 features: income, poverty, race, vehicle access, SNAP, population, urban/rural
- 80/20 stratified train/test split
- Class imbalance: 16.4% food desert — addressed with balanced class weights

**Right panel — Models:**
- Baseline: Logistic Regression
- Primary: Random Forest with 3-fold grid search
- Explainability: SHAP TreeExplainer for all 72k tracts
- Fairness: 4-method audit (race-removed, quartile, counterfactual, HOLC overlay)

---

## Slide 5 — Preliminary Results
**Heading:** Random Forest Outperforms Baseline on All Metrics

**Table (large, center-aligned):**
| Model | F1 | Precision | Recall | ROC-AUC |
|-------|----|-----------|--------|---------|
| Logistic Regression | 0.438 | 0.302 | 0.800 | 0.838 |
| Random Forest | 0.525 | 0.416 | 0.710 | 0.886 |

**Bottom callout box:**
"Median family income and poverty rate are the top global predictors — but racial composition appears in the top 5 features nationally"

**Visual:** SHAP bar chart (04_shap_bar.png)

---

## Slide 6 — Fairness Audit Findings
**Heading:** The Model Reproduces a Geography It Was Never Shown

**Four finding cards (2x2 grid):**

Card 1 — Race-removed model:
"Removing % Black and % Hispanic reduces F1 by 2.2 points — racial features carry signal not encoded by income alone"

Card 2 — Quartile analysis:
"False positive rate: 2.3% in lowest-Black quartile → 13.4% in highest-Black quartile (5.9x disparity)"

Card 3 — Counterfactual probe:
"33.6% of food desert predictions flip when racial features are set to the national median — holding all other features constant"

Card 4 — HOLC audit:
"Tracts graded D in the 1930s are 1.57x more likely to be predicted food deserts today than A-graded tracts (27.4% vs. 10.8%)"

**Visual:** HOLC bar chart (05_holc_audit.png) — full width below the cards

---

## Slide 7 — Answering the Essential Question
**Heading:** Responsible Development Makes the Difference Visible

**Essential Question (quoted at top):**
"How can the development processes of responsible AI/ML solutions address and mitigate the technology's negative impacts while strengthening its positive effects?"

**Two-column answer:**

Left — Without responsible development:
- Aggregate F1 of 0.525 looks adequate
- Racial bias in false positive rate is invisible
- HOLC reproduction goes undetected
- Model deployed = historical discrimination operationalized

Right — With responsible development:
- 5.9x FPR disparity surfaced and documented
- HOLC odds ratio of 1.57x measured and reported
- Mitigation strategies: equalized odds threshold calibration, adversarial debiasing
- Model becomes evidence — not an accelerant — of the problem

**Bottom line (large text):**
"AI trained on present data inherits past policy. Responsible development detects this. Deployment without auditing does not."
