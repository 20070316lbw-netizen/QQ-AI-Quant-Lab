"""
neutralize_features_us.py
=========================
执行风险中性化 (Risk Neutralization)。
目标：
1. 行业中性化 (Sector Neutral): 将绝对值特征（如 ROE, Volume 等）转化为行业内部的排名百分位 (Sector Rank)，消除行业天然壁垒（例如科技股与公用事业股的 ROE 鸿沟）。
2. 取消市场贝塔 (Market Neutral): 计算市场截面超额收益。虽然 LambdaRank 先天具有截面排序特性，但在评估中，我们可以显式观察纯粹超额收益的表现。
"""

import os
import sys
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

INPUT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_regime.parquet')
OUTPUT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_neutral.parquet')

def neutralize_features():
    print(">> 载入带宏观标签的特征库...")
    if not os.path.exists(INPUT_PATH):
        print("❌ 找不到输入特征。")
        return
        
    df = pd.read_parquet(INPUT_PATH)
    print(f"原数据形状: {df.shape}")
    
    # 我们不仅要中性化原始特征，还要包括之前提取的纯净 Alpha
    features_to_neutralize = [
        'mom_1m', 'mom_3m', 'mom_6m', 'mom_12m',
        'vol_60d_res', 'mom_1m_res',
        'vol_20d', 'vol_60d', 'vol_120d',
        'ROE', 'Net_Margin', 'Total Assets_YoY', 'Diluted EPS_YoY'
    ]
    
    # 填补行业空值
    df['sector'] = df['sector'].fillna('Unknown')
    
    print(">> 执行行业中性化 (Sector Neutralization)...")
    for col in features_to_neutralize:
        if col in df.columns:
            # 行业内排名：计算每个月、每个行业内的百分比位次 (0~1)
            # 这比传统的残差法更鲁棒，不受极值影响，极其适合 LambdaRank
            neutral_col = f"{col}_sec_rank"
            df[neutral_col] = df.groupby(['report_date', 'sector'])[col].rank(pct=True, na_option='keep')
            # 缺失值补中指
            df[neutral_col] = df[neutral_col].fillna(0.5)

    print(">> 执行大盘基准中性化 (Market Neutralized Label)...")
    # 计算每只股票当期的 横截面超额收益 = 股票收益 - 截面全市场等权平均收益
    df['market_mean_return'] = df.groupby('report_date')['label_3m_return'].transform('mean')
    df['label_3m_excess'] = df['label_3m_return'] - df['market_mean_return']
    
    # 我们可以基于 Excess Return 再次生成一个 Label Rank
    df['label_excess_rank'] = df.groupby('report_date')['label_3m_excess'].rank(ascending=True)

    df.to_parquet(OUTPUT_PATH)
    print(f"\n[DONE] 风险中性化特征已保存: {OUTPUT_PATH}")
    print(f"新增的中性化特征数量: {len(features_to_neutralize)}")

if __name__ == "__main__":
    neutralize_features()
