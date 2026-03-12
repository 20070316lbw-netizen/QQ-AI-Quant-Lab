"""
build_us_features.py
=====================
【纯量价/技术面版本】
从 10 年美股日线价格中提取月度频率（月末）的纯技术面/量价因子，
构建用于 LightGBM LambdaRank 训练的面板数据集。

输出：
  data/us_features.parquet
    每行 = 一只股票在某个月末的特征快照
    columns: ticker, report_date (月末), <技术面特征>, label_3m_return, label_rank
"""

import os
import sys
import glob
import warnings
import numpy as np
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings("ignore")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import US_PRICE_DIR, US_FUND_DIR

OUTPUT_PATH = os.path.join(os.path.dirname(US_FUND_DIR), "us_features.parquet")
INFO_PATH = os.path.join(US_FUND_DIR, "us_stock_info.parquet")


# ─── 核心指标计算函数（基于 pd.Series/DataFrame 向量化）───────────────────

def calc_momentum(close_s: pd.Series, lookback: int) -> pd.Series:
    """收益率动量: (P_t / P_{t-lookback}) - 1"""
    return close_s / close_s.shift(lookback) - 1

def calc_volatility(close_s: pd.Series, lookback: int) -> pd.Series:
    """日收益率的历史波动率（年化）"""
    rets = close_s.pct_change()
    min_p = lookback // 2 if lookback > 20 else int(lookback * 0.8)
    return rets.rolling(window=lookback, min_periods=min_p).std() * np.sqrt(252)

def calc_ma_bias(close_s: pd.Series, lookback: int) -> pd.Series:
    """均线偏离度: P_t / MA_lookback - 1"""
    ma = close_s.rolling(window=lookback, min_periods=lookback//2).mean()
    return close_s / ma - 1

def calc_rsi(close_s: pd.Series, window: int = 14) -> pd.Series:
    """计算相对强弱指标 RSI"""
    delta = close_s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window//2).mean()
    avg_loss = loss.rolling(window=window, min_periods=window//2).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi[avg_loss == 0] = 100
    return rsi

def calc_macd(close_s: pd.Series, fast: int = 12, slow: int = 26, sign: int = 9) -> pd.DataFrame:
    """计算 MACD，返回包含 MACD_line, Signal_line, MACD_hist 的 df"""
    ema_fast = close_s.ewm(span=fast, adjust=False).mean()
    ema_slow = close_s.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=sign, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd_line": macd_line, "macd_signal": signal_line, "macd_hist": hist}, index=close_s.index)

def calc_bollinger_bands(close_s: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """计算布林带 bandwidth 和 %b"""
    ma = close_s.rolling(window=window, min_periods=window//2).mean()
    std = close_s.rolling(window=window, min_periods=window//2).std()
    upper = ma + (std * num_std)
    lower = ma - (std * num_std)
    # bandwidth = (Upper - Lower) / MA
    bandwidth = (upper - lower) / ma
    # %b = (Close - Lower) / (Upper - Lower)
    pct_b = (close_s - lower) / (upper - lower).replace(0, np.nan)
    return pd.DataFrame({"bb_width": bandwidth, "bb_pct_b": pct_b}, index=close_s.index)

def calc_volume_ratio(volume_s: pd.Series, short_w: int = 5, long_w: int = 60) -> pd.Series:
    """成交量异动比率 (短周期均量 / 长周期均量)"""
    vol_short = volume_s.rolling(window=short_w, min_periods=1).mean()
    vol_long = volume_s.rolling(window=long_w, min_periods=long_w//2).mean()
    return vol_short / vol_long.replace(0, np.nan)

def future_return(close_s: pd.Series, days: int = 63) -> pd.Series:
    """未来 N 个交易日的收益率标签"""
    future_p = close_s.shift(-days)
    return (future_p / close_s) - 1


# ─── 主特征提取逻辑 ──────────────────────────────────────────────────────────

def extract_features_for_ticker(ticker: str) -> pd.DataFrame:
    """对单只股票处理所有日线特征，并通过 resample 提取月末截面"""
    path = os.path.join(US_PRICE_DIR, f"{ticker}.parquet")
    if not os.path.exists(path):
        return pd.DataFrame()

    df = pd.read_parquet(path)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    required_cols = ["Close", "High", "Low", "Volume"]
    if not all(c in df.columns for c in required_cols):
        # 尝试容错读取小写列名
        required_cols = [c.capitalize() for c in required_cols]
    
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    if len(close) < 252: # 剔除上市不足一年的
        return pd.DataFrame()

    out = pd.DataFrame(index=df.index)
    out["ticker"] = ticker

    # 1. 动量趋势 (1M, 3M, 6M, 12M)
    out["mom_1m"] = calc_momentum(close, 21)
    out["mom_3m"] = calc_momentum(close, 63)
    out["mom_6m"] = calc_momentum(close, 126)
    out["mom_12m"] = calc_momentum(close, 252)

    # 4均线偏离度
    out["bias_20d"] = calc_ma_bias(close, 20)
    out["bias_60d"] = calc_ma_bias(close, 60)
    out["bias_120d"] = calc_ma_bias(close, 120)

    # 2. 波动类
    out["vol_20d"] = calc_volatility(close, 20)
    out["vol_60d"] = calc_volatility(close, 60)
    out["vol_120d"] = calc_volatility(close, 120)
    # 振幅：(High - Low) / Close 的 20 日均值
    out["amplitude_20d"] = ((high - low) / close).rolling(20, min_periods=10).mean()

    # 3. 技术指标
    out["rsi_14d"] = calc_rsi(close, 14)
    out["rsi_28d"] = calc_rsi(close, 28)
    
    macd_df = calc_macd(close)
    out["macd_line"] = macd_df["macd_line"]
    out["macd_signal"] = macd_df["macd_signal"]
    out["macd_hist"] = macd_df["macd_hist"]

    bb_df = calc_bollinger_bands(close)
    out["bb_width"] = bb_df["bb_width"]
    out["bb_pct_b"] = bb_df["bb_pct_b"]

    # 4. 量价配合
    out["vol_trend_5_60"] = calc_volume_ratio(vol, 5, 60)

    # 5. 标签 (未来 3 个月 63交易日 收益率)
    out["label_3m_return"] = future_return(close, 63)

    # ================= 采样至月频 (月末) =================
    # 获取实际交易日：按自然月分组，取该月最后一个实际存在的交易日
    out["year_month"] = out.index.to_period("M")
    # 找到每个月最后一个交易日
    last_trading_days = out.groupby("year_month").apply(lambda x: x.index[-1]).values
    
    out_monthly = out.loc[last_trading_days].copy()
    out_monthly["report_date"] = out_monthly.index
    out_monthly.drop(columns=["year_month"], inplace=True)
    
    # ================= 引入 EDGAR 深度基本面 (完美解决历史 NaN) =================
    edgar_path = os.path.join(US_FUND_DIR, "edgar", f"{ticker}_edgar.parquet")
    if os.path.exists(edgar_path):
        df_fund = pd.read_parquet(edgar_path)
        if not df_fund.empty:
            # 排除非数值或元数据列，计算基本衍生
            if 'Net Income' in df_fund.columns and 'Stockholders Equity' in df_fund.columns:
                df_fund['ROE'] = df_fund['Net Income'] * 4 / df_fund['Stockholders Equity'].replace(0, np.nan)
            if 'Net Income' in df_fund.columns and 'Total Revenue' in df_fund.columns:
                df_fund['Net_Margin'] = df_fund['Net Income'] / df_fund['Total Revenue'].replace(0, np.nan)
            
            # 提取核心财报列，计算同比增速 (YoY)
            fund_num_cols = df_fund.select_dtypes(include='number').columns
            for col in fund_num_cols:
                # pandas pct_change periods=4 刚好就是同季对比 YoY
                df_fund[f"{col}_YoY"] = df_fund[col].pct_change(periods=4)
                
            # 【核心：消除前视偏差】假设财季结束（End Date）后 60 天对外披露，我们将生效期往后推 2 个月
            # 即: 3-31 的一季报，在 5-31 及其之后的截面才能被模型使用
            df_fund.index = pd.to_datetime(df_fund.index) + pd.DateOffset(months=2)
            # 转换索引时间戳精度一致，避免 '<M8[ms]' 与 '<M8[us]' 冲突
            df_fund.index = pd.to_datetime(df_fund.index).astype('datetime64[ns]')
            out_monthly.index = pd.to_datetime(out_monthly.index).astype('datetime64[ns]')
            df_fund = df_fund.sort_index()

            # 将基本面长表合入月底量价面板 (向前寻找最近披露的一次财报)
            out_monthly = pd.merge_asof(
                out_monthly.sort_index(), 
                df_fund, 
                left_index=True, 
                right_index=True, 
                direction='backward'
            )
            # 丢弃 EDGAR 重复合并进来的 ticker 名
            if 'ticker_y' in out_monthly.columns:
                out_monthly.drop(columns=['ticker_y'], inplace=True)
            if 'ticker_x' in out_monthly.columns:
                out_monthly.rename(columns={'ticker_x': 'ticker'}, inplace=True)
            if 'form' in out_monthly.columns:
                out_monthly.drop(columns=['form'], inplace=True)
    
    feature_cols = [c for c in out_monthly.columns if c not in ["ticker", "report_date", "label_3m_return"]]
    # 放宽剔除条件，允许历史早期某些季度缺少基本面而存在 NaN
    out_monthly = out_monthly.dropna(subset=[c for c in feature_cols if not c.endswith('YoY')], how="all")
    
    return out_monthly.reset_index(drop=True)


# ─── 主函数 ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  AlphaRanker — 美股量价月频特征提取")
    print(f"  输出路径: {OUTPUT_PATH}")
    print("=" * 55)

    price_files = sorted(glob.glob(os.path.join(US_PRICE_DIR, "*.parquet")))
    tickers = [os.path.basename(f).replace(".parquet", "") for f in price_files]
    print(f"\n共 {len(tickers)} 只股票，开始提取特征...\n")

    all_dfs = []
    errors = []

    for ticker in tqdm(tickers, desc="提取月度特征"):
        try:
            df_t = extract_features_for_ticker(ticker)
            if not df_t.empty:
                all_dfs.append(df_t)
        except Exception as e:
            errors.append((ticker, str(e)))
            tqdm.write(f"  [ERR] {ticker}: {e}")

    if not all_dfs:
        print("❌ 没有提取到任何数据，请检查数据路径")
        return

    df = pd.concat(all_dfs, ignore_index=True)
    df["report_date"] = pd.to_datetime(df["report_date"])
    
    # 关联静态行业特征 (sector, industry)
    if os.path.exists(INFO_PATH):
        info_df = pd.read_parquet(INFO_PATH)[["ticker", "sector", "industry"]]
        df = df.merge(info_df, on="ticker", how="left")
        # 对行业做基础的特征化处理 (Categorical 供 LGBM 使用)
        df["sector"] = df["sector"].astype("category")
        df["industry"] = df["industry"].astype("category")

    # 排序并构建排名标签
    df = df.sort_values(["report_date", "ticker"]).reset_index(drop=True)
    df["label_rank"] = df.groupby("report_date")["label_3m_return"].rank(
        ascending=True, method="average", na_option="keep"
    )

    feature_cols = [c for c in df.columns if c not in ["ticker", "report_date", "label_3m_return", "label_rank"]]
    
    print(f"\n特征数量: {len(feature_cols)}")
    print(f"特征列表: {feature_cols}")
    print(f"\n总样本数: {len(df)}")
    print(f"截面数量: {df['report_date'].nunique()} 个月")
    print(f"覆盖股票: {df['ticker'].nunique()} 只")
    print(f"有效标签数: {df['label_3m_return'].notna().sum()}")
    print(f"失败股票: {len(errors)}")

    # 保存
    df.to_parquet(OUTPUT_PATH, compression="snappy", index=False)
    print(f"\n[DONE] 已保存至: {OUTPUT_PATH}")

    # 打印各特征缺失率
    print("\n各特征缺失率 (Top 10):")
    missing = df[feature_cols].isnull().mean().sort_values(ascending=False).head(10)
    for col, rate in missing.items():
        if rate > 0:
            print(f"  {col}: {rate:.1%}")

if __name__ == "__main__":
    main()
