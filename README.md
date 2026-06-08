# 📈 Macro Model
### Cross-Country Macroeconomic Analysis — India, Singapore, United Kingdom

Python codebase for the empirical analysis in Gokhale (2026), documenting an asymmetric Granger causality chain running India → Singapore → UK in CPI inflation.

## What this code does
- Constructs multi-source monthly CPI datasets (RBI DBIE, SingStat, ONS)
- Runs VAR(2) models with Cholesky impulse response functions
- Tests pairwise Granger causality across all country pairs
- Johansen cointegration testing
- Diebold-Mariano out-of-sample forecast accuracy testing
- Markov-switching regime detection
- Extended VAR projection to December 2026

## Key finding
India's CPI Granger-causes Singapore's with a two-month lag (p = 0.028). Singapore's Granger-causes the UK's (p = 0.039). Neither reverse direction is significant. The transmission chain runs upstream to downstream — east to west.

## Technical stack
- Python (Statsmodels, Pandas, NumPy, Scipy)
- Stata (supplementary analysis)

## Research output
Gokhale, A.A. (2026). *Cross-Country Macroeconomic Dynamics: Inflation, Growth, and Monetary Policy — India, Singapore, and the United Kingdom.* SSRN Working Paper. [ssrn.com/abstract=6514338](https://ssrn.com/abstract=6514338)

---
*Anuja A. Gokhale · MA Applied Economics, NUS (Merit Scholar) · anujagokhale1604@gmail.com*
