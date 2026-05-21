# Bias Identification — DesertMap

## Overview

This document identifies sources of bias in the DesertMap project's data and methodology, and proposes concrete mitigation strategies. Bias identification is conducted as part of the responsible AI development process — not as an afterthought to model completion.

---

## Identified Bias Sources

### 1. Geographic Coverage Bias

**Description:** The USDA Food Access Research Atlas has more complete and granular data for urban census tracts than for rural ones. Rural tracts with sparse population may have missing or estimated values for key features (e.g., distance to nearest supermarket).

**Risk:** The model may perform well in urban settings but produce unreliable predictions in rural or semi-rural tracts — populations that may face the most acute food access challenges.

**Impact Level:** Medium

---

### 2. Temporal Misalignment Bias

**Description:** The three data sources span different time periods. HOLC redlining maps were produced in the 1930s. The ACS 5-Year Estimates are rolling (e.g., 2019–2023). The USDA food access data has its own survey year. Features from different temporal contexts are merged and treated as contemporaneous.

**Risk:** Temporal mismatch may create spurious correlations — a neighborhood may have changed significantly since its HOLC grade was assigned, but the model treats these as equivalent signals.

**Impact Level:** Medium

---

### 3. Label Definition Bias

**Description:** The USDA's food desert definition is based on supermarket proximity (>1 mile in urban areas, >10 miles in rural areas). This definition excludes corner stores, bodegas, farmers markets, food co-ops, community gardens, and other food sources that communities actually use and depend on.

**Risk:** The model learns to predict an administrative label that may not reflect actual community food security. Predicting a "food desert" tract may be a proxy for "lacks a large chain supermarket" rather than "lacks food access."

**Impact Level:** High — this is a fundamental label validity concern that should be disclosed in the proposal and final presentation.

---

### 4. Demographic Encoding and Proxy Discrimination

**Description:** Race and income are present as features in the merged dataset. Because food desert status is historically correlated with race (a downstream effect of redlining), the model may learn to use race as a shortcut predictor. This means the model is at risk of encoding discrimination rather than discovering it.

**Risk:** If deployed, a model that predicts food deserts using race could be used to justify continued disinvestment in communities of color — algorithmic redlining.

**Impact Level:** High — this is the central ethical risk of the project and the primary subject of the fairness audit.

---

## Mitigation Strategies

### Mitigation 1: Fairness Audit by Demographic Group

**Method:**
- Train the model twice: once with all features (including race), once with race features removed.
- Compute precision and recall separately for census tracts grouped by majority racial composition.
- Compute fairness metrics: demographic parity difference, equal opportunity difference.
- Report the accuracy delta between the two models and assess the fairness-accuracy trade-off.

**Outcome:** Provides a quantitative answer to the question "does the model perform equitably across racial groups?" and documents what accuracy is sacrificed by removing race features.

**Implementation:** `notebooks/06_xai.ipynb` and `docs/fairness_audit.md`

---

### Mitigation 2: Counterfactual Fairness Probe

**Method:**
- For each census tract predicted as a food desert, create a counterfactual version of the tract where the race composition is replaced with the city-level average.
- Run both the original and counterfactual tracts through the trained model.
- Count and analyze the tracts where the prediction changes solely due to the race feature perturbation.

**Outcome:** Identifies census tracts where race is the decisive factor in the model's prediction — a direct test of counterfactual fairness.

**Implementation:** `notebooks/06_xai.ipynb` — counterfactual section

---

## Connection to Essential Question

Identifying these biases before model training is not just good practice — it is the practice of responsible AI development. The development process itself is the intervention. A team that trains a food desert model and only discovers racial bias after deployment has failed the communities that model was meant to serve.
