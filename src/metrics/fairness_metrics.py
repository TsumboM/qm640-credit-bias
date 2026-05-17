"""
fairness_metrics.py
===================
Novel fairness metrics introduced by Munyai (2026) for QM640.

Metrics:
    - TIBAI: Temporal Intersectional Bias Amplification Index
    - PLSS:  Proxy Leakage Sensitivity Score
    - DRSI:  Demographic Residual Skewness Index

Usage:
    from src.metrics.fairness_metrics import compute_plss, compute_drsi, compute_tibai
"""

import numpy as np
from scipy import stats
from sklearn.metrics import mean_squared_error


def compute_plss(model, X_test: np.ndarray, y_test: np.ndarray,
                 feature_index: int, n_repeats: int = 5) -> float:
    """
    Proxy Leakage Sensitivity Score (PLSS).

    Measures the percentage increase in RMSE when a sensitive/proxy feature
    is randomly permuted, indicating how much the model relies on that feature.

    Parameters
    ----------
    model       : fitted sklearn-compatible model with .predict()
    X_test      : test feature matrix (n_samples, n_features)
    y_test      : true target values
    feature_index : column index of the sensitive feature to permute
    n_repeats   : number of permutation repeats (default 5)

    Returns
    -------
    plss : float — percentage increase in RMSE (0–100+)
    """
    baseline_rmse = np.sqrt(mean_squared_error(y_test, model.predict(X_test)))
    permuted_rmses = []
    rng = np.random.default_rng(42)
    for _ in range(n_repeats):
        X_perm = X_test.copy()
        X_perm[:, feature_index] = rng.permutation(X_perm[:, feature_index])
        permuted_rmses.append(
            np.sqrt(mean_squared_error(y_test, model.predict(X_perm)))
        )
    mean_permuted_rmse = np.mean(permuted_rmses)
    plss = (mean_permuted_rmse - baseline_rmse) / baseline_rmse * 100.0
    return round(plss, 4)


def compute_drsi(errors: np.ndarray, group_mask_a: np.ndarray,
                 group_mask_b: np.ndarray) -> float:
    """
    Demographic Residual Skewness Index (DRSI).

    Measures the difference in prediction error skewness between two groups.
    A non-zero DRSI indicates systematic over- or under-prediction for one group.

    Parameters
    ----------
    errors        : array of prediction errors (y_actual - y_predicted)
    group_mask_a  : boolean mask for group A
    group_mask_b  : boolean mask for group B

    Returns
    -------
    drsi : float — skewness(A) - skewness(B)
    """
    skew_a = stats.skew(errors[group_mask_a])
    skew_b = stats.skew(errors[group_mask_b])
    return round(float(skew_a - skew_b), 6)


def compute_tibai(di_baseline: float, di_current: float) -> float:
    """
    Temporal Intersectional Bias Amplification Index (TIBAI).

    Measures the relative change in intersectional Disparate Impact (DI)
    from a baseline year to the current year.

    Parameters
    ----------
    di_baseline : DI ratio at the reference/baseline year
    di_current  : DI ratio at the current year

    Returns
    -------
    tibai : float — positive means improving fairness, negative means worsening
    """
    if di_baseline == 0:
        raise ValueError("Baseline DI ratio cannot be zero.")
    tibai = (di_current - di_baseline) / di_baseline
    return round(float(tibai), 6)


def disparate_impact_ratio(y_pred: np.ndarray, group_mask_a: np.ndarray,
                            group_mask_b: np.ndarray,
                            threshold: float = None) -> float:
    """
    Compute the Disparate Impact (DI) ratio between two groups.

    For regression: DI = mean(y_pred[A]) / mean(y_pred[B])
    For classification (if threshold provided): DI = P(positive|A) / P(positive|B)

    Parameters
    ----------
    y_pred        : predicted values
    group_mask_a  : boolean mask for the protected group (numerator)
    group_mask_b  : boolean mask for the reference group (denominator)
    threshold     : optional classification threshold

    Returns
    -------
    di : float
    """
    if threshold is not None:
        rate_a = np.mean(y_pred[group_mask_a] >= threshold)
        rate_b = np.mean(y_pred[group_mask_b] >= threshold)
    else:
        rate_a = np.mean(y_pred[group_mask_a])
        rate_b = np.mean(y_pred[group_mask_b])

    if rate_b == 0:
        return np.inf
    return round(float(rate_a / rate_b), 6)
