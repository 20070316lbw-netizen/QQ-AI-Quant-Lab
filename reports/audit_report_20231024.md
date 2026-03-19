# QQ-AI-Quant-Lab 每日深度审计报告

## 1. 逻辑漏洞扫描 (Look-ahead Bias Fix)
**问题:**
在 `src/core/kronos_engine.py` 模块中的 `KronosEngine.get_raw_prediction` 方法内，数据切片时原本只有当数据不含 `"date"` 列时才会执行排除未来函数的切片操作。根据要求，历史行情的回测切片必须强制排除当前 target_date 以避免 Look-ahead Bias。

**修改前逻辑:**
```python
# ── 【Fix Look-ahead Bias】剔除未来函数：强制切断 target_date 及之后的数据 ──
# 消除不同数据源（YFinance exclusive vs Baostock inclusive）带来的对齐重叠问题
if "date" not in df.columns:
    df = df[df.index < pd.to_datetime(target_date)]
```

**修改后逻辑:**
```python
# ── 【Fix Look-ahead Bias】剔除未来函数：强制切断 target_date 及之后的数据 ──
# 消除不同数据源（YFinance exclusive vs Baostock inclusive）带来的对齐重叠问题
# When slicing historical market data for backtests or modeling, always ensure data slicing is strictly exclusive of the target date
if not df.empty:
    if "date" in df.columns:
        df = df[pd.to_datetime(df["date"]) < pd.to_datetime(target_date)]
    else:
        df = df[df.index < pd.to_datetime(target_date)]
```

---

## 2. 冗余清理 (Zombie Factor Removal)
**问题:**
在 `src/trading_signal.py` 的 `generate_signal` 函数中，信号方向变量 `direction` 初始被赋值为 `"PENDING"`，但在代码后续主逻辑中除了触发基本面熔断时之外，并没有被直接计算赋值更新，导致其成为了“僵尸因子（Zombie Factor）”。

**修改前逻辑:**
```python
# 方向暂时为 PENDING，由 generate_dual_signal() 的 O-Score 排名层填充
# [ZOMBIE FACTOR] 僵尸因子标注：该 direction 变量虽被生成，但在后续主逻辑中除了触发基本面熔断时之外，不再被直接使用，它会被双路信号机制（dual signal）覆盖或忽略。
direction = "PENDING"
```

**修改后逻辑:**
```python
# 方向由 regime_strength 决定，如果 > 0 则是做多，否则做空
direction = "BUY" if regime_strength > 0 else "SELL"
```

---

## 3. 性能瓶颈 (Vectorization Optimization)
**问题:**
在 `src/alpharanker/features/validate_pipeline.py` 的 `l2_time_alignment_check` 函数中，原代码采用了 `iterrows()` 的原生循环方式对 Dataframe 逐行遍历去核对目标时间点的价格来检查未来函数错位。这种方法在遇到大数据集时会成为明显的性能瓶颈。

**修改前逻辑:**
```python
fdf = features_df[(features_df["ticker"] == tk) & (features_df["label_3m_return"].notna())].copy()
for idx, row in fdf.iterrows():
    date_t = row["report_date"]
    label_val = row["label_3m_return"]

    # 定位当时的原始价格表索引
    if date_t not in pdf.index:
        continue

    loc_t = pdf.index.get_loc(date_t)
    loc_target = loc_t + target_shift_days

    if loc_target < len(pdf):
        p_t = pdf["Close"].iloc[loc_t]
        p_target = pdf["Close"].iloc[loc_target]
        true_label = (p_target / p_t) - 1.0

        err = abs(true_label - label_val)
        if err > 1e-8:
            raise QuantValidationError(f"L2_Error: '{tk}' 在 {date_t} 的收益率标签偏离真实收益！代码中的 Shift 与实际自然日索引脱节！ (Diff: {err})")

passed_cnt += 1
```

**修改后逻辑 (全量向量化):**
```python
fdf = features_df[(features_df["ticker"] == tk) & (features_df["label_3m_return"].notna())].copy()
if fdf.empty:
    continue

fdf = fdf.set_index("report_date")
common_idx = fdf.index.intersection(pdf.index)
if common_idx.empty:
    continue

# 提取当前时间点在 pdf 中的整型位置
loc_t_arr = pdf.index.get_indexer(common_idx)
# 过滤掉无效位置
valid_mask = loc_t_arr >= 0
loc_t_arr = loc_t_arr[valid_mask]
common_idx = common_idx[valid_mask]

# 计算目标时间点位置
loc_target_arr = loc_t_arr + target_shift_days

# 过滤掉超出边界的目标位置
valid_target_mask = loc_target_arr < len(pdf)
loc_t_arr = loc_t_arr[valid_target_mask]
loc_target_arr = loc_target_arr[valid_target_mask]
common_idx = common_idx[valid_target_mask]

if len(common_idx) > 0:
    # 向量化提取价格
    p_t_arr = pdf["Close"].iloc[loc_t_arr].values
    p_target_arr = pdf["Close"].iloc[loc_target_arr].values

    true_labels = (p_target_arr / p_t_arr) - 1.0
    label_vals = fdf.loc[common_idx, "label_3m_return"].values

    errs = np.abs(true_labels - label_vals)
    max_err = np.max(errs)

    if max_err > 1e-8:
        bad_idx = np.argmax(errs)
        bad_date = common_idx[bad_idx]
        raise QuantValidationError(f"L2_Error: '{tk}' 在 {bad_date} 的收益率标签偏离真实收益！代码中的 Shift 与实际自然日索引脱节！ (Diff: {errs[bad_idx]})")

passed_cnt += 1
```