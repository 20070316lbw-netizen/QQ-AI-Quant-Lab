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
    在每个 report_date 截面内执行线性回归离。
    """
    print(f">> 开始正交化: {y_col} ~ {x_col}")
    
    def get_residual(group):
        # 过滤 NaN
        valid = group.dropna(subset=[x_col, y_col])
        if len(valid) < 20: 
            return pd.Series(index=group.index, dtype=float)
            
        X = sm.add_constant(valid[x_col])
        y = valid[y_col]
        model = OLS(y, X).fit()
        
        # 返回残差
        res = pd.Series(index=group.index, dtype=float)
        res.loc[valid.index] = model.resid
        return res

    # 按截面并行计算 (transform)
    df[f"{y_col}_res"] = df.groupby('report_date').apply(get_residual).reset_index(level=0, drop=True)
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
