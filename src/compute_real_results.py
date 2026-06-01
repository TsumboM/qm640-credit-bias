"""
Compute REAL race/ethnicity Disparate Impact ratios and novel metric validation
from actual HMDA 2024 data downloaded from CFPB.
- Michigan data (urban-heavy) for race/ethnicity DI
- Rural states (WV, MT, WY, SD, ND, ME, VT) for location/PLSS analysis
- Combined dataset for full model training
All results saved to /home/ubuntu/qm640_real_results.json
"""
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.model_selection import train_test_split, KFold
import xgboost as xgb
import json, warnings
warnings.filterwarnings('ignore')

# ─── Load and combine data ────────────────────────────────────────────────────
print("Loading HMDA 2024 data...")
df_mi = pd.read_csv('/home/ubuntu/hmda_2024_sample.csv', low_memory=False)
df_ru = pd.read_csv('/home/ubuntu/hmda_2024_rural.csv', low_memory=False)
df_raw = pd.concat([df_mi, df_ru], ignore_index=True)
print(f"  Combined raw records: {len(df_raw):,}")

# ─── Clean ────────────────────────────────────────────────────────────────────
df = df_raw[df_raw['action_taken'] == 1].copy()
df['rate_spread'] = pd.to_numeric(df['rate_spread'], errors='coerce')
df = df.dropna(subset=['rate_spread'])
df = df[df['rate_spread'] > 0]
df['income'] = pd.to_numeric(df['income'], errors='coerce')
df['loan_amount'] = pd.to_numeric(df['loan_amount'], errors='coerce')
df = df.dropna(subset=['income', 'loan_amount'])
df = df[(df['income'] > 0) & (df['income'] <= 5000)]
df = df[df['loan_amount'] > 0]
df['dti_numeric'] = pd.to_numeric(df['debt_to_income_ratio'], errors='coerce')
df = df.dropna(subset=['dti_numeric'])
df = df[df['dti_numeric'] <= 65]
df['ltv_numeric'] = pd.to_numeric(df['loan_to_value_ratio'], errors='coerce')
df = df.dropna(subset=['ltv_numeric'])
df['loan_term'] = pd.to_numeric(df['loan_term'], errors='coerce')
df = df.dropna(subset=['loan_term'])
df = df[df['rate_spread'] <= 10]
print(f"  Clean records: {len(df):,}")

# ─── Encode sex ───────────────────────────────────────────────────────────────
df['sex_clean'] = df['applicant_sex'].map({1: 'Male', 2: 'Female', 6: 'Male', 7: 'Female'})
df = df.dropna(subset=['sex_clean'])
df['sex_encoded'] = (df['sex_clean'] == 'Female').astype(int)

# ─── Encode location ─────────────────────────────────────────────────────────
# derived_msa-md: 99999 = non-MSA (rural), any other numeric MSA code = urban
df['msa_numeric'] = pd.to_numeric(df['derived_msa-md'], errors='coerce')
df['location_encoded'] = (df['msa_numeric'] == 99999).astype(int)
print(f"  Urban: {(df['location_encoded']==0).sum():,}  Rural: {(df['location_encoded']==1).sum():,}")

# ─── Race map ─────────────────────────────────────────────────────────────────
race_map = {
    'White': 'White',
    'Black or African American': 'Black',
    'Asian': 'Asian',
    'American Indian or Alaska Native': 'American Indian',
    'Native Hawaiian or Other Pacific Islander': 'Pacific Islander',
    '2 or more minority races': 'Two or More',
    'Joint': 'Joint',
}
df['race_clean'] = df['derived_race'].map(race_map)

# ─── Feature engineering ──────────────────────────────────────────────────────
df['log_income'] = np.log1p(df['income'])
df['log_loan_amount'] = np.log1p(df['loan_amount'])
df['sex_x_location'] = df['sex_encoded'] * df['location_encoded']

FEATURES = ['sex_encoded', 'location_encoded', 'log_income', 'dti_numeric',
            'loan_term', 'ltv_numeric', 'log_loan_amount', 'sex_x_location']
TARGET = 'rate_spread'

df_model = df.dropna(subset=FEATURES + [TARGET])
X = df_model[FEATURES].values
y = df_model[TARGET].values
print(f"\nFinal model dataset: {len(df_model):,} records")
print(f"  Male: {(df_model['sex_clean']=='Male').sum():,}  Female: {(df_model['sex_clean']=='Female').sum():,}")
print(f"  Urban: {(df_model['location_encoded']==0).sum():,}  Rural: {(df_model['location_encoded']==1).sum():,}")

# ─── Train XGBoost model ──────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model_xgb = xgb.XGBRegressor(max_depth=8, n_estimators=100, learning_rate=0.1,
                               random_state=42, verbosity=0)
model_xgb.fit(X_train, y_train)
y_pred_test = model_xgb.predict(X_test)
rmse_xgb = float(np.sqrt(np.mean((y_pred_test - y_test)**2)))
r2_xgb = float(1 - np.sum((y_pred_test - y_test)**2) / np.sum((y_test - y_test.mean())**2))
print(f"\nXGBoost: RMSE={rmse_xgb:.4f}, R²={r2_xgb:.4f}")

# ─── Predict on full dataset ──────────────────────────────────────────────────
df_model = df_model.copy()
df_model['y_pred'] = model_xgb.predict(X)

# ─── Race/Ethnicity Disparate Impact ─────────────────────────────────────────
print("\n=== RACE/ETHNICITY DISPARATE IMPACT ===")
df_race = df_model.dropna(subset=['race_clean'])
ref_mean = float(df_race[df_race['race_clean'] == 'White']['y_pred'].mean())
print(f"Reference (White) mean predicted rate spread: {ref_mean:.4f}%")

race_di_results = {}
for race in ['Black', 'Asian', 'American Indian', 'Pacific Islander', 'Two or More']:
    grp = df_race[df_race['race_clean'] == race]
    if len(grp) < 30:
        print(f"  {race}: insufficient data (n={len(grp)}) — skipped")
        continue
    grp_mean = float(grp['y_pred'].mean())
    di = grp_mean / ref_mean if ref_mean > 0 else np.nan
    white_vals = df_race[df_race['race_clean'] == 'White']['y_pred'].values
    grp_vals = grp['y_pred'].values
    pooled_sd = float(np.sqrt((white_vals.std()**2 + grp_vals.std()**2) / 2))
    cohens_d = float((grp_mean - ref_mean) / pooled_sd) if pooled_sd > 0 else 0.0
    ks_stat, ks_p = stats.ks_2samp(grp_vals, white_vals)
    race_di_results[race] = {
        'n': int(len(grp)),
        'mean_pred_rs': round(grp_mean, 4),
        'di': round(float(di), 4),
        'cohens_d': round(cohens_d, 4),
        'ks_stat': round(float(ks_stat), 4),
        'ks_p': round(float(ks_p), 6),
    }
    sig = "p<0.05" if ks_p < 0.05 else "p≥0.05"
    print(f"  {race}: n={len(grp)}, mean_RS={grp_mean:.4f}, DI={di:.4f}, d={cohens_d:.4f}, KS {sig}")

# ─── PLSS ─────────────────────────────────────────────────────────────────────
print("\n=== PLSS COMPUTATION ===")
mean_rural_female = float(df_model[(df_model['sex_encoded']==1) & (df_model['location_encoded']==1)]['y_pred'].mean())
mean_urban_male   = float(df_model[(df_model['sex_encoded']==0) & (df_model['location_encoded']==0)]['y_pred'].mean())
mean_urban_female = float(df_model[(df_model['sex_encoded']==1) & (df_model['location_encoded']==0)]['y_pred'].mean())
mean_rural_male   = float(df_model[(df_model['sex_encoded']==0) & (df_model['location_encoded']==1)]['y_pred'].mean())
plss_total    = mean_rural_female - mean_urban_male
plss_sex      = mean_urban_female - mean_urban_male
plss_location = mean_rural_male   - mean_urban_male
plss_interaction = plss_total - plss_sex - plss_location
n_rural_female = int((df_model['sex_encoded']==1) & (df_model['location_encoded']==1)).sum() if False else int(len(df_model[(df_model['sex_encoded']==1) & (df_model['location_encoded']==1)]))
print(f"  n rural female: {n_rural_female}")
print(f"  PLSS (total):       {plss_total:.4f}%")
print(f"  PLSS_sex:           {plss_sex:.4f}%")
print(f"  PLSS_location:      {plss_location:.4f}%")
print(f"  PLSS_interaction:   {plss_interaction:.4f}%")

# Test significance of interaction
rf_vals = df_model[(df_model['sex_encoded']==1) & (df_model['location_encoded']==1)]['y_pred'].values
um_vals = df_model[(df_model['sex_encoded']==0) & (df_model['location_encoded']==0)]['y_pred'].values
if len(rf_vals) >= 30 and len(um_vals) >= 30:
    t_stat, t_p = stats.ttest_ind(rf_vals, um_vals)
    print(f"  t-test (rural female vs urban male): t={t_stat:.4f}, p={t_p:.4f}")
else:
    t_p = None
    print(f"  Insufficient rural female records for t-test (n={len(rf_vals)})")

# ─── DRSI ─────────────────────────────────────────────────────────────────────
print("\n=== DRSI COMPUTATION ===")
male_pred    = float(df_model[df_model['sex_encoded']==0]['y_pred'].mean())
female_pred  = float(df_model[df_model['sex_encoded']==1]['y_pred'].mean())
overall_pred = float(df_model['y_pred'].mean())
drsi_xgb = abs(female_pred - male_pred) / overall_pred
di_overall = female_pred / male_pred
print(f"  Male mean pred RS:    {male_pred:.4f}")
print(f"  Female mean pred RS:  {female_pred:.4f}")
print(f"  Overall mean pred RS: {overall_pred:.4f}")
print(f"  DRSI (XGBoost):       {drsi_xgb:.4f}")
print(f"  DI (Female/Male):     {di_overall:.4f}")

# ─── Cross-Validation of Novel Metrics ───────────────────────────────────────
print("\n=== NOVEL METRIC CROSS-VALIDATION (10-fold) ===")
kf = KFold(n_splits=10, shuffle=True, random_state=42)
drsi_folds, plss_folds, di_folds = [], [], []

for fold_i, (train_idx, val_idx) in enumerate(kf.split(X)):
    X_tr, X_val = X[train_idx], X[val_idx]
    y_tr = y[train_idx]
    m = xgb.XGBRegressor(max_depth=8, n_estimators=100, learning_rate=0.1,
                          random_state=42, verbosity=0)
    m.fit(X_tr, y_tr)
    y_pred_val = m.predict(X_val)
    
    df_val = df_model.iloc[val_idx].copy()
    df_val['y_pred_fold'] = y_pred_val
    
    # DRSI
    m_p = df_val[df_val['sex_encoded']==0]['y_pred_fold'].mean()
    f_p = df_val[df_val['sex_encoded']==1]['y_pred_fold'].mean()
    ov_p = df_val['y_pred_fold'].mean()
    drsi_f = abs(f_p - m_p) / ov_p if ov_p > 0 else np.nan
    drsi_folds.append(float(drsi_f))
    di_folds.append(float(f_p / m_p) if m_p > 0 else np.nan)
    
    # PLSS
    rf_p = df_val[(df_val['sex_encoded']==1) & (df_val['location_encoded']==1)]['y_pred_fold'].mean()
    um_p = df_val[(df_val['sex_encoded']==0) & (df_val['location_encoded']==0)]['y_pred_fold'].mean()
    plss_f = float(rf_p - um_p) if not (np.isnan(rf_p) or np.isnan(um_p)) else np.nan
    plss_folds.append(plss_f)

drsi_clean = [x for x in drsi_folds if not np.isnan(x)]
plss_clean = [x for x in plss_folds if not np.isnan(x)]
di_clean   = [x for x in di_folds if not np.isnan(x)]

drsi_mean = float(np.mean(drsi_clean))
drsi_std  = float(np.std(drsi_clean))
drsi_cv   = float(drsi_std / drsi_mean * 100) if drsi_mean != 0 else 0.0

plss_mean = float(np.mean(plss_clean)) if plss_clean else float('nan')
plss_std  = float(np.std(plss_clean)) if plss_clean else float('nan')
plss_cv   = float(abs(plss_std / plss_mean * 100)) if plss_clean and plss_mean != 0 else float('nan')

di_mean = float(np.mean(di_clean))
di_std  = float(np.std(di_clean))

print(f"  DRSI 10-fold: mean={drsi_mean:.4f}, std={drsi_std:.4f}, CV={drsi_cv:.1f}%")
print(f"  PLSS 10-fold: mean={plss_mean:.4f}, std={plss_std:.4f}, CV={plss_cv:.1f}% (n_folds={len(plss_clean)})")
print(f"  DI   10-fold: mean={di_mean:.4f}, std={di_std:.4f}")

# ─── Save results ─────────────────────────────────────────────────────────────
results = {
    'dataset': 'HMDA 2024 (Michigan + WV/MT/WY/SD/ND/ME/VT) from CFPB',
    'n_clean': int(len(df_model)),
    'n_urban': int((df_model['location_encoded']==0).sum()),
    'n_rural': int((df_model['location_encoded']==1).sum()),
    'n_male': int((df_model['sex_clean']=='Male').sum()),
    'n_female': int((df_model['sex_clean']=='Female').sum()),
    'model_xgb_rmse': round(rmse_xgb, 4),
    'model_xgb_r2': round(r2_xgb, 4),
    'race_di': race_di_results,
    'race_reference': 'White',
    'race_reference_mean_rs': round(ref_mean, 4),
    'plss_total': round(plss_total, 4),
    'plss_sex': round(plss_sex, 4),
    'plss_location': round(plss_location, 4),
    'plss_interaction': round(plss_interaction, 4),
    'n_rural_female': n_rural_female,
    'plss_ttest_p': round(float(t_p), 4) if t_p is not None else None,
    'drsi_xgb': round(drsi_xgb, 4),
    'di_overall': round(di_overall, 4),
    'drsi_cv_validation': {
        'folds': 10,
        'mean': round(drsi_mean, 4),
        'std': round(drsi_std, 4),
        'cv_pct': round(drsi_cv, 1),
    },
    'plss_cv_validation': {
        'folds': 10,
        'n_valid_folds': len(plss_clean),
        'mean': round(plss_mean, 4) if not np.isnan(plss_mean) else None,
        'std': round(plss_std, 4) if not np.isnan(plss_std) else None,
        'cv_pct': round(plss_cv, 1) if not np.isnan(plss_cv) else None,
    },
    'di_cv_validation': {
        'folds': 10,
        'mean': round(di_mean, 4),
        'std': round(di_std, 4),
    },
}

with open('/home/ubuntu/qm640_real_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n✓ Results saved to /home/ubuntu/qm640_real_results.json")
print(json.dumps(results, indent=2))
