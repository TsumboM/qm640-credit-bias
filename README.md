# QM640 — Detecting and Quantifying Credit Bias in U.S. Mortgage Lending

**Author:** Tsumbo Munyai  
**Institution:** Walsh College  
**Course:** QM640 — Quantitative Methods  
**Dataset:** HMDA 2024 Loan Application Register (LAR) — 1,839,520 records  
**Status:** Interim Report Submitted

---

## Project Overview

This research investigates whether algorithmic mortgage rate-spread predictions systematically disadvantage applicants based on **gender** and **geographic location (rural vs. urban)**, using the 2024 Home Mortgage Disclosure Act (HMDA) public dataset published by the CFPB/FFIEC.

Two predictive models are compared — **Linear Regression** and **XGBoost Regressor** — across six research questions, with three novel fairness metrics introduced:

| Metric | Full Name | Purpose |
|--------|-----------|---------|
| **TIBAI** | Temporal Intersectional Bias Amplification Index | Tracks bias change over time |
| **PLSS** | Proxy Leakage Sensitivity Score | Measures how much sensitive features influence predictions |
| **DRSI** | Demographic Residual Skewness Index | Quantifies asymmetry in prediction errors by group |

---

## Research Questions

| RQ | Question |
|----|----------|
| **RQ1** | Do prediction error distributions differ significantly by gender? |
| **RQ2** | Does location-based bias vary across conventional, FHA, VA, and USDA loan types? |
| **RQ3** | How much do sex and location proxy features leak into predictions (PLSS)? |
| **RQ4** | What is the Pareto trade-off between predictive accuracy (RMSE) and fairness (DI)? |
| **RQ5** | Do rural female applicants face compounding intersectional bias beyond additive effects? |
| **RQ6** | What is the TIBAI 2024 baseline for temporal bias tracking? |

---

## Repository Structure

```
qm640-credit-bias/
│
├── notebooks/
│   └── HMDA_2024_Full_Analysis.ipynb     # Full end-to-end analysis notebook (58 cells)
│
├── src/
│   ├── pipeline/
│   │   ├── hmda_analysis.py              # Core EDA and modelling pipeline
│   │   ├── hmda_full_pipeline.py         # Full pipeline with all 6 RQs
│   │   └── hmda_supplementary_analysis.py # Supplementary RQ1/RQ2/RQ4 analysis
│   ├── figures/
│   │   ├── regen_rq1_figure.py           # RQ1: Error distribution by gender
│   │   ├── regen_feature_importance.py   # XGBoost feature importance chart
│   │   └── regen_pareto_tradeoff.py      # RQ4: Pareto accuracy–fairness trade-off
│   └── generate_report.py               # Generates the Word report from results
│
├── reports/
│   ├── QM640_Interim_Report_Final.docx   # Submitted Interim Report
│   └── figures/                          # All 11 publication-quality figures
│       ├── fig1_rate_spread_by_gender.png
│       ├── fig2_boxplot_gender_location.png
│       ├── fig3_heatmap_intersectional.png
│       ├── fig4_scatter_income_rate_spread.png
│       ├── fig5_feature_importance.png
│       ├── fig6_actual_vs_predicted.png
│       ├── fig7_residual_distribution_gender.png
│       ├── fig8_fairness_metrics_comparison.png
│       ├── fig_rq1_error_distributions.png
│       ├── fig_rq2_loan_type_bias.png
│       └── fig_rq4_pareto_tradeoff.png
│
├── data/
│   └── .gitkeep                          # HMDA 2024 LAR CSV not tracked (2.5 GB)
│
├── docs/
│   ├── METRICS.md                        # Formal definitions of TIBAI, PLSS, DRSI
│   └── DATA_DICTIONARY.md               # HMDA variable descriptions
│
├── results/
│   └── .gitkeep                          # Model outputs and JSON results (generated at runtime)
│
├── tests/
│   └── .gitkeep                          # Unit tests (planned for final report phase)
│
├── requirements.txt                      # Python dependencies
├── .gitignore                            # Excludes large data files and caches
└── README.md                             # This file
```

---

## Key Results (Interim Report)

### Model Performance

| Model | RMSE | R² |
|-------|------|-----|
| Linear Regression | 1.0232 | 0.2853 |
| XGBoost (depth=4) | 0.8239 | 0.5366 |

### Fairness Findings

| RQ | Finding |
|----|---------|
| RQ1 | XGB KS=0.0059 (p=0.395) — distributions closely aligned; females receive slightly lower MAE |
| RQ2 | Conventional loans most biased (DPD=0.0252); FHA least biased (DPD=0.0025) |
| RQ3 | PLSS location=2.00%, PLSS sex=1.04% — both below 5% leakage threshold |
| RQ4 | XGB depth=4 is Pareto-optimal (RMSE=6.4798, DI=0.9991) |
| RQ5 | Rural female compounding effect confirmed (+0.0065 above additive sum) |
| RQ6 | TIBAI 2024 baseline = 0.0023 (established for future temporal comparison) |

---

## Data Source

- **Dataset:** [HMDA 2024 LAR Public Data](https://ffiec.cfpb.gov/data-publication/2024)
- **Publisher:** CFPB / FFIEC
- **Records:** 1,839,520 originated loans with valid rate spread
- **Note:** The raw CSV (~2.5 GB) is excluded from this repository via `.gitignore`. Download directly from the FFIEC portal.

---

## Setup and Reproduction

```bash
# 1. Clone the repository
git clone https://github.com/TsumboM/qm640-credit-bias.git
cd qm640-credit-bias

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download HMDA 2024 data and place in data/
#    https://ffiec.cfpb.gov/data-publication/2024

# 4. Run the full pipeline
python src/pipeline/hmda_full_pipeline.py

# 5. Open the analysis notebook
jupyter notebook notebooks/HMDA_2024_Full_Analysis.ipynb
```

---

## Citation

> Munyai, T. (2026). *Detecting and Quantifying Credit Bias in U.S. Mortgage Lending: A Comparative Analysis of Linear Regression and XGBoost Using HMDA 2024 Data*. Walsh College, QM640 Interim Report.

---

## License

This project is submitted for academic purposes at Walsh College. All code is available for review and educational use.
