# QM640 Final Presentation: Acronyms & Talking Points

## Part 1: Acronyms & Definitions

| Acronym | Full Term | Definition |
|---|---|---|
| **HMDA** | Home Mortgage Disclosure Act | A federal law requiring lenders to report public loan data to monitor fair lending. |
| **FFIEC** | Federal Financial Institutions Examination Council | The interagency body that publishes the HMDA data. |
| **CFPB** | Consumer Financial Protection Bureau | The primary federal regulator enforcing fair lending laws. |
| **APR** | Annual Percentage Rate | The total cost of borrowing, including interest and fees. |
| **APOR** | Average Prime Offer Rate | The baseline market interest rate for highly qualified borrowers. |
| **Rate Spread** | APR minus APOR | The target variable of this study. A higher rate spread means the borrower was charged a premium above the market baseline. |
| **LTV** | Loan-to-Value Ratio | The loan amount divided by the property value. A key risk metric. |
| **DTI** | Debt-to-Income Ratio | The borrower's monthly debt payments divided by their gross monthly income. |
| **FHA** | Federal Housing Administration | A government agency that insures loans for lower-income or lower-credit borrowers. |
| **VA** | Veterans Affairs | A government agency that guarantees loans for military veterans. |
| **USDA/RHS** | Rural Housing Service | A government agency that guarantees loans for rural borrowers. |
| **LR** | Linear Regression | The baseline statistical model used in this study. |
| **XGBoost** | Extreme Gradient Boosting | The advanced machine learning model used in this study. |
| **RMSE** | Root Mean Squared Error | A measure of model accuracy. Lower is better. |
| **CV-RMSE** | Cross-Validated RMSE | The RMSE calculated across 5 different folds of data to prove the model doesn't overfit. |
| **DI** | Disparate Impact Ratio | A fairness metric comparing the approval rate (or favorable pricing rate) of a protected class vs. a privileged class. Perfect fairness = 1.0. CFPB threshold = 0.8. |
| **DPD** | Demographic Parity Difference | The absolute difference in outcomes between two groups. |
| **KS Test** | Kolmogorov-Smirnov Test | A statistical test that checks if two distributions (e.g., male vs. female errors) are significantly different. |
| **TIBAI** | Temporal Intersectional Bias Amplification Index | **Novel Metric (Munyai, 2026):** Tracks how bias changes over time across economic cycles. |
| **PLSS** | Proxy Leakage Sensitivity Score | **Novel Metric (Munyai, 2026):** Measures exactly how much a model relies on sensitive features (like sex) as a proxy for other variables. |
| **DRSI** | Differential Residual Skewness Index | **Novel Metric (Munyai, 2026):** Measures whether a model's errors are symmetric across demographic groups. |

---

## Part 2: Slide-by-Slide Talking Points

*Note: These talking points are written for a high-stakeholder audience (executives, regulators, board members). They focus on the "so what" rather than just reading the slides.*

### Slide 1: Title Slide
**Talking Point:** "Good morning. My name is Tsumbo Munyai, and today I am presenting my Capstone research on Algorithmic Fairness in Mortgage Lending. Over the past few months, under the guidance of my mentor, I have analyzed over 10 million mortgage records to answer a critical question: Are modern algorithmic pricing models systematically overcharging protected demographic groups?"

### Slide 2: Executive Summary
**Talking Point:** "If you take away one thing from this presentation, let it be this: Algorithmic bias in mortgage pricing is real, but it is not uniform. Our analysis of 360,000 clean records proves that advanced models like XGBoost are highly accurate, but they systematically disadvantage rural and female applicants. Most concerningly, we found that government-backed FHA loans—which are designed to help vulnerable borrowers—actually show the highest rural penalty. Furthermore, we mathematically proved an intersectional compounding effect: being a rural female applicant carries a penalty greater than the sum of its parts."

### Slide 3: Gap Analysis
**Talking Point:** "Why does this research matter? Because the current fair lending literature has three massive blind spots. First, temporal blindness: regulators look at single years, missing how bias changes when interest rates spike. Second, binary focus: regulators focus on who gets approved, ignoring the subtle bias in *what rate they are charged*. Third, proxy leakage: everyone talks about models using zip codes as a proxy for race or gender, but no one quantifies it. My research introduces three novel metrics—TIBAI, DRSI, and PLSS—to solve these exact gaps."

### Slide 4: Research Questions
**Talking Point:** "We tested six formal hypotheses using rigorous statistical methods. I won't read every row, but notice the decisions on the right. We rejected the null hypothesis for location bias, Pareto-optimality, and intersectional compounding. This means the biases we found are not statistical noise—they are mathematically proven realities in the 2024 mortgage market."

### Slide 5: Data Description and EDA
**Talking Point:** "This is not a toy dataset. We ingested 40 million raw HMDA records from the federal government. To ensure our results were statistically sound without overpowering the p-values, we used a stratified random sample of 120,000 records per year. A formal power analysis confirms this gives us 100% statistical power. The exploratory data alone reveals a stark reality: rural applicants pay an average premium of nearly 9 basis points compared to urban applicants with similar profiles."

### Slide 6: Architecture Diagram / Workflow
**Talking Point:** "To ensure this research is world-class and fully reproducible, we built an eight-stage automated pipeline in Python. It handles everything from raw data ingestion to cross-validation and fairness evaluation. This isn't just a one-off study; it is a deployable software framework that a bank or regulator could run tomorrow on their own data."

### Slide 7: Model Building
**Talking Point:** "We compared a standard Linear Regression against an advanced XGBoost model. The results are night and day. XGBoost captures 52% of the variance in rate spreads, compared to just 22% for linear regression. We used 5-fold cross-validation to prove the model isn't overfitting. Interestingly, the model relies heavily on legitimate factors like Loan Amount and Income. Sensitive features like Sex and Location rank at the bottom, which tells us the bias isn't coming from direct discrimination, but from complex interactions deep within the algorithm."

### Slide 8: Results
**Talking Point:** "Here is where the data gets alarming. Look at RQ2: FHA loans show a Disparate Impact ratio of 1.07 against rural borrowers. That is a statistically significant penalty on a government-insured loan. Look at RQ5: The intersectional compounding effect. A rural female applicant doesn't just pay the rural penalty plus the female penalty—the algorithm penalizes the *combination* of those traits by an additional $700 over the life of a standard mortgage. Finally, our temporal analysis shows that fairness actually worsened significantly during the 2023 interest rate shock."

### Slide 9: Implementation and User Benefit
**Talking Point:** "This research isn't just academic; it's actionable. We are delivering three novel metrics that regulators like the CFPB or bank compliance officers can use today. The TIBAI dashboard can track bias across economic cycles. The PLSS tool can audit models for proxy leakage before they are deployed. And the DRSI metric can serve as a fairness certification standard. All the code to do this is open-source and available on GitHub right now."

### Slide 10: Conclusion
**Talking Point:** "In conclusion, we have proven that while machine learning can price mortgages with incredible accuracy, it requires active fairness constraints. We acknowledge limitations—we don't have FICO scores, so some of this disparity may reflect legitimate credit risk. However, the framework we've built stands. Our future work will involve partnering with lenders to ingest proprietary credit data and building a real-time regulatory dashboard."

### Slide 11: Bibliography
**Talking Point:** "Our methodology is grounded in the latest 2024 and 2025 literature on algorithmic fairness, ensuring this Capstone represents the cutting edge of data analytics in financial services. Thank you for your time, and I welcome any questions."
