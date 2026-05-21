# Project Proposal — DesertMap: Predicting Food Desert Status and Auditing for Redlining-Era Bias

**Program:** AI4ALL Ignite Accelerator — Semester 1  
**Week 7 Midpoint Proposal**

---

## Research Question

Do census tract-level socioeconomic and demographic features — including median family income, poverty rate, vehicle access, SNAP enrollment, and racial composition — predict USDA-defined food desert status with sufficient accuracy to support policy targeting, and does a classifier trained exclusively on contemporary data reproduce the spatial pattern of 1930s HOLC redlining grades among the tracts it flags as food deserts?

This question is analytical rather than descriptive: it asks not only whether prediction is possible, but whether the model's errors and positive predictions are distributed equitably across demographic groups, and whether the patterns the model learns from modern data independently reconstruct a geography of discrimination that precedes it by ninety years.

**Target population:** All 72,531 U.S. census tracts in the USDA Food Access Research Atlas 2019 dataset, with a fairness audit sub-population restricted to the 16,421 tracts that overlap with historically HOLC-graded neighborhoods.

---

## Background

Food deserts — areas where residents lack physical or economic access to affordable, nutritious food — affect an estimated 19 million Americans and are disproportionately concentrated in low-income communities of color (Ver Ploeg et al., 2015). Research consistently links food access to long-term health outcomes including obesity, type 2 diabetes, and cardiovascular disease (Walker et al., 2010). The spatial distribution of food deserts is not random: it reflects decades of disinvestment, exclusionary zoning, and discriminatory mortgage lending policy. Between 1935 and 1940, the Home Owners' Loan Corporation (HOLC) graded neighborhoods in over 200 U.S. cities from A ("Best") to D ("Hazardous"), with D grades assigned predominantly to Black and immigrant communities. These maps shaped where banks lent, where grocery chains opened, and where infrastructure was built — effects that persist in the present built environment (Nardone et al., 2021; Aaronson et al., 2021).

This project uses machine learning to quantify that persistence: a Random Forest classifier is trained on modern socioeconomic and demographic data to predict which census tracts meet the federal food desert definition, and the predictions are then spatially joined to HOLC grades to measure how strongly current predictions align with historical discrimination — without the model ever having seen the HOLC data.

---

## Dataset

**Primary dataset:** USDA Food Access Research Atlas 2019 (Economic Research Service)
- 72,531 U.S. census tracts covering the entire contiguous United States
- 147 variables including income, poverty, vehicle access, SNAP participation, store proximity, and demographic composition
- Target variable: `LILATracts_1And10` — the federally recognized food desert definition (low income AND low access at the 1-mile urban / 10-mile rural threshold)
- Class distribution: 16.4% positive (food desert), 83.6% negative

**HOLC crosswalk:** Mapping Inequality v3 (Nelson et al., 2023), spatial join to 2010 census tract boundaries
- 16,421 tracts with HOLC grades A through D across historically surveyed cities
- Used exclusively as a post-prediction grouping variable — not a training feature

**Train/test split:** 80% training (58,024 tracts), 20% holdout (14,507 tracts), stratified by target variable, random seed 42.

The dataset is large enough to support robust train/test evaluation, cross-validation, and demographic subgroup analysis across all four racial composition quartiles with statistically meaningful group sizes (N ≥ 3,626 per quartile in the test set).

---

## Methodology

**Feature engineering:** Raw demographic counts (TractBlack, TractHispanic, etc.) are converted to per-tract percentages immediately after data loading, with guards for zero-denominator tracts. Nine features are used for training: median family income, poverty rate, percentage Black, percentage Hispanic, percentage White, percentage households without vehicles, percentage SNAP-enrolled households, tract population, and urban/rural classification.

**Models:** A logistic regression baseline establishes a performance floor. A Random Forest classifier with grid search over tree depth (10, 20, None) and estimator count (100, 200) is optimized using 3-fold stratified cross-validation with F1 on the food desert class as the scoring metric. Both models use class-balanced weighting to address the 5:1 class imbalance.

**Fairness audit (four-method approach):**
1. Race-removed model: retrain without percentage Black and Hispanic; compare F1 and ROC-AUC delta
2. Quartile analysis: stratify the test set into quartiles by percentage Black (and separately by percentage Hispanic); compute false positive rate per quartile
3. Counterfactual probe: for tracts predicted food desert, replace racial composition features with national median values and measure prediction flip rate
4. HOLC post-prediction audit: join predictions to the Mapping Inequality crosswalk; compare food desert prediction rate by historical HOLC grade

---

## Preliminary Results

| Model | F1 (food desert class) | Precision | Recall | ROC-AUC |
|-------|----------------------|-----------|--------|---------|
| Logistic Regression (baseline) | 0.438 | 0.302 | 0.800 | 0.838 |
| Random Forest | 0.525 | 0.416 | 0.710 | 0.886 |

The Random Forest improves F1 by 8.7 percentage points and ROC-AUC by 4.8 points over the baseline. Pre-computed SHAP values identify median family income and poverty rate as the dominant global predictors, with racial composition features appearing in the top five across the national test set.

**Fairness audit findings (preliminary):**
- Removing percentage Black and percentage Hispanic reduces F1 by 2.2 points and ROC-AUC by 1.6 points, confirming that racial features carry independent predictive signal beyond socioeconomic proxies
- The false positive rate rises from 2.3% in the lowest-Black-population quartile to 13.4% in the highest — a 5.9x disparity
- 33.6% of food desert predictions flip to non-food-desert when racial composition is replaced with national median values, holding all socioeconomic features constant
- Tracts historically graded C or D by HOLC are 1.57x more likely to be predicted food deserts today (25.4%) than tracts graded A or B (16.2%), with a monotonic gradient from A (10.8%) to D (27.4%)

---

## Bias Identification and Mitigation

**Bias source 1 — Racial composition as a predictive feature**
The model learns associations between tract racial composition and food desert status that exceed what is warranted by actual access conditions. This is evidenced by the 5.9x false positive rate disparity across Black population quartiles and the 33.6% counterfactual flip rate.

*Mitigation 1:* Post-processing threshold calibration using equalized odds — adjust the classification threshold per demographic quartile so that false positive rates are equalized across groups before any predictions are used for policy targeting.

*Mitigation 2:* Adversarial debiasing during training — include a fairness penalty in the objective function that penalizes prediction error correlation with racial composition, rather than removing racial features entirely (which degrades recall for communities that genuinely need intervention).

**Bias source 2 — HOLC audit selection bias**
The 16,421 tracts with HOLC grades represent historically surveyed cities (predominantly older, larger, Northern and Midwestern cities). This population is not representative of the full 72,531-tract national dataset, which limits the geographic generalizability of the HOLC audit finding.

*Mitigation:* Explicitly scope the audit conclusion to HOLC-surveyed cities. Conduct a separate rural food desert analysis using USDA Rural-Urban Continuum Codes to ensure rural and non-surveyed communities are not systematically excluded from the fairness analysis.

**Bias source 3 — Target variable as proxy**
`LILATracts_1And10` is a geographic and economic measure of food access, not a direct measure of food insecurity experienced by residents. A tract may have a supermarket within one mile but residents may still face transportation barriers, time poverty, or economic barriers not captured by the binary label.

*Mitigation:* Supplement the USDA binary label with SNAP participation rate and vehicle access rate as continuous outcome measures for model calibration, and report all predictions with uncertainty intervals rather than point predictions.

---

## Expected Impact and Essential Question

This project demonstrates that the development process of responsible AI/ML directly determines whether a model amplifies or surfaces structural inequality. The DesertMap pipeline applies five responsible development practices — bias identification before modeling, class-balanced training, fairness auditing with multiple complementary methods, explainability through SHAP, and pre-computed inference to ensure deployment transparency — that collectively convert a standard classification problem into an accountable analysis.

The HOLC finding is the clearest answer to the Essential Question: a model that receives no information about historical discrimination nonetheless learns to reproduce it from modern data, because modern data encodes historical policy. Responsible development does not prevent this — but it detects it, quantifies it, and creates the evidentiary basis for mitigation. Without the fairness audit, the model would appear to perform adequately by aggregate metrics. With it, the 5.9x false positive rate disparity and the 1.57x HOLC odds ratio become visible, actionable, and correctable.

The affirmative case: AI can strengthen positive outcomes here by directing policy attention to tracts the USDA definition misses (high recall with calibrated precision), providing tract-level SHAP explanations that policy teams can interrogate, and surfacing geographic patterns of systemic disinvestment that would be difficult to identify through manual analysis of 72,000 individual tracts.

---

## References

1. Aaronson, D., Hartley, D., & Mazumder, B. (2021). The long-run effects of the 1930s HOLC residential security maps on economic mobility. *Federal Reserve Bank of Chicago Working Paper 2017-12*.

2. Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5–32.

3. Lundberg, S. M., & Lee, S. I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems, 30*.

4. Nardone, A., Rudolph, K. E., Morello-Frosch, R., & Casey, J. A. (2021). Redlines and greenspace: The relationship between historical redlining and 2010 greenspace across the United States. *Environmental Health Perspectives, 129*(1), 017006.

5. Nelson, R. K., Winling, L., Marciano, R., & Connolly, N. (2023). *Mapping inequality: Redlining in New Deal America*. Digital Scholarship Lab, University of Richmond. https://dsl.richmond.edu/panorama/redlining/

6. USDA Economic Research Service. (2019). *Food Access Research Atlas*. United States Department of Agriculture. https://www.ers.usda.gov/data-products/food-access-research-atlas/

7. Ver Ploeg, M., Breneman, V., Farrigan, T., Hamrick, K., Hopkins, D., Kaufman, P., ... & Tuckermanty, E. (2015). *Access to affordable and nutritious food: Measuring and understanding food deserts and their consequences* (Economic Information Bulletin No. 33). USDA Economic Research Service.

8. Walker, R. E., Keane, C. R., & Burke, J. G. (2010). Disparities and access to healthy food in the United States: A review of food deserts literature. *Health & Place, 16*(5), 876–884.
