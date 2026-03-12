"""
eval_ic_ir.py
=============
计算并可视化模型的截面 IC 时间序列（IC Time-Series Stability）
并计算量化核心指标 IC_IR = mean(IC) / std(IC)
"""

import os
import sys
import numpy as np
import pandas as pd
import lightgbm as lgb
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings("ignore")
from scipy.stats import spearmanr

FEATURES_PATH = r"C:\Data\Market\us\us_features.parquet"
OUTPUT_PLOT = r"C:\Users\lbw15\.gemini\antigravity\brain\88d8f421-374e-42de-aea5-14e30065f5a5\ic_stability.png"

# 使用刚刚消融实验得出的最强 6 因子核
TOP_6_FEATS = ["Total Liabilities_YoY", "vol_60d", "vol_120d", "Total Assets", "mom_12m", "Stockholders Equity_YoY"]

def split_by_time(df: pd.DataFrame):
    dates = sorted(df["report_date"].unique())
    n = len(dates)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)
    
    train_dates = dates[: n_train]
    val_dates   = dates[n_train : n_train + n_val]
    test_dates  = dates[n_train + n_val : ]
    
    return (
        df[df["report_date"].isin(train_dates)],
        df[df["report_date"].isin(val_dates)],
        df[df["report_date"].isin(test_dates)]
    )

def prepare_data(df: pd.DataFrame, valid_feats: list):
    df = df[df["label_rank"].notna()].copy().sort_values("report_date").reset_index(drop=True)
    for col in valid_feats:
        if col in df.columns:
            df[col] = df.groupby('report_date')[col].transform(lambda x: x.fillna(x.median())).fillna(0)

    pct = df.groupby("report_date")["label_rank"].transform(lambda x: x.rank(pct=True))
    df["relevance"] = pd.cut(pct, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=[0, 1, 2, 3, 4], include_lowest=True).astype(int)

    X = df[valid_feats].values.astype(np.float32)
    y = df["relevance"].values.astype(np.int32)
    q_sizes = df.groupby("report_date", sort=True).size().values
    return X, y, q_sizes, df

def main():
    print("=======================================================")
    print("  AlphaRanker IC 稳定性与 ICIR 评估")
    print("=======================================================")
    
    df = pd.read_parquet(FEATURES_PATH)
    df["report_date"] = pd.to_datetime(df["report_date"])
    
    train_df, val_df, test_df = split_by_time(df)
    
    X_train, y_train, q_train, _ = prepare_data(train_df, TOP_6_FEATS)
    X_val,   y_val,   q_val,   _ = prepare_data(val_df, TOP_6_FEATS)
    X_test,  _,       _,       te_df = prepare_data(test_df, TOP_6_FEATS)

    lgb_train = lgb.Dataset(X_train, label=y_train, group=q_train)
    lgb_val   = lgb.Dataset(X_val,   label=y_val,   group=q_val, reference=lgb_train)

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "verbose": -1,
        "seed": 42
    }
    
    model = lgb.train(
        params, lgb_train,
        num_boost_round=100,
        valid_sets=[lgb_val],
        callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
    )

    preds = model.predict(X_test)
    te_df["pred"] = preds
    
    # 逐截面计算 IC
    ic_list = []
    dates = []
    
    for date, grp in te_df.groupby("report_date"):
        if len(grp) > 5 and grp["pred"].std() > 1e-6 and grp["relevance"].std() > 1e-6:
            ic, _ = spearmanr(grp["pred"], grp["relevance"])
            ic_list.append(ic)
            dates.append(date)
            
    ic_arr = np.array(ic_list)
    mean_ic = np.mean(ic_arr)
    std_ic = np.std(ic_arr)
    ic_ir = mean_ic / (std_ic + 1e-8)
    win_rate = np.mean(ic_arr > 0)
    
    print(f"\n评估结果 (2024-2026 样本外测试期):")
    print(f"  截面期数: {len(ic_list)}")
    print(f"  Mean IC:  {mean_ic:.4f}")
    print(f"  Std IC:   {std_ic:.4f}")
    print(f"  IC IR:    {ic_ir:.4f}")
    print(f"  IC > 0 胜率: {win_rate:.1%}")
    
    # 可视化 IC 时序图
    plt.figure(figsize=(12, 6))
    colors = ['#2ecc71' if x > 0 else '#e74c3c' for x in ic_arr]
    plt.bar(dates, ic_arr, width=20, color=colors, alpha=0.8)
    
    # 添加均值辅助线
    plt.axhline(mean_ic, color='blue', linestyle='--', label=f'Mean IC: {mean_ic:.4f}')
    plt.axhline(0, color='black', linewidth=1)
    
    plt.title(f'Monthly Rank IC Out-of-Sample (IC IR = {ic_ir:.4f})', fontsize=14)
    plt.xlabel('Date')
    plt.ylabel('Rank IC (Spearman)')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT, dpi=150)
    print(f"\n[DONE] IC 稳定性时序图已生成: {OUTPUT_PLOT}")

if __name__ == "__main__":
    main()
