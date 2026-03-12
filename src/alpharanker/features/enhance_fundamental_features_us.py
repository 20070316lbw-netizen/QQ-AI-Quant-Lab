"""
enhance_fundamental_features_us.py
==================================
Alpha Genome 扩展：价值与质量因子簇。
从原始财报数据中衍生计算估值指标（Value）与盈利/营运质量指标（Quality）。

计算逻辑：
Value:
    - EP (Earnings/Price): Diluted EPS / Close  (PE的倒数，更稳定)
    - SP (Sales/Price): Total Revenue / MarketCap (这里暂时用 Revenue / Close 作为替代指标)
    - BP (Book/Price): Stockholders Equity / MarketCap
Quality:
    - ROA: Net Income / Total Assets
    - AssetTurnover: Total Revenue / Total Assets
    - DE_Ratio (Leverage): Total Liabilities / Stockholders Equity
"""

import os
import sys
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

INPUT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_neutral.parquet')
OUTPUT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_enhanced.parquet')

def calculate_derived_factors(df):
    print(">> 开始计算衍生质量与价值因子...")
    
    # 0. 合并价格数据以计算价值因子 (Value)
    PRICE_SNAPSHOT = os.path.join(DATA_ROOT, 'us', 'us_monthly_closes.parquet')
    if os.path.exists(PRICE_SNAPSHOT):
        print(">> 合并月度价格快照...")
        price_df = pd.read_parquet(PRICE_SNAPSHOT)
        price_df['report_date'] = pd.to_datetime(price_df['report_date'])
        df['report_date'] = pd.to_datetime(df['report_date'])
        df = pd.merge(df, price_df, on=['report_date', 'ticker'], how='left')
        df['close'] = df.groupby('ticker')['close'].ffill() # 少量缺失值前向填充
    else:
        print("⚠️ 找不到价格快照，将跳过价值因子计算。")
        df['close'] = np.nan

    # 1. 质量因子 (Quality)
    df['ROA'] = df['Net Income'] / df['Total Assets'].replace(0, np.nan)
    df['Asset_Turnover'] = df['Total Revenue'] / df['Total Assets'].replace(0, np.nan)
    df['DE_Ratio'] = df['Total Liabilities'] / df['Stockholders Equity'].replace(0, np.nan)
    
    # 2. 增长与营运
    print(">> 计算营运效率同比变化...")
    df['Asset_Turnover_YoY'] = df.groupby('ticker')['Asset_Turnover'].pct_change(4)
    df['Cash_to_Liabilities'] = df['Operating Cash Flow'] / df['Total Liabilities'].replace(0, np.nan)
    
    # 3. 价值因子 (Value)
    print(">> 计算价值因子群 (EP, SP, BP)...")
    # EP: Earnings to Price
    df['EP'] = df['Diluted EPS'] / df['close'].replace(0, np.nan)
    
    # 推导 Shares Outstanding = Net Income / Diluted EPS (如果有)
    # SP: Sales / (Close * Shares) = Sales / (Close * (Net Income / Diluted EPS))
    #    = (Sales/Net Income) * (Diluted EPS / Close)
    df['SP'] = (df['Total Revenue'] / df['Net Income'].replace(0, np.nan)) * df['EP']
    
    # BP: Equity / (Close * Shares) = (Equity/Net Income) * (Diluted EPS / Close)
    df['BP'] = (df['Stockholders Equity'] / df['Net Income'].replace(0, np.nan)) * df['EP']

    # 清理非数值
    cols_to_fix = ['ROA', 'Asset_Turnover', 'DE_Ratio', 'Asset_Turnover_YoY', 'Cash_to_Liabilities', 'EP', 'SP', 'BP']
    print(f">> 处理极值与缺失值: {cols_to_fix}")
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
    
    # 批量填补截面中位数
    print(">> 执行截面中位数填补...")
    valid_fix_cols = [c for c in cols_to_fix if c in df.columns]
    medians = df.groupby('report_date')[valid_fix_cols].transform('median')
    df[valid_fix_cols] = df[valid_fix_cols].fillna(medians)
    df[valid_fix_cols] = df[valid_fix_cols].fillna(0)
        
    print(f">> 因子计算核心逻辑完成。")
    return df

def main():
    if not os.path.exists(INPUT_PATH):
        print(f"❌ 找不到输入特征文件: {INPUT_PATH}")
        return
        
    df = pd.read_parquet(INPUT_PATH)
    print(f"载入特征库: {df.shape}")
    
    df = calculate_derived_factors(df)
    
    print(">> 对新增因子执行行业中性化排名...")
    new_cols = ['ROA', 'Asset_Turnover', 'DE_Ratio', 'Cash_to_Liabilities', 'EP', 'SP', 'BP']
    df['sector'] = df['sector'].fillna('Unknown')
    
    for col in new_cols:
        if col in df.columns:
            df[f"{col}_sec_rank"] = df.groupby(['report_date', 'sector'])[col].rank(pct=True)
            df[f"{col}_sec_rank"] = df[f"{col}_sec_rank"].fillna(0.5)

    df.to_parquet(OUTPUT_PATH)
    print(f"\n[DONE] 增强版特征库已保存: {OUTPUT_PATH}")
    print(f"最终特征数: {df.shape[1]}")

if __name__ == "__main__":
    main()
