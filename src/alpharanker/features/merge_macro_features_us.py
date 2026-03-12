"""
merge_macro_features_us.py
===========================
将宏观市场状态机 (Regime) 标签合并入美股特征宽表。
输入: 
    1. C:/Data/Market/us/us_features_ortho.parquet (已包含正交化Alpha的特征)
    2. C:/Data/Market/us/macro_regime.parquet 
输出:
    C:/Data/Market/us/us_features_regime.parquet
"""

import os
import sys
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

FEAT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_ortho.parquet')
MACRO_PATH = os.path.join(DATA_ROOT, 'us', 'macro_regime.parquet')
OUTPUT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_regime.parquet')

def main():
    if not os.path.exists(FEAT_PATH):
        print(f"❌ 找不到特征文件: {FEAT_PATH}")
        return
    if not os.path.exists(MACRO_PATH):
        print(f"❌ 找不到宏观数据文件: {MACRO_PATH}")
        return
        
    print(">> 载入数据...")
    df = pd.read_parquet(FEAT_PATH)
    macro_df = pd.read_parquet(MACRO_PATH)
    
    # 确保日期格式一致
    df['report_date'] = pd.to_datetime(df['report_date'])
    macro_df['date'] = pd.to_datetime(macro_df['date'])
    
    macro_df.rename(columns={'date': 'report_date'}, inplace=True)
    
    print(f"特征库形状: {df.shape}")
    print(f"宏观库形状: {macro_df.shape}")
    
    # 合并
    print(">> 执行 As-Of / 对齐合并...")
    # 按照精确日期合并宏观标签
    df = pd.merge(df, macro_df[['report_date', 'sp500_close', 'vix_close', 'regime_label']], 
                  on='report_date', how='left')
    
    # 容错：如果某些交易日错位，用 ffill 填补
    df = df.sort_values(['ticker', 'report_date'])
    df['regime_label'] = df['regime_label'].fillna('Neutral') 
    
    print("\n--- 合并后的 Regime 分布 (按样本) ---")
    dist = df['regime_label'].value_counts(normalize=True) * 100
    for label, pct in dist.items():
        print(f"{label:10}: {pct:>5.1f}%")
        
    df.to_parquet(OUTPUT_PATH)
    print(f"\n[DONE] 已包含 Regime 环境因子的宽表保存至: {OUTPUT_PATH}")
    print(f"融合后列数: {df.shape[1]}")

if __name__ == "__main__":
    main()
