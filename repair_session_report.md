# QQ-AI-Quant-Lab: 每日深度审计修复报告 (Daily Depth Audit & Repair Session)

**日期 / Date:** 2025-05-20 (Simulated)
**审计领域 / Scope:** Logic Vulnerabilities, Code Redundancy, Performance Bottlenecks

## 1. 逻辑漏洞：修复“未来函数” (Look-ahead Bias in `src/core/kronos_engine.py`)
- **漏洞描述:** 在回测或建模时截取历史市场数据，没有进行时区隔离。由于 `pd.to_datetime(target_date)` 生成的 `Timestamp` 默认无时区信息，若直接与可能带有当地时区信息（如通过 YFinance 获取）的 Pandas 日期索引进行比较会导致 `TypeError`，或者对不同交易所数据（Baostock 与 YFinance）产生边界时间重叠的 Look-ahead bias（未来函数渗透）。
- **修改对比:**
  *修改前:*
  ```python
  if "date" in df.columns:
      df = df[pd.to_datetime(df["date"]) < pd.to_datetime(target_date)]
  else:
      df = df[pd.to_datetime(df.index) < pd.to_datetime(target_date)]
  ```
  *修改后:*
  ```python
  target_dt_obj = pd.to_datetime(target_date)
  if "date" in df.columns:
      dt_col = pd.to_datetime(df["date"])
      if dt_col.dt.tz is not None:
          target_dt_obj = target_dt_obj.tz_localize(dt_col.dt.tz)
      df = df[dt_col < target_dt_obj]
  else:
      dt_idx = pd.to_datetime(df.index)
      if dt_idx.tz is not None:
          target_dt_obj = target_dt_obj.tz_localize(dt_idx.tz)
      df = df[dt_idx < target_dt_obj]
  ```

## 2. 冗余清理：剔除“僵尸因子” (Zombie Factor Cleanup in `src/trading_signal.py`)
- **冗余描述:** 发现系统中存在若干 LLM 情绪因子与风险因子的计算（`get_llm_adjustments`, `ext_sentiment`, `ext_risk`, `sentiment_score`, `risk_factor`）。它们虽然在 `generate_signal` 函数中被分配并在 `final_confidence` 与旧版 `metadata` 中计算保留，但其输出完全未被新的下游的双模块交易架构采用，占用执行计算、引入冗余。
- **修改对比:**
  *修改前:*
  ```python
  def get_llm_adjustments(ticker: str) -> Tuple[float, float]:
      return 0.0, 0.3

  def generate_signal(ticker: str, as_of_date: str = None, ext_sentiment: float = None, ext_risk: float = None) -> Dict[str, Any]:
      # ...
      default_sentiment, default_risk = get_llm_adjustments(ticker)
      sentiment_score = ext_sentiment if ext_sentiment is not None else default_sentiment
      risk_factor = ext_risk if ext_risk is not None else default_risk
      # ...
      final_confidence = max(0.0, min(1.0, kronos_position_cap * (1 + 0.3 * sentiment_score) * (1 - risk_factor)))
  ```
  *修改后:* 删除了 `get_llm_adjustments()` 函数定义及全部传参。
  ```python
  def generate_signal(ticker: str, as_of_date: str = None) -> Dict[str, Any]:
      # ...
      final_confidence = max(0.0, min(1.0, kronos_position_cap))
  ```

## 3. 性能瓶颈：向量化 Python 循环 (Vectorization in `src/alpharanker/data/fetch_industry.py`)
- **瓶颈描述:** 在进行股票代码映射时（将 `sh.600000` 映射到 `600000.SS`），系统使用了基于原生 Python 函数的 Pandas `.apply()` 方法循环调用转换逻辑。这在全A股（超过 5000 只股票）的操作中是非常慢的原生循环，可以被 Pandas 自带的纯粹底层 C 级字符串向量化方法取代。
- **修改对比:**
  *修改前:*
  ```python
  def _bs_to_std(bs_code: str) -> str:
      parts = bs_code.split(".")
      return f"{parts[1]}.{'SS' if parts[0] == 'sh' else 'SZ'}"
  # ...
  df["ticker"] = df["bs_code"].apply(_bs_to_std)
  ```
  *修改后:*
  ```python
  # 完全删除 _bs_to_std 定义
  # ...
  df["ticker"] = df["bs_code"].str.split(".").str[1] + "." + df["bs_code"].str.split(".").str[0].map({"sh": "SS", "sz": "SZ"})
  ```