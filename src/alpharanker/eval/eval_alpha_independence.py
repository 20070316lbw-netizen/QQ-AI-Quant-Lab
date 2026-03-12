"""
eval_alpha_independence.py
==========================
Alpha Genome 核心实验：因子独立性验证。
使用双重排序法 (Double Sort) 剥离动量 (Momentum) 对波动率 (Volatility) 的影响。

步骤：
1. 按 12 个月动量 (mom_12m) 进行 5 分组。
2. 在每个动量组内部，再按 60 日波动率 (vol_60d) 进行 5 分组。
3. 计算 25 个组合的平均未来 3 个月收益。
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

FEATURES_PATH = os.path.join(DATA_ROOT, 'us', 'us_features.parquet')

def load_data():
    if not os.path.exists(FEATURES_PATH):
        print(f"❌ 未找到特征文件: {FEATURES_PATH}")
        return None
    df = pd.read_parquet(FEATURES_PATH)
    # 确保日期格式
    df['report_date'] = pd.to_datetime(df['report_date'])
    return df

def run_double_sort(df, sort_col1="mom_12m", sort_col2="vol_60d", label_col="label_3m_return"):
    print(f"\n>> 启动双重排序实验: 第一因子={sort_col1}, 第二因子={sort_col2}")
    
    # 过滤掉缺失值
    df = df.dropna(subset=[sort_col1, sort_col2, label_col])
    
    # 第一步：按 report_date 截面进行第一因子 5 分组
    df['group1'] = df.groupby('report_date')[sort_col1].transform(
        lambda x: pd.qcut(x, 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    )
    
    # 第二步：在每个 report_date + group1 的子集内，按第二因子 5 分组
    # 这一步是关键，它实现了对 group1 的受控（Controlled）
    df['group2'] = df.groupby(['report_date', 'group1'])[sort_col2].transform(
        lambda x: pd.qcut(x, 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    )
    
    # 计算 25 个格子的平均收益
    result_matrix = df.groupby(['group1', 'group2'])[label_col].mean().unstack()
    
    # 转化为百分比
    result_matrix *= 100
    
    print("\n--- 5x5 双重排序收益矩阵 (未来3个月, %) ---")
    print(result_matrix)
    
    return result_matrix

def plot_heatmap(matrix, sort_col1, sort_col2):
    plt.figure(figsize=(10, 8))
    sns.heatmap(matrix, annot=True, fmt=".2f", cmap="RdYlGn", center=0)
    plt.title(f"Double Sort: {sort_col1} (Rows) vs {sort_col2} (Cols)\nAverage 3M Forward Return (%)")
    plt.xlabel(f"{sort_col2} Quintile")
    plt.ylabel(f"{sort_col1} Quintile")
    
    output_path = os.path.join(os.path.dirname(FEATURES_PATH), "double_sort_heatmap.png")
    plt.savefig(output_path, dpi=150)
    print(f"\n[DONE] 热力图已保存至: {output_path}")

def main():
    df = load_data()
    if df is None: return
    
    # 默认实验：动量 vs 波动率
    matrix = run_double_sort(df, "mom_12m", "vol_60d")
    plot_heatmap(matrix, "mom_12m", "vol_60d")
    
    # 分析独立性
    # 检查每一行（固定动量）中，Q5(高波) vs Q1(低波) 的差异是否一致
    diff = matrix[5] - matrix[1]
    print("\n--- 独立性分析：固定动量组，高波 vs 低波的超额收益 ---")
    print(diff)
    
    avg_diff = diff.mean()
    if avg_diff > 0.5:
        print(f"\n结论: 波动率因子具备独立 Alpha。平均超额收益: {avg_diff:.2f}%")
    else:
        print(f"\n结论: 波动率因子独立性较弱，可能受动量或其他因素主导。")

if __name__ == "__main__":
    main()
