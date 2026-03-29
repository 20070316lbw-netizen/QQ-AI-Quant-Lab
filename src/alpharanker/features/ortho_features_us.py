"""
ortho_features_us.py
=====================
执行因子正交化 (Factor Orthogonalization)。
目标：从 vol_60d 中剥离 mom_12m 的线性影响，获得纯净波动率残差。

由于 LambdaRank 对非线性特征具有很强的捕捉能力，正交化可以帮助我们：
1. 观察纯净 Alpha 的贡献。
2. 减少特征间的共线性压力。
"""

import os
import sys
import pandas as pd
import numpy as np
from statsmodels.regression.linear_model import OLS
import statsmodels.api as sm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

INPUT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features.parquet')
OUTPUT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_ortho.parquet')

def orthogonalize_cross_section(df, x_col="mom_12m", y_col="vol_60d"):
    """
    在每个 report_date 截面内执行线性回归离 (Vectorized)。
    """
    print(f">> 开始正交化: {y_col} ~ {x_col}")
    
    # 过滤 NaN 并确保每组至少有 20 个样本
    valid_mask = df[x_col].notna() & df[y_col].notna()
    valid_counts = df[valid_mask].groupby('report_date')[x_col].transform('count')
    mask = valid_mask & (valid_counts >= 20)

    df_valid = df[mask].copy()

    # 计算分组均值
    means = df_valid.groupby('report_date')[[x_col, y_col]].transform('mean')
    df_c_x = df_valid[x_col] - means[x_col]
    df_c_y = df_valid[y_col] - means[y_col]

    # 向量化计算斜率(beta)和截距(alpha)
    cov_xy = (df_c_x * df_c_y).groupby(df_valid['report_date']).transform('sum')
    var_x = (df_c_x ** 2).groupby(df_valid['report_date']).transform('sum')

    beta = cov_xy / var_x
    alpha = means[y_col] - beta * means[x_col]

    # 计算残差
    df_valid['res'] = df_valid[y_col] - (alpha + beta * df_valid[x_col])

    # 映射回原 DataFrame
    df[f"{y_col}_res"] = np.nan
    df.loc[mask, f"{y_col}_res"] = df_valid['res']

    return df

def main():
    if not os.path.exists(INPUT_PATH):
        print("❌ 未找到输入特征。")
        return
        
    df = pd.read_parquet(INPUT_PATH)
    print(f"载入特征: {df.shape}")
    
    # 执行正交化
    df = orthogonalize_cross_section(df, "mom_12m", "vol_60d")
    df = orthogonalize_cross_section(df, "mom_12m", "mom_1m") # 剥离短期干扰
    
    # 填充少量残差 NaN
    res_cols = [c for c in df.columns if c.endswith("_res")]
    for col in res_cols:
        df[col] = df.groupby('report_date')[col].transform(lambda x: x.fillna(x.median()))
    
    df.to_parquet(OUTPUT_PATH)
    print(f"\n[DONE] 正交化特征已保存: {OUTPUT_PATH}")
    print(f"新增列: {res_cols}")

if __name__ == "__main__":
    main()
