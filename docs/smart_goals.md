# SMART Goals — DesertMap

## Project Goal

Build a machine learning model that predicts food desert status at the census tract level and audits its own bias against historical redlining patterns.

---

## SMART Goal Breakdown

| Dimension | Goal |
|-----------|------|
| **Specific** | Train a Random Forest classifier on USDA food access data merged with Census ACS demographics to predict food desert status (binary); conduct a SHAP-based fairness audit to identify whether race features drive predictions |
| **Measurable** | Achieve F1 score > 0.75 on held-out test set; produce fairness audit showing precision/recall disaggregated by majority census tract race; document accuracy delta when race features are removed |
| **Achievable** | USDA and Census datasets are publicly available and documented; Random Forest and SHAP are well-supported in scikit-learn and the shap library; feasible for a solo intermediate Python practitioner |
| **Relevant** | Directly answers the Essential Question: the development process (the audit) is the responsible AI intervention |
| **Time-bound** | Model trained by end of Week 6; fairness audit complete by end of Week 6; Streamlit deployment by end of Week 10; final presentation Week 12 |

---

## Milestones

| Milestone | Target Date | Success Criterion |
|-----------|------------|-------------------|
| Datasets acquired and joined | End of Week 1 | FIPS join produces >60,000 valid tract rows |
| EDA complete | End of Week 2 | 3 figures committed, class balance documented |
| Bias identification documented | End of Week 3 | `bias_identification.md` complete with 4 sources and 2 mitigations |
| Baseline Logistic Regression | End of Week 4 | Metrics logged: accuracy, F1, ROC-AUC |
| Random Forest + SHAP | End of Week 5 | SHAP plots committed; top features identified |
| Fairness audit | End of Week 6 | `fairness_audit.md` complete |
| Proposal submitted | Week 7 | 2 pages, 7 citations, rubric verified |
| K-Fold evaluation | End of Week 8 | Cross-val results logged |
| XAI complete | End of Week 9 | All SHAP plots publication-ready |
| Streamlit deployed | End of Week 10 | Live URL confirmed working |
| Final presentation | Week 12 | Score target: 24/30 |
| GitHub Page live | Week 13 | All content published |
