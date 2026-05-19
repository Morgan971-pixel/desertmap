# DesertMap

**Predicting Food Desert Status in U.S. Census Tracts and Auditing for Redlining-Era Bias**

AI4ALL Ignite Program — Semester 1 Portfolio Project

---

## Research Question

Can a supervised ML model using socioeconomic, transportation, and demographic census features predict which urban census tracts qualify as USDA-defined food deserts, and do the model's strongest predictive features reveal patterns of structural inequality rooted in historical redlining?

---

## Model

Two supervised classifiers are trained and compared:

| Model | Type | Purpose |
|-------|------|---------|
| Logistic Regression | Linear binary classifier | Interpretable baseline; coefficient analysis |
| Random Forest | Ensemble binary classifier | Performance ceiling; SHAP explainability |

**Inputs:** Socioeconomic features (median income, SNAP enrollment, vehicle access), demographic features (race composition), geographic features (distance to supermarket, urban/rural flag), HOLC redlining grade (ordinal encoded)

**Output:** Binary label — food desert (1) / not food desert (0)

**Pros of Random Forest:** Handles non-linear feature interactions; robust to outliers; native feature importance
**Cons of Random Forest:** Less interpretable than Logistic Regression; can overfit on small feature sets; slower inference

---

## Data Sources

| Dataset | Source | Level |
|---------|--------|-------|
| USDA Food Access Research Atlas | ers.usda.gov | Census tract |
| U.S. Census ACS 5-Year Estimates | census.gov | Census tract |
| Mapping Inequality HOLC Shapefiles | dsl.richmond.edu | City/neighborhood |

---

## Repository Structure

```
desertmap/
├── data/
│   ├── raw/            # Original downloaded datasets (not modified)
│   └── processed/      # Cleaned, merged, feature-engineered data
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_cleaning.ipynb
│   ├── 03_baseline_model.ipynb
│   ├── 04_random_forest.ipynb
│   ├── 05_evaluation.ipynb
│   └── 06_xai.ipynb
├── app/
│   └── streamlit_app.py
├── docs/
│   ├── smart_goals.md
│   ├── bias_identification.md
│   └── fairness_audit.md
├── outputs/
│   └── figures/        # All publication-ready plots
├── requirements.txt
└── README.md
```

---

## Bias Mitigation

Two mitigation strategies are implemented and documented:

1. **Fairness audit by demographic group** — model is retrained with race features removed; accuracy delta and fairness metrics (equal opportunity, demographic parity) are compared across both versions
2. **Counterfactual fairness probe** — for tracts predicted as food deserts, race composition is perturbed to the city average and prediction stability is measured

Full methodology: `docs/fairness_audit.md`

---

## Societal Impact

A model that predicts food deserts by encoding race is not solving food insecurity — it is encoding the geography of discrimination. Responsible AI development in this context means building the audit into the development process itself, not as an afterthought.

---

## Reproduction

```bash
pip install -r requirements.txt
jupyter lab
# Run notebooks in order: 01 → 02 → 03 → 04 → 05 → 06
streamlit run app/streamlit_app.py
```

---

## Live Demo

Streamlit app: [link to be added at Week 10 deployment]
