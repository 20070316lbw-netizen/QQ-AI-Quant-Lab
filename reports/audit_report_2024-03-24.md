# QQ-AI-Quant-Lab Daily Deep Audit Report
**Date:** 2024-03-24

## 1. Look-ahead Bias Remediation (Future Function Fix)
**Issue:** `src/core/multi_factor/factor_extractor.py` calculated the 6-month momentum factor using `t.history(period="6mo")`, which implicitly fetched data up to the current real-world date, even if the system was simulating a historical `target_date`. This caused future data leakage (look-ahead bias) during historical backtesting or specific past-date signal generation.

**Fix:**
Modified `extract_raw_factors` to accept an `as_of_date` parameter.
*Before:*
```python
hist = t.history(period="6mo")
```
*After:*
```python
if as_of_date:
    start_dt = pd.to_datetime(as_of_date) - pd.DateOffset(months=6)
    hist = t.history(start=start_dt.strftime("%Y-%m-%d"), end=as_of_date)
else:
    hist = t.history(period="6mo")
```
Propagated `as_of_date` via `src/core/factor_engine.py` and `src/trading_signal.py` to ensure it's securely passed down to the `extract_raw_factors` call.

## 2. Zombie Factors Cleanup
**Issue:** `current_price` was extracted from `yfinance` into `factors["meta"]["price"]` in `src/core/multi_factor/factor_extractor.py`, but it was never used by `src/core/multi_factor/scoring_engine.py` or any downstream logic. This consumed unnecessary I/O and memory.

**Fix:** Completely removed the `current_price` fetch logic and `factors["meta"]["price"]` assignment from `factor_extractor.py`.
*Before:*
```python
current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
factors["meta"]["price"] = current_price
```
*After:* (Removed completely)

## 3. Performance Bottlenecks Vectorization
**Issue:** Multiple locations used highly inefficient native Python loops (`iterrows()` or `.apply(lambda)`) to manipulate Pandas DataFrames.

**Fixes:**
- **tui_app.py:** Converted `iterrows()` to `itertuples()` for UI rendering loops, modifying dictionary accesses to tuple dot-notation.
- **yuan_500_assistant.py:** Converted `iterrows()` to `itertuples()`.
- **evaluation scripts (`eval_cn_ic_decay.py`, etc):** Vectorized a string manipulation lambda function.
*Before:*
```python
index_map['ticker'] = index_map['code'].apply(lambda x: x.split(".")[1] + (".SS" if x.startswith("sh") else ".SZ"))
```
*After:*
```python
import numpy as np
index_map['ticker'] = index_map['code'].str.split(".").str[1] + np.where(index_map['code'].str.startswith("sh"), ".SS", ".SZ")
```
This massively speeds up dataframe processing for large arrays of data.
