# HMDA 2024 Data Dictionary

**Source:** CFPB / FFIEC — Home Mortgage Disclosure Act Loan Application Register  
**URL:** https://ffiec.cfpb.gov/data-publication/2024  
**Records Used:** 1,839,520 originated loans with valid rate spread

---

## Variables Used in This Study

| Variable | Type | Description | Values / Units |
|----------|------|-------------|----------------|
| `rate_spread` | Continuous | Difference between the loan's APR and the Average Prime Offer Rate (APOR) | Percentage points (%) |
| `applicant_sex` | Categorical | Sex of the primary applicant as reported | 1=Male, 2=Female, 3=Not provided, 4=Not applicable |
| `income` | Continuous | Gross annual income of the applicant used in underwriting | Thousands of USD |
| `loan_amount` | Continuous | Amount of the loan applied for | Thousands of USD |
| `loan_type` | Categorical | Type of loan | 1=Conventional, 2=FHA-insured, 3=VA-guaranteed, 4=USDA/RHS |
| `loan_purpose` | Categorical | Purpose of the loan | 1=Home purchase, 2=Home improvement, 31=Refinancing, 32=Cash-out refinancing |
| `combined_loan_to_value_ratio` | Continuous | Ratio of total loan amount to property value | Percentage (%) |
| `loan_term` | Continuous | Length of the loan | Months |
| `debt_to_income_ratio` | Categorical/Continuous | Ratio of total monthly debt payments to gross monthly income | Ranges: <20%, 20%-<30%, ..., >60% |
| `property_value` | Continuous | Value of the property securing the loan | Thousands of USD |
| `tract_population` | Continuous | Total population of the census tract | Count |
| `tract_minority_population_percent` | Continuous | Percentage of minority residents in the census tract | Percentage (%) |

---

## Derived / Encoded Variables

| Variable | Description | Encoding |
|----------|-------------|----------|
| `sex_encoded` | Binary encoding of applicant sex | 0=Male, 1=Female |
| `location_encoded` | Rural/Urban classification based on tract population | 0=Urban (≥ median), 1=Rural (< median) |
| `dti_numeric` | Numeric conversion of DTI ratio categories | Midpoint of each range (e.g., 20%-<30% → 25) |

---

## Data Cleaning Steps

1. Retained only **originated loans** (action_taken = 1)
2. Removed records with missing or non-positive `rate_spread`
3. Restricted `applicant_sex` to Male (1) and Female (2) only
4. Clipped `income`, `loan_amount`, and `combined_loan_to_value_ratio` to 1st–99th percentile
5. Clipped `rate_spread` to 0.5th–99.5th percentile (range: 0.008% to 5.4%) to remove extreme outliers
6. Dropped rows with any remaining missing values in the feature set

**Final clean dataset:** 486,288 records (from 1,839,520 raw records)

---

## Notes

- The raw HMDA 2024 LAR CSV file is approximately **2.5 GB** and is excluded from this repository.
- Download from: https://ffiec.cfpb.gov/data-publication/2024
- Place the file at `data/2024_public_lar_csv.csv` before running any pipeline scripts.
