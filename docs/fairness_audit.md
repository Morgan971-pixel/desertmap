# Fairness Audit: DesertMap

**Model audited:** Random Forest food desert classifier  
**Target variable:** `LILATracts_1And10` (USDA 1-mile urban / 10-mile rural threshold)  
**Audit date:** Week 6 analysis, conducted on test set (20% holdout, N = 14,507 census tracts)  
**Audit notebook:** `notebooks/05_fairness_audit.ipynb`

---

## Methodology

The audit applies four complementary techniques to evaluate whether the model's predictions reproduce or amplify racial and historical disparities in food access. All four use the same fitted model, so they probe one set of predictions from several angles.

1. **Race-removed model comparison**: retrain with all three race shares (percentage Black, Hispanic and White) excluded; measure performance delta
2. **Quartile analysis**: stratify the test set by percentage Black (and separately by percentage Hispanic) into quartiles; compute precision, recall, and false positive rate per quartile
3. **Counterfactual probe**: for tracts predicted food desert, perturb racial composition features to their median across held-out tracts and measure prediction change
4. **HOLC post-prediction audit**: join model predictions to the Mapping Inequality HOLC crosswalk; compare food desert prediction rates across historical redlining grades A through D

**Critical design note:** HOLC grade was not included as a training feature at any stage. The audit uses HOLC grade exclusively as a post-prediction grouping variable. Any observed correlation between HOLC grade and predicted food desert status reflects patterns the model learned from modern socioeconomic data alone.

---

## 1. Race-Removed Model Comparison

| Metric | Full Model | Race-Removed | Delta |
|--------|-----------|--------------|-------|
| F1 (food desert class) | 0.533 | 0.486 | -0.047 |
| Precision | 0.446 | 0.374 | -0.073 |
| Recall | 0.661 | 0.695 | +0.034 |
| ROC-AUC | 0.885 | 0.861 | -0.024 |

All three race shares are removed together because the three race shares sum to nearly 100%, so any one left in reveals the others. Removing them reduces F1 by 4.7 percentage points and ROC-AUC by 2.4 percentage points (removing only percentage Black and Hispanic costs 3.8 F1 points). The precision drop (-7.3 pp) is larger than the recall change (+3.4 pp): without racial composition features the model flags more tracts as food deserts, and a larger share of those flags are wrong. Racial composition features carry signal that median family income, poverty rate, vehicle access, and SNAP enrollment do not fully replace.

---

## 2. Quartile Analysis: Percentage Black Population

Tracts in the test set were divided into quartiles by percentage Black population using rank-based assignment.

| Quartile | N tracts | Precision | Recall | F1 | False Positive Rate |
|----------|----------|-----------|--------|----|---------------------|
| Q1 (lowest) | 3,627 | 0.514 | 0.606 | 0.556 | 6.9% |
| Q2 | 3,627 | 0.420 | 0.627 | 0.503 | 7.6% |
| Q3 | 3,626 | 0.404 | 0.638 | 0.495 | 11.6% |
| Q4 (highest) | 3,627 | 0.452 | 0.713 | 0.553 | 23.8% |

**Primary finding:** The false positive rate rises at every step from Q1 to Q4, from 6.9% to 23.8%, a 3.47x disparity. In tracts where Black residents make up the highest share of the population, the model is about three and a half times more likely to falsely predict food desert status than in tracts where they make up the lowest share. Recall also rises across quartiles (0.606 to 0.713), so the model flags more tracts in high-Black-population areas and a larger share of those flags are false alarms. The gap points to associations between racial composition and food insecurity that the model learned beyond the ground truth signal in this demographic dimension.

---

## 3. Quartile Analysis: Percentage Hispanic Population

| Quartile | N tracts | Precision | Recall | F1 | False Positive Rate |
|----------|----------|-----------|--------|----|---------------------|
| Q1 (lowest) | 3,627 | 0.456 | 0.636 | 0.531 | 11.6% |
| Q2 | 3,627 | 0.485 | 0.746 | 0.588 | 11.1% |
| Q3 | 3,626 | 0.423 | 0.730 | 0.536 | 12.6% |
| Q4 (highest) | 3,627 | 0.421 | 0.558 | 0.480 | 13.0% |

The Hispanic quartile pattern is much flatter than the Black quartile pattern. The false positive rate stays between 11.1% and 13.0% across all four quartiles. Recall is lowest in the highest-Hispanic quartile (55.8%), so the model misses more actual food deserts there than in the other quartiles. High-Hispanic tracts span dense urban areas, where food access may be adequate, and rural agricultural communities, where it may not, which may explain the mixed signal.

---

## 4. Counterfactual Probe

Starting from the 2,755 held-out tracts predicted as food deserts, all three race shares (percentage Black, Hispanic and White) were replaced with their median values across held-out tracts while all other features (income, poverty, vehicle access, SNAP, population, urban status) remained unchanged.

| | Count | Rate |
|-|-------|------|
| Food desert predictions | 2,755 | n/a |
| Predictions that flip to non-food-desert | 452 | 16.4% |

Holding all socioeconomic and geographic characteristics constant, changing racial composition alone reverses about one in six food desert predictions. An earlier version reset only percentage Black and Hispanic and flipped 22.0% (605), but it left 29% of flagged tracts with race shares summing below 60%, so part of that effect came from impossible inputs. Resetting all three keeps each tract's makeup consistent.

---

## 5. HOLC Post-Prediction Audit

Predictions from the full national dataset (N = 72,531 tracts) were joined to the Mapping Inequality v3 HOLC crosswalk (2010 census tract boundaries). The crosswalk covers 16,421 tracts across historically HOLC-graded cities; rural areas and cities not surveyed by HOLC are excluded from this analysis.

| HOLC Grade | N tracts | Predicted food desert rate | Actual food desert rate |
|------------|----------|---------------------------|------------------------|
| A (Best) | 1,171 | 8.8% | 3.8% |
| B (Still Desirable) | 3,341 | 14.9% | 6.9% |
| C (Declining) | 7,361 | 19.4% | 9.4% |
| D (Hazardous) | 4,548 | 21.8% | 13.7% |

**C+D prediction rate:** 20.3%  
**A+B prediction rate:** 13.3%  
**Rate ratio (C+D vs A+B):** 1.53x

The predicted food desert rate increases at every step from A to D. Tracts designated "Hazardous" by HOLC appraisers in the 1930s are 3.6x more likely to be actual food deserts today (13.7% vs 3.8% for grade A) and 2.5x more likely to be predicted food deserts by the model (21.8% vs 8.8%).

About 80% of the crosswalk tracts were training tracts, so the 1.53x ratio mixes in-sample and held-out predictions. On the 3,290 held-out crosswalk tracts alone, the predicted rate is 21.2% for C+D and 16.4% for A+B, a ratio of 1.30x. The true labels show a larger gap than either predicted ratio: 11.1% for C+D against 6.1% for A+B, a ratio of 1.82x. The model follows a real gap in food access and predicts it somewhat flatter than the data shows.

HOLC grade was excluded from all training runs. The model learned from median family income, poverty rate, racial composition, vehicle access, SNAP enrollment, population, and urban classification. The spatial reproduction of HOLC boundaries in the model's output indicates that contemporary socioeconomic conditions and demographic composition in formerly redlined neighborhoods are structurally distinct from those in formerly preferred neighborhoods, and that a model trained on those modern conditions will reproduce the 1930s geographic order as an output.

---

## Interpretation

The four audit methods point the same way: the model's predictions skew by race. It produces more false positives in tracts with high Black population (3.47x higher false positive rate in Q4 vs Q1), shows racial composition dependency in about one in six positive predictions (16.4%), and spatially reproduces historical HOLC redlining grades it was never shown (1.53x predicted rate ratio, 1.30x on held-out tracts, against 1.82x in the true labels). All four checks use the same model.

The model performs well at its stated task (ROC-AUC 0.885). The disparity shows that food insecurity in the United States is itself geographically patterned by historical policy, and a classifier trained on modern socioeconomic conditions will inherit that pattern. The audit finding is both a methodological concern (the model may be less accurate for protected demographic groups) and a substantive finding (present food access conditions spatially reproduce past discriminatory policy).

**Proposed mitigations:**
1. Collect and incorporate store-level data (distance to nearest supermarket) to provide a direct access signal less confounded by racial composition
2. Apply post-processing calibration (equalized odds or threshold adjustment) to reduce FPR disparity across Black population quartiles before any deployment
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
