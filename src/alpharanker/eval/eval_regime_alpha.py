"""
eval_regime_alpha.py
====================
测试 Alpha 因子 (特别是 vol_60d_res 和 mom_12m) 在不同宏观环境 (Regime) 下的表现。

输出：
- 不同 Regime 下单因子的 Rank IC
- 不同 Regime 下单组合 (Q5 vs Q1) 的平均收益差异
"""

import os
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

FEAT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_regime.parquet')

def compute_ic_by_regime(df, factor_col, label_col="label_3m_return"):
    """按 Regime 分组计算 Rank IC"""
    res = []
    
    for regime, grp_r in df.groupby('regime_label'):
        ic_list = []
        # 在该 Regime 的每一个截面上计算 IC
        for date, grp_d in grp_r.groupby('report_date'):
            if len(grp_d) > 5 and grp_d[factor_col].std() > 1e-6 and grp_d[label_col].std() > 1e-6:
                ic, _ = spearmanr(grp_d[factor_col], grp_d[label_col])
                ic_list.append(ic)
        
        if ic_list:
            res.append({
                'Regime': regime,
                'Factor': factor_col,
                'Mean_IC': np.mean(ic_list),
                'Periods': len(ic_list)
            })
            
    return pd.DataFrame(res)

def compute_q_return_by_regime(df, factor_col, label_col="label_3m_return"):
    """按 Regime 计算五等分分组收益"""
    res = []
    
    # 全局去极值处理，防止单只股票异常影响
    df = df.dropna(subset=[factor_col, label_col]).copy()
    
    for regime, grp_r in df.groupby('regime_label'):
        grp_r = grp_r.copy()
        
        # 定义安全的分箱函数
        def safe_qcut(x):
            try:
                return pd.qcut(x, 5, labels=[1,2,3,4,5], duplicates='drop')
            except:
                return pd.Series([np.nan]*len(x), index=x.index)
                
        grp_r['q'] = grp_r.groupby('report_date')[factor_col].transform(safe_qcut)
        
        # 计算 Q1 和 Q5 的平均收益
        q_ret = grp_r.groupby('q')[label_col].mean()
        if 1 in q_ret.index and 5 in q_ret.index:
            res.append({
                'Regime': regime,
                'Factor': factor_col,
                'Q1_Ret': q_ret.loc[1] * 100,
                'Q5_Ret': q_ret.loc[5] * 100,
                'Spread(Q5-Q1)': (q_ret.loc[5] - q_ret.loc[1]) * 100
            })
            
    return pd.DataFrame(res)

def main():
    if not os.path.exists(FEAT_PATH):
        print("❌ 找不到融合后的 Regime 特征宽表。")
        return
        
    df = pd.read_parquet(FEAT_PATH)
    
    factors_to_test = ['mom_12m', 'vol_60d_res', 'Total Assets']
    
    print("\n--- 1. 不同 Regime 下的 Factor Rank IC ---")
    ic_df_list = []
    for f in factors_to_test:
        if f in df.columns:
            ic_df = compute_ic_by_regime(df, f)
            ic_df_list.append(ic_df)
    
    final_ic = pd.concat(ic_df_list).set_index(['Regime', 'Factor'])['Mean_IC'].unstack()
    print(final_ic.round(4))
    
    print("\n\n--- 2. 不同 Regime 下的组合超额收益 (Q5 - Q1) (%) ---")
    ret_df_list = []
    for f in factors_to_test:
        if f in df.columns:
            ret_df = compute_q_return_by_regime(df, f)
            ret_df_list.append(ret_df)
            
    final_ret = pd.concat(ret_df_list).set_index(['Regime', 'Factor'])['Spread(Q5-Q1)'].unstack()
    print(final_ret.round(2))
    
    # 绘制热力图以供研报使用
    plt.figure(figsize=(10, 5))
    sns.heatmap(final_ret, annot=True, fmt=".2f", cmap="RdYlGn", center=0)
    plt.title("Regime Alpha Spread (Q5-Q1 Return %)")
    plt.tight_layout()
    out_img = os.path.join(DATA_ROOT, 'us', 'regime_alpha_heatmap.png')
    plt.savefig(out_img, dpi=150)
    print(f"\n[DONE] Regime 分析热力图已保存至: {out_img}")

if __name__ == "__main__":
    main()
