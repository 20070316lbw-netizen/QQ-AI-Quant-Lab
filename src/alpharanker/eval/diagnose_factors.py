import pandas as pd
import numpy as np
import os
from scipy.stats import spearmanr
import statsmodels.api as sm

# Path from config
FEATURES_PATH = r'C:\Data\Market\cn\cn_features_enhanced.parquet'

def diagnostic_report():
    if not os.path.exists(FEATURES_PATH):
        print("Features not found.")
        return
        
    df = pd.read_parquet(FEATURES_PATH)
    print(f"Total Rows: {len(df)}")
    
    # 检查 IC 稳定性
    dates = sorted(df["date"].unique())
    df["year"] = pd.to_datetime(df["date"]).dt.year

    # 2. 12-1 动量深度分析
    print("\n" + "="*40)
    print("  12-1 Momentum (M_long) 流失诊断")
    print("="*40)
    
    for f in ["mom_12m_minus_1m", "mom_12m_minus_1m_rank"]:
        if f not in df.columns: continue
        ics = []
        for d in dates:
            grp = df[df["date"] == d]
            mask = grp[[f, "label_next_month"]].notna().all(axis=1)
            if mask.sum() > 50:
                ic, _ = spearmanr(grp.loc[mask, f], grp.loc[mask, "label_next_month"])
                ics.append(ic)
        print(f"\n{f} Global IC Mean: {np.mean(ics):.4f}, Std: {np.std(ics):.4f}")
    
    # 检查中性化前后的关联
    if "mom_12m_minus_1m" in df.columns:
        corr_before_after = df[["mom_12m_minus_1m", "mom_12m_minus_1m_rank"]].corr().iloc[0,1]
        print(f"Correlation (Before vs After Neutralization): {corr_before_after:.4f}")
        
    # 4. 分指数诊断 (HS300 vs ZZ500)
    print("\n" + "="*40)
    print("  Index-Specific Analysis (ZZ500 vs HS300)")
    print("="*40)
    
    import baostock as bs
    bs.login()
    zz500 = []
    rs = bs.query_zz500_stocks()
    while rs.next(): zz500.append(rs.get_row_data()[1].split(".")[1] + (".SS" if rs.get_row_data()[1].startswith("sh") else ".SZ"))
    hs300 = []
    rs = bs.query_hs300_stocks()
    while rs.next(): hs300.append(rs.get_row_data()[1].split(".")[1] + (".SS" if rs.get_row_data()[1].startswith("sh") else ".SZ"))
    bs.logout()
    
    for name, pool in [("ZZ500", zz500), ("HS300", hs300)]:
        print(f"\n--- {name} Pool (Size: {len(pool)}) ---")
        sub_df = df[df["ticker"].isin(pool)]
        for f in ["mom_12m_minus_1m_rank"]:
            ics = []
            for d in sub_df["date"].unique():
                grp = sub_df[sub_df["date"] == d]
                mask = grp[[f, "label_next_month"]].notna().all(axis=1)
                if mask.sum() > 20:
                    ic, _ = spearmanr(grp.loc[mask, f], grp.loc[mask, "label_next_month"])
                    ics.append(ic)
            if ics:
                print(f"  {f} IC Mean: {np.mean(ics):.4f}, T-stat: {np.mean(ics)/(np.std(ics)/np.sqrt(len(ics))):.2f}")

if __name__ == "__main__":
    diagnostic_report()
