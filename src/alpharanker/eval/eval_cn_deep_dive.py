import os
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import CN_DIR

FEATURES_PATH = os.path.join(CN_DIR, 'cn_features_enhanced.parquet')
INDEX_MAP_PATH = os.path.join(CN_DIR, 'index_map.parquet')

def calculate_ic_series(df, factor, target):
    ics = []
    dates = sorted(df["date"].unique())
    for d in dates:
        grp = df[df["date"] == d]
        if len(grp) > 20:
            ic, _ = spearmanr(grp[factor], grp[target])
            ics.append((d, ic))
    return pd.Series(dict(ics))

def get_newey_west_t(series):
    if len(series) < 2: return np.nan
    # Newey-West t-stat for the mean, usage: regression on constant
    y = series.values
    X = np.ones(len(y))
    model = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': min(len(y)-1, 4)})
    return model.tvalues[0]

def main():
    print("="*80)
    print("  Alpha Genome: A 股基因深度科学论证 (Deep Dive)")
    print("="*80)

    if not os.path.exists(FEATURES_PATH) or not os.path.exists(INDEX_MAP_PATH):
        print("❌ 缺少数据。")
        return

    df = pd.read_parquet(FEATURES_PATH)
    index_map = pd.read_parquet(INDEX_MAP_PATH)
    
    # Baostock code in index_map is 'sh.600000', in features it's '600000.SS'
    # Let's normalize ticker format
    index_map['ticker'] = index_map['code'].str.split(".").str[1] + np.where(index_map['code'].str.startswith("sh"), ".SS", ".SZ")
    
    df = pd.merge(df, index_map[['ticker', 'index_group']], on='ticker', how='left')
    df['index_group'] = df['index_group'].fillna('Other')
    
    factors = ["mom_60d_rank", "mom_20d_rank", "vol_60d_res_rank", "sp_ratio_rank", "roe_rank"]
    target = "label_next_month"
    df = df.dropna(subset=[target])

    print(f"\n[实证区间]: {df['date'].min().date()} -> {df['date'].max().date()} ({len(df['date'].unique())} 个月度截面)")

    groups = ["HS300", "ZZ500"]
    all_results = []

    for group in groups:
        print(f"\n>> 正在分析样本池: {group} <<")
        g_df = df[df["index_group"] == group]
        
        for f in factors:
            ic_series = calculate_ic_series(g_df, f, target)
            mean_ic = ic_series.mean()
            std_ic = ic_series.std()
            t_stat = get_newey_west_t(ic_series)
            
            all_results.append({
                "Group": group,
                "Factor": f,
                "Mean IC": mean_ic,
                "NW t-stat": t_stat,
                "Positive%": (ic_series > 0).mean()
            })
            
            print(f" - {f:20}: IC={mean_ic:+.4f}, t-stat={t_stat:+.2f}")

    # --- ROE Lag Analysis ---
    print("\n" + "="*50)
    print(">> ROE (Quality) 因子滞后性归因分析 <<")
    # 测试将 ROE 滞后 3 个月 (约为一个季度披露时间)
    df_sorted = df.sort_values(['ticker', 'date'])
    df_sorted['roe_rank_lag3'] = df_sorted.groupby('ticker')['roe_rank'].shift(3)
    
    for group in groups:
        g_df = df_sorted[df_sorted["index_group"] == group].dropna(subset=['roe_rank_lag3'])
        ic_orig = calculate_ic_series(g_df, 'roe_rank', target).mean()
        ic_lag = calculate_ic_series(g_df, 'roe_rank_lag3', target).mean()
        print(f"[{group}] ROE (Original) IC: {ic_orig:+.4f} | ROE (Lag 3m) IC: {ic_lag:+.4f}")

    # Summary
    res_df = pd.DataFrame(all_results)
    print("\n" + "="*80)
    print("  深度验证总结表")
    print("="*80)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    main()
