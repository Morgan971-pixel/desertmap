# Fairness Audit — DesertMap

**Model audited:** Random Forest food desert classifier  
**Target variable:** `LILATracts_1And10` (USDA 1-mile urban / 10-mile rural threshold)  
**Audit date:** Week 6 analysis, conducted on test set (20% holdout, N = 14,507 census tracts)  
**Audit notebook:** `notebooks/05_fairness_audit.ipynb`

---

## Methodology

The audit applies four complementary techniques to evaluate whether the model's predictions reproduce or amplify racial and historical disparities in food access:

1. **Race-removed model comparison** — retrain with percentage Black and Hispanic features excluded; measure performance delta
2. **Quartile analysis** — stratify the test set by percentage Black (and separately by percentage Hispanic) into quartiles; compute precision, recall, and false positive rate per quartile
3. **Counterfactual probe** — for tracts predicted food desert, perturb racial composition features to national median values and measure prediction change
4. **HOLC post-prediction audit** — join model predictions to the Mapping Inequality HOLC crosswalk; compare food desert prediction rates across historical redlining grades A through D

**Critical design note:** HOLC grade was not included as a training feature at any stage. The audit uses HOLC grade exclusively as a post-prediction grouping variable. Any observed correlation between HOLC grade and predicted food desert status reflects patterns the model learned from modern socioeconomic data alone.

---

## 1. Race-Removed Model Comparison

| Metric | Full Model | Race-Removed | Delta |
|--------|-----------|--------------|-------|
| F1 (food desert class) | 0.489 | 0.467 | -0.022 |
| Precision | 0.523 | 0.455 | -0.068 |
| Recall | 0.459 | 0.480 | +0.021 |
| ROC-AUC | 0.883 | 0.867 | -0.016 |

Removing percentage Black and percentage Hispanic from the feature set reduces F1 by 2.2 percentage points and ROC-AUC by 1.6 percentage points. The precision drop (-6.8 pp) is notably larger than the recall change, indicating that without racial composition features, the model generates more false positive food desert predictions — yet still cannot recover the overall discriminative power of the full model. Racial composition features carry signal not fully substituted by median family income, poverty rate, vehicle access, or SNAP enrollment.

---

## 2. Quartile Analysis — Percentage Black Population

Tracts in the test set were divided into quartiles by percentage Black population using rank-based assignment.

| Quartile | N tracts | Precision | Recall | F1 | False Positive Rate |
|----------|----------|-----------|--------|----|---------------------|
| Q1 (lowest) | 3,627 | 0.674 | 0.394 | 0.498 | 2.3% |
| Q2 | 3,627 | 0.481 | 0.394 | 0.433 | 3.7% |
| Q3 | 3,626 | 0.476 | 0.455 | 0.465 | 6.2% |
| Q4 (highest) | 3,627 | 0.515 | 0.519 | 0.517 | 13.4% |

**Primary finding:** The false positive rate increases monotonically from Q1 to Q4, rising from 2.3% to 13.4% — a 5.9x disparity. In tracts where Black residents constitute the highest share of the population, the model is nearly six times more likely to falsely predict food desert status than in tracts where Black residents constitute the lowest share. This disparity is not explained by actual food access conditions; it indicates the model has learned associations between racial composition and food insecurity that exceed the ground truth signal present in this demographic dimension.

---

## 3. Quartile Analysis — Percentage Hispanic Population

| Quartile | N tracts | Precision | Recall | F1 | False Positive Rate |
|----------|----------|-----------|--------|----|---------------------|
| Q1 (lowest) | 3,627 | 0.538 | 0.426 | 0.476 | 5.6% |
| Q2 | 3,627 | 0.558 | 0.580 | 0.569 | 6.4% |
| Q3 | 3,626 | 0.464 | 0.547 | 0.502 | 8.0% |
| Q4 (highest) | 3,627 | 0.544 | 0.320 | 0.403 | 4.6% |

The Hispanic quartile pattern differs from the Black quartile pattern. Q3 shows the highest false positive rate (8.0%) rather than Q4. The highest-Hispanic quartile shows relatively lower FPR (4.6%) alongside the lowest recall (32.0%), suggesting the model undershoots actual food desert status in predominantly Hispanic tracts rather than overshooting it. This bimodal pattern may reflect geographic heterogeneity: high-Hispanic tracts span both dense urban areas (where food access may be adequate) and rural agricultural communities (where it may not), creating a mixed signal that the model resolves inconsistently.

---

## 4. Counterfactual Probe

Starting from the 1,633 test-set tracts predicted as food deserts, percentage Black and percentage Hispanic were replaced with their national test-set median values while all other features (income, poverty, vehicle access, SNAP, population, urban status) remained unchanged.

| | Count | Rate |
|-|-------|------|
| Food desert predictions | 1,633 | — |
| Predictions that flip to non-food-desert | 549 | 33.6% |

Holding all socioeconomic and geographic characteristics constant, racial composition alone reverses one-in-three food desert predictions. This is direct evidence that the model's positive predictions are not fully explainable by socioeconomic conditions alone — racial composition operates as an independent driver of classification even when income, poverty, and access features are held fixed.

---

## 5. HOLC Post-Prediction Audit

Predictions from the full national dataset (N = 72,531 tracts) were joined to the Mapping Inequality v3 HOLC crosswalk (2010 census tract boundaries). The crosswalk covers 16,421 tracts across historically HOLC-graded cities; rural areas and cities not surveyed by HOLC are excluded from this analysis.

| HOLC Grade | N tracts | Predicted food desert rate | Actual food desert rate |
|------------|----------|---------------------------|------------------------|
| A (Best) | 1,171 | 10.8% | 3.8% |
| B (Still Desirable) | 3,341 | 18.0% | 6.9% |
| C (Declining) | 7,361 | 24.2% | 9.4% |
| D (Hazardous) | 4,548 | 27.4% | 13.7% |

**C+D prediction rate:** 25.4%  
**A+B prediction rate:** 16.2%  
**Odds ratio (C+D vs A+B):** 1.57x

The predicted food desert rate increases monotonically from A to D. Tracts designated "Hazardous" by HOLC appraisers in the 1930s are 2.5x more likely to be actual food deserts today (13.7% vs 3.8% for grade A) and 1.57x more likely to be predicted food deserts by the model.

This pattern is not attributable to the model receiving HOLC information — HOLC grade was excluded from all training runs. The model learned from median family income, poverty rate, racial composition, vehicle access, SNAP enrollment, population, and urban classification. The spatial reproduction of HOLC boundaries in the model's output indicates that contemporary socioeconomic conditions and demographic composition in formerly redlined neighborhoods are structurally distinct from those in formerly preferred neighborhoods — and that a model trained on those modern conditions will reproduce the 1930s geographic order as an output.

---

## Interpretation

The four audit methods converge on a consistent finding: the model's predictions are not demographically neutral. It disproportionately predicts food desert status in tracts with high Black population (5.9x higher false positive rate in Q4 vs Q1), shows direct racial composition dependency in one-in-three positive predictions, and spatially reproduces historical HOLC redlining grades it was never shown.

This does not indicate the model is a poor model for its stated task — ROC-AUC of 0.883 reflects substantial discriminative ability. It indicates that food insecurity in the United States is itself geographically patterned by historical policy, and a classifier trained on modern socioeconomic conditions will inherit that pattern. The audit finding is therefore both a methodological concern (the model may be less accurate for protected demographic groups) and a substantive finding (present food access conditions spatially reproduce past discriminatory policy).

**Proposed mitigations:**
1. Collect and incorporate store-level data (distance to nearest supermarket) to provide a direct access signal less confounded by racial composition
2. Apply post-processing calibration — equalized odds or threshold adjustment — to reduce FPR disparity across Black population quartiles before any deployment
3. Report model predictions alongside prediction uncertainty intervals; do not use point predictions as sole basis for policy targeting
4. Conduct ongoing monitoring of false positive rates by racial composition quartile as any deployed model receives feedback data

---

## Files

| File | Description |
|------|-------------|
| `notebooks/05_fairness_audit.ipynb` | Full audit code and outputs |
| `outputs/fairness_metrics.json` | Key metrics in machine-readable format |
| `outputs/figures/05_quartile_black.png` | FPR/precision/recall by Black population quartile |
| `outputs/figures/05_quartile_hispanic.png` | FPR/precision/recall by Hispanic population quartile |
| `outputs/figures/05_holc_audit.png` | Predicted food desert rate by HOLC grade |
| `data/raw/holc_tract_crosswalk.csv` | HOLC-to-census-tract crosswalk (Mapping Inequality v3, 2010 tracts) |
