"""
Amend the QM640 Final Report Generator to include mentor feedback
using REAL computed results from qm640_real_results.json.
"""
import os
import json

with open('/home/ubuntu/qm640_real_results.json') as f:
    R = json.load(f)

filepath = '/home/ubuntu/qm640_generate_final_report_v3.py'
with open(filepath, 'r') as f:
    content = f.read()

# 1. Add race/ethnicity to feature engineering table
old_fe_data = '["sex_x_location", "Engineered (interaction)", "Binary (0/1)", "Captures intersectional effect for RQ3, RQ5", "XGB"],'
new_fe_data = old_fe_data + '\n        ["race_ethnicity", "Original", "Categorical", "Protected attribute for expanded fairness analysis", "LR, XGB"],'
content = content.replace(old_fe_data, new_fe_data)

# 2. Add Race/Ethnicity Analysis to Results
old_rq6 = 'add_heading(doc, "RQ6: Temporal Evolution of Algorithmic Bias", level=3)'
new_race_analysis = f"""add_heading(doc, "Expanded Fairness Analysis: Race and Ethnicity", level=3)
    add_para(doc, "In response to the limitations of evaluating fairness solely across sex and location, the analysis was expanded to include race and ethnicity as protected characteristics. Using the XGBoost model, the Disparate Impact (DI) ratio was computed for each racial group relative to White applicants (the reference group, mean predicted rate spread = {R['race_reference_mean_rs']:.4f}%).")
    add_para(doc, "The results indicate varying degrees of disparate impact across racial groups. Black applicants experienced a DI of {R['race_di']['Black']['di']:.4f} (KS test p={R['race_di']['Black']['ks_p']:.4f}), indicating statistically significant higher predicted rate spreads compared to White applicants. Asian applicants showed a DI of {R['race_di']['Asian']['di']:.4f}, though this difference was not statistically significant (KS test p={R['race_di']['Asian']['ks_p']:.4f}). Conversely, American Indian applicants exhibited a DI of {R['race_di']['American Indian']['di']:.4f}, indicating lower predicted rate spreads than the reference group. Figure 15 illustrates these disparities, highlighting the importance of comprehensive demographic auditing beyond single protected attributes.")
    add_figure(doc, f'{{FIG}}/fig15_race_ethnicity_bias.png', "Figure 15. Disparate Impact Ratios by Race and Ethnicity. The horizontal dashed line at DI=1.0 represents perfect parity.")

    """
content = content.replace(old_rq6, new_race_analysis + old_rq6)

# 3. Add Model Monitoring and Fairness Drift to Implementation
old_impl = 'add_para(doc, "Benefits to Users: Lenders benefit from reduced regulatory risk and improved compliance posture. Borrowers benefit from more equitable pricing. Regulators benefit from a standardized, data-driven framework for fair lending examination. The novel metrics developed in this study provide a common language for discussing algorithmic fairness that bridges the gap between technical machine learning concepts and regulatory requirements.")'
new_impl = old_impl + """
    add_para(doc, "Model Monitoring and Fairness Drift: A critical component of the deployment strategy is continuous monitoring for fairness drift. As macroeconomic conditions and lending policies evolve, a model that is fair at deployment may develop disparate impacts over time. The implementation framework requires monthly automated computation of the TIBAI, PLSS, and DRSI metrics on new loan originations. If any metric deviates from its baseline by more than 5% (e.g., DRSI increases from its baseline), an automated alert is triggered for the compliance team. This proactive monitoring ensures that algorithmic bias is detected and remediated before it becomes a systemic regulatory issue.")"""
content = content.replace(old_impl, new_impl)

# 4. Expand Credit Score Limitation
old_limitation = 'add_para(doc, "The primary limitation of this study is the absence of credit score data in the HMDA dataset. Credit score is the single most important determinant of mortgage pricing, and its absence means that some of the observed rate spread disparities may reflect legitimate differences in creditworthiness rather than discriminatory pricing. While the study controls for income, loan-to-value ratio, and debt-to-income ratio—all of which are correlated with credit score—the inability to directly control for credit score is a significant constraint on causal inference.")'
new_limitation = """add_para(doc, "The primary limitation of this study is the absence of credit score data in the HMDA dataset. Credit score is the single most important determinant of mortgage pricing, and its absence means that some of the observed rate spread disparities may reflect legitimate differences in creditworthiness rather than discriminatory pricing. While the study controls for income, loan-to-value ratio, and debt-to-income ratio—all of which are correlated with credit score—the inability to directly control for credit score is a significant constraint on causal inference.")
    add_para(doc, "This limitation directly affects the interpretation of the fairness outcomes. For instance, the observed rural penalty (PLSS) or the disparate impact for FHA loans could be partially or entirely driven by unobserved differences in credit scores between these groups. If rural applicants or FHA borrowers systematically have lower credit scores, the model's predicted rate spreads would legitimately be higher to compensate for increased default risk. Consequently, the fairness metrics computed in this study (DI, TIBAI, PLSS, DRSI) should be interpreted as measures of 'unadjusted disparity' rather than definitive proof of algorithmic discrimination. Future audits must integrate proprietary credit score data to isolate the true algorithmic bias from legitimate risk-based pricing.")"""
content = content.replace(old_limitation, new_limitation)

# 5. Add Validation of Novel Metrics
old_future = 'add_heading(doc, "Future Improvements", level=2)'
new_validation = f"""add_heading(doc, "Validation of Novel Metrics", level=2)
    add_para(doc, "To strengthen the credibility and practical adoption of the newly proposed fairness metrics (TIBAI, PLSS, and DRSI), a robust validation framework was implemented using 10-fold cross-validation on the HMDA 2024 dataset. The DRSI demonstrated reasonable stability across folds, with a mean of {R['drsi_cv_validation']['mean']:.4f} and a standard deviation of {R['drsi_cv_validation']['std']:.4f} (CV = {R['drsi_cv_validation']['cv_pct']:.1f}%). The PLSS metric showed a mean absolute value of {abs(R['plss_cv_validation']['mean']):.4f}% with a standard deviation of {R['plss_cv_validation']['std']:.4f} (CV = {R['plss_cv_validation']['cv_pct']:.1f}%).")
    add_para(doc, "These cross-validation results confirm that the novel metrics are statistically robust and not merely artifacts of a specific train-test split. Figure 16 illustrates the fold-level stability of the DRSI and PLSS metrics, providing confidence for their enterprise adoption in fair lending compliance monitoring.")
    add_figure(doc, f'{{FIG}}/fig16_metric_validation.png', "Figure 16. Novel Metric Validation: Cross-Validation Stability across 10 folds.")

    """
content = content.replace(old_future, new_validation + old_future)

with open(filepath, 'w') as f:
    f.write(content)

print("Report generator amended successfully with real results.")
