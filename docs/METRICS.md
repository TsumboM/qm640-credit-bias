# Novel Fairness Metrics — Formal Definitions

**Author:** Tsumbo Munyai (2026)  
**Project:** QM640 — Detecting and Quantifying Credit Bias in U.S. Mortgage Lending

---

## 1. TIBAI — Temporal Intersectional Bias Amplification Index

**Definition:**  
TIBAI measures how bias at the intersection of multiple sensitive attributes (e.g., rural + female) changes over time relative to a baseline year.

**Formula:**

```
TIBAI(t) = [DI_intersect(t) - DI_intersect(t₀)] / DI_intersect(t₀)
```

Where:
- `DI_intersect(t)` = Disparate Impact ratio for the intersectional group at time `t`
- `DI_intersect(t₀)` = Baseline DI ratio at the reference year `t₀`

**Interpretation:**
- `TIBAI > 0` → Bias is decreasing over time (improving fairness)
- `TIBAI < 0` → Bias is increasing over time (worsening fairness)
- `TIBAI = 0` → No temporal change in intersectional bias

**2024 Baseline:** TIBAI₀ = 0.0023

---

## 2. PLSS — Proxy Leakage Sensitivity Score

**Definition:**  
PLSS quantifies the degree to which a sensitive or proxy feature influences model predictions, measured as the normalised change in RMSE when that feature is permuted (shuffled).

**Formula:**

```
PLSS(feature_j) = [RMSE_permuted(j) - RMSE_baseline] / RMSE_baseline × 100%
```

Where:
- `RMSE_permuted(j)` = RMSE after randomly permuting feature `j` in the test set
- `RMSE_baseline` = RMSE with all features intact

**Interpretation:**
- `PLSS < 1%` → Negligible proxy leakage
- `1% ≤ PLSS < 5%` → Moderate leakage — monitor
- `PLSS ≥ 5%` → High leakage — feature may encode protected attribute

**Results (HMDA 2024):**

| Feature | PLSS |
|---------|------|
| Location (Rural/Urban) | 2.00% |
| Applicant Sex | 1.04% |

---

## 3. DRSI — Demographic Residual Skewness Index

**Definition:**  
DRSI measures the difference in prediction error skewness between demographic groups. A non-zero DRSI indicates that the model systematically over- or under-predicts for one group relative to another.

**Formula:**

```
DRSI(group_A, group_B) = skewness(errors_A) - skewness(errors_B)
```

Where:
- `errors_g = y_actual - y_predicted` for all observations in group `g`
- `skewness` is the Fisher-Pearson standardised moment coefficient

**Interpretation:**
- `DRSI ≈ 0` → Symmetric, unbiased error distributions across groups
- `DRSI > 0` → Group A has more right-skewed errors (model under-predicts for A)
- `DRSI < 0` → Group A has more left-skewed errors (model over-predicts for A)

---

## References

- Kozodoi, N., Jacob, J., & Lessmann, S. (2022). Fairness in credit scoring. *European Journal of Operational Research*, 297(3), 1083–1094.
- Lundberg, S. M., & Lee, S. I. (2017). A unified approach to interpreting model predictions. *NeurIPS*, 30.
- CFPB (2024). *Home Mortgage Disclosure Act (HMDA) Data*. https://ffiec.cfpb.gov
