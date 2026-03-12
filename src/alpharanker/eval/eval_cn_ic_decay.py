import os
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import statsmodels.api as sm

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
            mask = grp[[factor, target]].notna().all(axis=1)
            if mask.sum() > 10:
                ic, _ = spearmanr(grp.loc[mask, factor], grp.loc[mask, target])
                ics.append((d, ic))
    return pd.Series(dict(ics))

def get_newey_west_t(series):
    if len(series) < 5: return np.nan
    y = series.values
    X = np.ones(len(y))
    model = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': min(len(y)-1, 4)})
    return model.tvalues[0]

def main():
    print("="*80)
    print("  Alpha Genome: A 股基因时序衰减分析 (IC Decay)")
    print("="*80)

    if not os.path.exists(FEATURES_PATH) or not os.path.exists(INDEX_MAP_PATH):
        print("❌ 缺少数据。")
        return

    df = pd.read_parquet(FEATURES_PATH)
    index_map = pd.read_parquet(INDEX_MAP_PATH)
    index_map['ticker'] = index_map['code'].apply(lambda x: x.split(".")[1] + (".SS" if x.startswith("sh") else ".SZ"))
    
    df = pd.merge(df, index_map[['ticker', 'index_group']], on='ticker', how='left')
    df['index_group'] = df['index_group'].fillna('Other')
    
    factors = ["sp_ratio_rank", "vol_60d_res_rank", "mom_60d_rank"]
    horizons = ["label_5d", "label_20d", "label_60d", "label_120d"]
    groups = ["HS300", "ZZ500"]

    results = []

    for group in groups:
        print(f"\n>> 分析样本池: {group} <<")
        g_df = df[df["index_group"] == group]
        
        for f in factors:
            print(f"   因子: {f}")
            for h in horizons:
                ic_series = calculate_ic_series(g_df, f, h)
                if ic_series.empty:
                    continue
                
                mean_ic = ic_series.mean()
                t_stat = get_newey_west_t(ic_series)
                
                results.append({
                    "Group": group,
                    "Factor": f,
                    "Horizon": h.replace("label_", ""),
                    "Mean IC": mean_ic,
                    "NW t-stat": t_stat
                })

    res_df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("  IC Decay 汇总表")
    print("="*80)
    
    # 打印交叉表方便查看衰减
    for group in groups:
        print(f"\n--- [{group}] IC 衰减趋势 ---")
        sub_df = res_df[res_df["Group"] == group]
        pivot_df = sub_df.pivot(index="Factor", columns="Horizon", values="Mean IC")
        # 按照 5, 20, 60, 120 排序
        h_order = ["5d", "20d", "60d", "120d"]
        pivot_df = pivot_df[[h for h in h_order if h in pivot_df.columns]]
        print(pivot_df.to_string())

    print("\n" + "="*80)
    print("  t-stat (Newey-West) 显著性汇总")
    print("="*80)
    for group in groups:
        print(f"\n--- [{group}] t-stat 显著性 ---")
        sub_df = res_df[res_df["Group"] == group]
        pivot_t = sub_df.pivot(index="Factor", columns="Horizon", values="NW t-stat")
        h_order = ["5d", "20d", "60d", "120d"]
        pivot_t = pivot_t[[h for h in h_order if h in pivot_t.columns]]
        print(pivot_t.to_string())

if __name__ == "__main__":
    main()
