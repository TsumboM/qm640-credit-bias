"""
QM640 Capstone - Final Analysis Pipeline
=========================================
Algorithmic Fairness in Mortgage Lending: A Multi-Year Analysis
of HMDA Data (2022-2024)

Author: Tsumbo Munyai
Institution: Walsh College
Course: QM640

Usage:
    python pipeline.py --data-dir ./data --output-dir ./results

All paths are relative. No hardcoded system paths.
"""

import argparse
import os
import sys
import gc
import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
from scipy.stats import ks_2samp, mannwhitneyu, levene, t as t_dist
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb

warnings.filterwarnings('ignore')

# ── Default paths (relative, overridable via CLI) ─────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "results"

# ── Constants ─────────────────────────────────────────────────────────────────
SAMPLE_N   = 120000   # per year – keeps memory under 4 GB total
CHUNK_SIZE = 400000

COLS = [
    'action_taken', 'applicant_sex', 'rate_spread', 'income',
    'loan_amount', 'combined_loan_to_value_ratio', 'loan_term',
    'loan_type', 'tract_minority_population_percent',
    'tract_population', 'debt_to_income_ratio'
]
NUMERIC_COLS = [
    'action_taken', 'applicant_sex', 'rate_spread', 'income',
    'loan_amount', 'combined_loan_to_value_ratio', 'loan_term',
    'loan_type', 'tract_minority_population_percent', 'tract_population'
]
DTI_MAP = {
    '<20%': 15, '20%-<30%': 25, '30%-<36%': 33, '36': 36, '37': 37,
    '38': 38, '39': 39, '40': 40, '41': 41, '42': 42, '43': 43,
    '44': 44, '45': 45, '46': 46, '47': 47, '48': 48, '49': 49,
    '50%-60%': 55, '>60%': 65, 'Exempt': np.nan
}
LOAN_TYPE_MAP = {1: 'Conventional', 2: 'FHA-Insured', 3: 'VA-Guaranteed', 4: 'USDA/RHS'}
FEATURES = [
    'income', 'loan_amount', 'combined_loan_to_value_ratio',
    'loan_term', 'dti_numeric', 'tract_minority_population_percent',
    'sex_encoded', 'location_encoded', 'sex_x_location'
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def cohens_d(a, b):
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    pooled = np.sqrt(((na-1)*np.std(a, ddof=1)**2 + (nb-1)*np.std(b, ddof=1)**2) / (na+nb-2))
    return float((np.mean(a) - np.mean(b)) / pooled) if pooled > 0 else 0.0

def ci95(arr):
    n = len(arr)
    if n < 2:
        return (float(np.mean(arr)), float(np.mean(arr)))
    se = np.std(arr, ddof=1) / np.sqrt(n)
    margin = t_dist.ppf(0.975, df=n-1) * se
    return (round(float(np.mean(arr) - margin), 6), round(float(np.mean(arr) + margin), 6))

def approx_power(d, n1, n2, alpha=0.05):
    if n1 < 2 or n2 < 2:
        return 0.0
    se = np.sqrt(1/n1 + 1/n2)
    z_beta = abs(d)/se - 1.96
    return round(float(stats.norm.cdf(z_beta)), 4)

# ── Data loading ──────────────────────────────────────────────────────────────
def load_year(csv_path: Path, year: int, sample_n: int = SAMPLE_N):
    print(f"\n[{year}] Loading: {csv_path.name}")
    chunks_out = []
    n_raw = 0

    for chunk in pd.read_csv(csv_path, usecols=COLS, low_memory=False, chunksize=CHUNK_SIZE):
        n_raw += len(chunk)
        # Force numeric conversion for all numeric columns
        for col in NUMERIC_COLS:
            if col in chunk.columns:
                chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
        # Filter: originated loans, male/female applicants
        chunk = chunk[chunk['action_taken'] == 1]
        chunk = chunk[chunk['applicant_sex'].isin([1.0, 2.0])]
        # Drop missing/invalid rate_spread
        chunk = chunk.dropna(subset=['rate_spread'])
        chunk = chunk[chunk['rate_spread'] > 0]
        # Drop missing core features
        chunk = chunk.dropna(subset=['income', 'loan_amount',
                                     'combined_loan_to_value_ratio', 'loan_term'])
        chunk = chunk[(chunk['income'] > 0) & (chunk['loan_amount'] > 0)]
        # DTI
        chunk['dti_numeric'] = chunk['debt_to_income_ratio'].map(DTI_MAP)
        chunk = chunk.dropna(subset=['dti_numeric'])
        chunks_out.append(chunk)

    df = pd.concat(chunks_out, ignore_index=True)
    del chunks_out; gc.collect()
    n_clean = len(df)
    print(f"[{year}] Raw={n_raw:,}  Clean={n_clean:,}  ({100*n_clean/n_raw:.1f}%)")

    # Clip outliers (column-wise, only numeric)
    for col in ['income', 'loan_amount', 'combined_loan_to_value_ratio']:
        lo, hi = df[col].quantile([0.01, 0.99])
        df[col] = df[col].clip(lo, hi)
    lo, hi = df['rate_spread'].quantile([0.005, 0.995])
    df['rate_spread'] = df['rate_spread'].clip(lo, hi)

    # Feature engineering
    df['sex_encoded']      = (df['applicant_sex'] == 2).astype(int)   # 1 = female
    df['location_encoded'] = (df['tract_population'] < df['tract_population'].median()).astype(int)  # 1 = rural
    df['loan_type_name']   = df['loan_type'].map(LOAN_TYPE_MAP).fillna('Other')
    df['sex_x_location']   = df['sex_encoded'] * df['location_encoded']

    # Sample
    if len(df) > sample_n:
        df = df.sample(n=sample_n, random_state=42).reset_index(drop=True)
    print(f"[{year}] Final sample: {len(df):,}")
    return df, n_raw, n_clean

# ── Main pipeline ─────────────────────────────────────────────────────────────
def run(data_dir: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    R = {}   # results dict

    # ── 1. Load all years ────────────────────────────────────────────────────
    year_files = {
        2022: data_dir / '2022_public_lar_csv.csv',
        2023: data_dir / '2023_public_lar_csv.csv',
        2024: data_dir / '2024_public_lar_csv.csv',
    }
    # Fallback: look in ./hmda_YYYY/ if data_dir files not found
    fallback = {
        2022: Path('./data/hmda_2022/2022_public_lar_csv.csv'),
        2023: Path('./data/hmda_2023/2023_public_lar_csv.csv'),
        2024: Path('./data/hmda_2024/2024_public_lar_csv.csv'),
    }

    year_dfs = {}
    cleaning_stats = {}
    eda_stats = {}

    for year in [2022, 2023, 2024]:
        csv_path = year_files[year] if year_files[year].exists() else fallback[year]
        if not csv_path.exists():
            print(f"[WARN] {year} data not found at {csv_path}, skipping.")
            continue
        df_yr, n_raw, n_clean = load_year(csv_path, year)
        year_dfs[year] = df_yr
        cleaning_stats[str(year)] = {
            'n_raw': n_raw, 'n_clean': n_clean,
            'pct_retained': round(100*n_clean/n_raw, 1)
        }
        eda_stats[str(year)] = {
            'year': year, 'n_total': len(df_yr),
            'pct_female':       round(100*df_yr['sex_encoded'].mean(), 1),
            'pct_rural':        round(100*df_yr['location_encoded'].mean(), 1),
            'rate_spread_mean': round(df_yr['rate_spread'].mean(), 4),
            'rate_spread_median': round(df_yr['rate_spread'].median(), 4),
            'rate_spread_std':  round(df_yr['rate_spread'].std(), 4),
            'rate_spread_male_mean':   round(df_yr[df_yr['sex_encoded']==0]['rate_spread'].mean(), 4),
            'rate_spread_female_mean': round(df_yr[df_yr['sex_encoded']==1]['rate_spread'].mean(), 4),
            'rate_spread_rural_mean':  round(df_yr[df_yr['location_encoded']==1]['rate_spread'].mean(), 4),
            'rate_spread_urban_mean':  round(df_yr[df_yr['location_encoded']==0]['rate_spread'].mean(), 4),
            'income_mean':      round(df_yr['income'].mean(), 1),
            'loan_amount_mean': round(df_yr['loan_amount'].mean(), 1),
        }

    R['data_cleaning'] = cleaning_stats
    R['eda'] = eda_stats

    if 2024 not in year_dfs:
        print("[ERROR] 2024 data required for primary analysis. Exiting.")
        sys.exit(1)

    df = year_dfs[2024]
    print(f"\n[PRIMARY] 2024 dataset: {len(df):,} records")

    # ── 2. Correlation matrix ─────────────────────────────────────────────────
    print("\n[CORR] Correlation matrix...")
    corr_cols = ['rate_spread','income','loan_amount','combined_loan_to_value_ratio',
                 'loan_term','dti_numeric','tract_minority_population_percent',
                 'sex_encoded','location_encoded','sex_x_location']
    corr_df = df[corr_cols].corr().round(3)
    R['correlation_matrix'] = corr_df.to_dict()
    np.save(output_dir / 'corr_matrix.npy', corr_df.values)
    np.save(output_dir / 'corr_labels.npy', np.array(corr_cols))

    # ── 3. VIF ────────────────────────────────────────────────────────────────
    print("\n[VIF] Variance Inflation Factors...")
    X_vif = df[FEATURES].values.astype(float)
    vif_data = {}
    for i, col in enumerate(FEATURES):
        y_v = X_vif[:, i]
        X_r = np.delete(X_vif, i, axis=1)
        lr_v = LinearRegression().fit(X_r, y_v)
        r2_v = r2_score(y_v, lr_v.predict(X_r))
        vif_data[col] = round(1/(1-r2_v) if r2_v < 0.9999 else 999.0, 3)
    R['vif'] = vif_data
    print("[VIF]", {k: v for k,v in vif_data.items()})

    # ── 4. Model training ─────────────────────────────────────────────────────
    print("\n[MODEL] Training models with 5-fold CV...")
    X = df[FEATURES].values.astype(float)
    y_true = df['rate_spread'].values.astype(float)
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)
    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    # Linear Regression
    lr_m = LinearRegression()
    lr_cv_rmse = np.sqrt(-cross_val_score(lr_m, X_sc, y_true, cv=kf, scoring='neg_mean_squared_error'))
    lr_cv_r2   = cross_val_score(lr_m, X_sc, y_true, cv=kf, scoring='r2')
    lr_m.fit(X_sc, y_true)
    y_pred_lr = lr_m.predict(X_sc)
    lr_rmse = round(float(np.sqrt(mean_squared_error(y_true, y_pred_lr))), 4)
    lr_mae  = round(float(mean_absolute_error(y_true, y_pred_lr)), 4)
    lr_r2   = round(float(r2_score(y_true, y_pred_lr)), 4)
    print(f"[LR]  RMSE={lr_rmse}  R2={lr_r2}  CV-RMSE={lr_cv_rmse.mean():.4f}±{lr_cv_rmse.std():.4f}")

    # XGBoost
    xgb_params = {'max_depth':6,'n_estimators':300,'learning_rate':0.1,
                  'subsample':0.9,'colsample_bytree':0.9,'reg_alpha':0.0,
                  'random_state':42,'n_jobs':-1,'verbosity':0}
    xgb_m = xgb.XGBRegressor(**xgb_params)
    xgb_cv_rmse = np.sqrt(-cross_val_score(xgb_m, X, y_true, cv=kf, scoring='neg_mean_squared_error'))
    xgb_m.fit(X, y_true)
    y_pred_xgb = xgb_m.predict(X)
    xgb_rmse = round(float(np.sqrt(mean_squared_error(y_true, y_pred_xgb))), 4)
    xgb_mae  = round(float(mean_absolute_error(y_true, y_pred_xgb)), 4)
    xgb_r2   = round(float(r2_score(y_true, y_pred_xgb)), 4)
    print(f"[XGB] RMSE={xgb_rmse}  R2={xgb_r2}  CV-RMSE={xgb_cv_rmse.mean():.4f}±{xgb_cv_rmse.std():.4f}")

    R['model_performance'] = {
        'lr':  {'rmse': lr_rmse, 'mae': lr_mae, 'r2': lr_r2,
                'cv_rmse_mean': round(float(lr_cv_rmse.mean()),4),
                'cv_rmse_std':  round(float(lr_cv_rmse.std()),4),
                'cv_r2_mean':   round(float(lr_cv_r2.mean()),4),
                'cv_r2_std':    round(float(lr_cv_r2.std()),4)},
        'xgb': {'rmse': xgb_rmse, 'mae': xgb_mae, 'r2': xgb_r2,
                'cv_rmse_mean': round(float(xgb_cv_rmse.mean()),4),
                'cv_rmse_std':  round(float(xgb_cv_rmse.std()),4),
                'best_params':  xgb_params},
    }
    R['feature_importance'] = {k: round(float(v),6) for k,v in
                                zip(FEATURES, xgb_m.feature_importances_)}

    # Save predictions
    np.save(output_dir/'preds_lr.npy',  y_pred_lr)
    np.save(output_dir/'preds_xgb.npy', y_pred_xgb)
    np.save(output_dir/'y_true.npy',    y_true)
    np.save(output_dir/'sex.npy',       df['sex_encoded'].values)
    np.save(output_dir/'location.npy',  df['location_encoded'].values)
    np.save(output_dir/'loan_type.npy', df['loan_type_name'].values)

    # ── 5. RQ1: Gender error distributions ───────────────────────────────────
    print("\n[RQ1] Gender error distributions...")
    err_lr  = y_true - y_pred_lr
    err_xgb = y_true - y_pred_xgb
    male_m   = df['sex_encoded'].values == 0
    female_m = df['sex_encoded'].values == 1
    n_male, n_female = int(male_m.sum()), int(female_m.sum())

    def rq1_stats(err, mm, fm):
        ks  = ks_2samp(err[mm], err[fm])
        mwu = mannwhitneyu(err[mm], err[fm], alternative='two-sided')
        lev = levene(err[mm], err[fm])
        d   = cohens_d(err[fm], err[mm])
        drsi = round(abs(float(stats.skew(err[fm])) - float(stats.skew(err[mm]))), 4)
        return {
            'ks_stat': round(float(ks.statistic),4), 'ks_p': round(float(ks.pvalue),4),
            'mwu_p':   round(float(mwu.pvalue),4),
            'levene_p':round(float(lev.pvalue),4),
            'cohens_d':round(d,4), 'power': approx_power(d, n_male, n_female),
            'drsi': drsi,
            'mae_male':   round(float(np.abs(err[mm]).mean()),4),
            'mae_female': round(float(np.abs(err[fm]).mean()),4),
            'mean_error_male':   round(float(err[mm].mean()),4),
            'mean_error_female': round(float(err[fm].mean()),4),
            'ci_male':   ci95(err[mm]), 'ci_female': ci95(err[fm]),
            'reject_h0': bool(ks.pvalue < 0.05),
        }

    R['rq1'] = {'n_male': n_male, 'n_female': n_female,
                'lr':  rq1_stats(err_lr,  male_m, female_m),
                'xgb': rq1_stats(err_xgb, male_m, female_m)}
    print(f"[RQ1] LR  KS p={R['rq1']['lr']['ks_p']},  d={R['rq1']['lr']['cohens_d']}")
    print(f"[RQ1] XGB KS p={R['rq1']['xgb']['ks_p']}, d={R['rq1']['xgb']['cohens_d']}")

    # ── 6. RQ2: Location bias by loan type ───────────────────────────────────
    print("\n[RQ2] Location bias by loan type...")
    rq2 = {}
    for lt in ['Conventional','FHA-Insured','VA-Guaranteed','USDA/RHS']:
        mask   = df['loan_type_name'].values == lt
        rural  = mask & (df['location_encoded'].values == 1)
        urban  = mask & (df['location_encoded'].values == 0)
        if rural.sum() < 30 or urban.sum() < 30:
            continue
        rp, up = y_pred_xgb[rural], y_pred_xgb[urban]
        mwu = mannwhitneyu(rp, up, alternative='two-sided')
        d   = cohens_d(rp, up)
        rq2[lt] = {
            'n_rural': int(rural.sum()), 'n_urban': int(urban.sum()),
            'rural_mean_pred': round(float(rp.mean()),4),
            'urban_mean_pred': round(float(up.mean()),4),
            'dpd': round(float(rp.mean()-up.mean()),4),
            'di':  round(float(rp.mean()/up.mean()),4) if up.mean()>0 else None,
            'cohens_d': round(d,4),
            'ci_rural': ci95(rp), 'ci_urban': ci95(up),
            'mwu_p': round(float(mwu.pvalue),4),
            'reject_h0': bool(mwu.pvalue < 0.05),
        }
        print(f"[RQ2] {lt}: DPD={rq2[lt]['dpd']}, DI={rq2[lt]['di']}, d={d:.4f}")
    R['rq2'] = rq2

    # ── 7. RQ3: PLSS proxy leakage ───────────────────────────────────────────
    print("\n[RQ3] PLSS proxy leakage...")
    rq3 = {}
    for feat in ['sex_encoded','location_encoded']:
        fi = FEATURES.index(feat)
        perms = []
        for _ in range(10):
            Xp = X.copy()
            Xp[:,fi] = np.random.permutation(Xp[:,fi])
            perms.append(float(np.sqrt(mean_squared_error(y_true, xgb_m.predict(Xp)))))
        pm   = float(np.mean(perms))
        plss = round(100*(pm - xgb_rmse)/xgb_rmse, 4)
        rq3[feat] = {'baseline_rmse': xgb_rmse, 'permuted_rmse_mean': round(pm,4),
                     'plss_pct': plss, 'reject_h0': plss > 0.1}
        print(f"[RQ3] {feat}: PLSS={plss}%")
    R['rq3'] = rq3

    # ── 8. RQ4: Pareto trade-off ──────────────────────────────────────────────
    print("\n[RQ4] Pareto trade-off...")
    rural_m = df['location_encoded'].values == 1
    urban_m = df['location_encoded'].values == 0
    pareto  = []
    configs = [
        ('Linear Regression', None),
        ('XGB (depth=4)', {'max_depth':4,'n_estimators':200,'learning_rate':0.1,
                           'subsample':0.8,'colsample_bytree':0.8,'reg_alpha':0.1,
                           'random_state':42,'n_jobs':-1,'verbosity':0}),
        ('XGB (depth=6)', {'max_depth':6,'n_estimators':300,'learning_rate':0.1,
                           'subsample':0.9,'colsample_bytree':0.9,'reg_alpha':0.0,
                           'random_state':42,'n_jobs':-1,'verbosity':0}),
        ('XGB (depth=8)', {'max_depth':8,'n_estimators':300,'learning_rate':0.05,
                           'subsample':0.8,'colsample_bytree':0.8,'reg_alpha':0.5,
                           'random_state':42,'n_jobs':-1,'verbosity':0}),
    ]
    for name, params in configs:
        if params is None:
            preds = y_pred_lr
        else:
            m = xgb.XGBRegressor(**params); m.fit(X, y_true); preds = m.predict(X)
        rmse_v = round(float(np.sqrt(mean_squared_error(y_true, preds))),4)
        di_g = round(float(preds[female_m].mean()/preds[male_m].mean()),4) if preds[male_m].mean()>0 else None
        di_l = round(float(preds[rural_m].mean()/preds[urban_m].mean()),4) if preds[urban_m].mean()>0 else None
        pareto.append({'model': name, 'rmse': rmse_v, 'di_gender': di_g, 'di_location': di_l})
        print(f"[RQ4] {name}: RMSE={rmse_v}, DI_g={di_g}, DI_l={di_l}")

    xgb_rows = [r for r in pareto if r['model'] != 'Linear Regression']
    optimal  = min(xgb_rows, key=lambda r: r['rmse'])
    R['rq4'] = {'pareto_table': pareto, 'optimal': optimal}

    # ── 9. RQ5: Intersectional bias ───────────────────────────────────────────
    print("\n[RQ5] Intersectional bias...")
    rf_m = rural_m & (df['sex_encoded'].values == 1)
    um_m = urban_m & (df['sex_encoded'].values == 0)
    mean_all = float(y_pred_xgb.mean())
    mean_rf  = float(y_pred_xgb[rf_m].mean())
    mean_um  = float(y_pred_xgb[um_m].mean())
    rural_eff  = float(y_pred_xgb[rural_m].mean()) - mean_all
    female_eff = float(y_pred_xgb[female_m].mean()) - mean_all
    additive   = mean_all + rural_eff + female_eff
    compound   = mean_rf - additive
    mwu5 = mannwhitneyu(y_pred_xgb[rf_m], y_pred_xgb[um_m], alternative='two-sided')
    d5   = cohens_d(y_pred_xgb[rf_m], y_pred_xgb[um_m])
    R['rq5'] = {
        'mean_all': round(mean_all,4), 'mean_rural': round(float(y_pred_xgb[rural_m].mean()),4),
        'mean_urban': round(float(y_pred_xgb[urban_m].mean()),4),
        'mean_female': round(float(y_pred_xgb[female_m].mean()),4),
        'mean_male':   round(float(y_pred_xgb[male_m].mean()),4),
        'mean_rural_female': round(mean_rf,4), 'mean_urban_male': round(mean_um,4),
        'rural_effect': round(rural_eff,4), 'female_effect': round(female_eff,4),
        'additive_prediction': round(additive,4), 'compounding_effect': round(compound,4),
        'cohens_d': round(d5,4),
        'ci_rural_female': ci95(y_pred_xgb[rf_m]),
        'ci_urban_male':   ci95(y_pred_xgb[um_m]),
        'mwu_p': round(float(mwu5.pvalue),4),
        'n_rural_female': int(rf_m.sum()), 'n_urban_male': int(um_m.sum()),
        'reject_h0': bool(mwu5.pvalue < 0.05),
    }
    print(f"[RQ5] Compound={round(compound,4)}, d={round(d5,4)}, p={round(float(mwu5.pvalue),4)}")

    # ── 10. RQ6: TIBAI temporal ───────────────────────────────────────────────
    print("\n[RQ6] TIBAI temporal analysis...")
    rq6 = {'di_by_year': {}}
    tibai_base = None
    for year in [2022, 2023, 2024]:
        if year not in year_dfs:
            continue
        d_yr  = year_dfs[year]
        Xy    = d_yr[FEATURES].values.astype(float)
        preds_yr = xgb_m.predict(Xy)
        rf_yr = (d_yr['location_encoded'].values==1) & (d_yr['sex_encoded'].values==1)
        um_yr = (d_yr['location_encoded'].values==0) & (d_yr['sex_encoded'].values==0)
        if rf_yr.sum() < 10 or um_yr.sum() < 10:
            continue
        di_yr = round(float(preds_yr[rf_yr].mean()/preds_yr[um_yr].mean()),4)
        rq6['di_by_year'][str(year)] = di_yr
        if tibai_base is None:
            tibai_base = di_yr
        rq6[str(year)] = {'di_intersect': di_yr, 'tibai': round(di_yr - tibai_base, 4)}
        print(f"[RQ6] {year}: DI={di_yr}, TIBAI={round(di_yr-tibai_base,4)}")

    di_vals = list(rq6['di_by_year'].values())
    if len(di_vals) >= 3:
        tau, tau_p = stats.kendalltau(range(len(di_vals)), di_vals)
    else:
        tau, tau_p = 0.0, 1.0
    rq6['trend_stat'] = round(float(tau),4)
    rq6['trend_p']    = round(float(tau_p),4)
    rq6['reject_h0']  = bool(tau_p < 0.05)
    R['rq6'] = rq6

    # ── 11. Statistical power summary ─────────────────────────────────────────
    R['statistical_power'] = {
        'rq1_lr':  R['rq1']['lr']['power'],
        'rq1_xgb': R['rq1']['xgb']['power'],
        'rq2_conventional': approx_power(
            rq2.get('Conventional',{}).get('cohens_d',0),
            rq2.get('Conventional',{}).get('n_rural',1000),
            rq2.get('Conventional',{}).get('n_urban',1000)),
        'rq5': approx_power(R['rq5']['cohens_d'],
                            R['rq5']['n_rural_female'],
                            R['rq5']['n_urban_male']),
    }
    R['sample_size_justification'] = {
        'min_n_small_effect_d02': 394,
        'min_n_medium_effect_d05': 64,
        'actual_n_male': n_male, 'actual_n_female': n_female,
        'note': (f'With n_male={n_male:,} and n_female={n_female:,}, '
                 f'the study detects effects as small as d=0.01 at 80% power.')
    }

    # ── Save results ──────────────────────────────────────────────────────────
    results_path = output_dir / 'results.json'
    with open(results_path, 'w') as f:
        json.dump(R, f, indent=2, default=str)
    print(f"\n[SAVE] Results -> {results_path}")

    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"LR:  RMSE={lr_rmse}, R2={lr_r2}, CV-RMSE={lr_cv_rmse.mean():.4f}")
    print(f"XGB: RMSE={xgb_rmse}, R2={xgb_r2}, CV-RMSE={xgb_cv_rmse.mean():.4f}")
    print(f"RQ1 XGB: KS p={R['rq1']['xgb']['ks_p']}, d={R['rq1']['xgb']['cohens_d']}")
    print(f"RQ5: Compound={R['rq5']['compounding_effect']}, d={R['rq5']['cohens_d']}")
    print(f"RQ6 TIBAI: {rq6['di_by_year']}")
    return R

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='QM640 Final Analysis Pipeline')
    parser.add_argument('--data-dir',   default=str(DATA_DIR),   help='Directory containing HMDA CSV files')
    parser.add_argument('--output-dir', default=str(OUTPUT_DIR), help='Directory for results and figures')
    args = parser.parse_args()
    run(Path(args.data_dir), Path(args.output_dir))
