"""
eval_enhanced_factors_us.py
==========================
评估新增的 Quality 因子在美股的表现。
包括：ROA_sec_rank, Asset_Turnover_sec_rank, DE_Ratio_sec_rank, Cash_to_Liabilities_sec_rank
"""

import os
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

FEAT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_enhanced.parquet')

def main():
    if not os.path.exists(FEAT_PATH):
        print("❌ 找不到增强版特征库。")
        return
        
    df = pd.read_parquet(FEAT_PATH)
    label_col = 'label_3m_excess' # 使用剥离大盘后的超额收益
    
    new_factors = [
        'ROA_sec_rank', 
        'Asset_Turnover_sec_rank', 
        'DE_Ratio_sec_rank', 
        'Cash_to_Liabilities_sec_rank',
        'EP_sec_rank',
        'SP_sec_rank',
        'BP_sec_rank'
    ]
    
    results = []
    print(f"\n>> 开始对 {len(new_factors)} 个新增质量因子进行 IC 测试...")
    
    for factor in new_factors:
        # 计算每一期的 Rank IC
        ics = []
        for date, group in df.groupby('report_date'):
            valid = group.dropna(subset=[factor, label_col])
            if len(valid) > 50:
                ic, _ = spearmanr(valid[factor], valid[label_col])
                ics.append(ic)
        
        if ics:
            mean_ic = np.mean(ics)
            ir = mean_ic / np.std(ics) if np.std(ics) != 0 else 0
            
            # 分组收益 (Q5 - Q1)
            q_rets = []
            for date, group in df.groupby('report_date'):
                valid = group.dropna(subset=[factor, label_col])
                if len(valid) > 50:
                    # 使用 rank 百分位 + cut 确保稳定分为 5 组（或空组）
                    ranks = valid[factor].rank(pct=True)
                    valid['q'] = pd.cut(ranks, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], 
                                     labels=[1, 2, 3, 4, 5], include_lowest=True)
                    ret = valid.groupby('q', observed=True)[label_col].mean()
                    if 1 in ret.index and 5 in ret.index:
                        q_rets.append(ret.loc[5] - ret.loc[1])
            
            mean_spread = np.mean(q_rets) * 100
            
            results.append({
                'Factor': factor,
                'Mean_IC': mean_ic,
                'IC_IR': ir,
                'Q5-Q1_Spread(%)': mean_spread
            })
            print(f"   [{factor:25s}] IC: {mean_ic:.4f} | IR: {ir:.4f} | Spread: {mean_spread:.2f}%")

    print("\n--- 质量因子评估汇总 ---")
    res_df = pd.DataFrame(results)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    main()
