"""
ablation_test_us.py
===================
执行美股 LambdaRank 模型的因子消融实验 (Ablation Test)。
通过将 39 个因子切分为几个逻辑簇（动量、波动率、财务规模、盈利增速），
逐一剔除（Drop）这些簇后重新训练并测算测试集 IC 的损失，从而定位真正的 Alpha 源泉。
"""

import os
import sys
import numpy as np
import pandas as pd
import lightgbm as lgb
import warnings

warnings.filterwarnings("ignore")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "features")))
from validate_pipeline import compute_rank_ic

FEATURES_PATH = r"C:\Data\Market\us\us_features.parquet"

FEATURE_COLS = [
    # 动量与趋势指标
    "mom_1m", "mom_3m", "mom_6m", "mom_12m", 
    "bias_20d", "bias_60d", "bias_120d", 
    "rsi_14d", "rsi_28d", 
    "macd_line", "macd_signal", "macd_hist", 
    "bb_width", "bb_pct_b", 
    "vol_trend_5_60",
    
    # 波动与振幅
    "vol_20d", "vol_60d", "vol_120d", "amplitude_20d", 
    
    # 基本面底层财务
    "Net Income", "Total Assets", "Total Liabilities", 
    "Stockholders Equity", "Operating Cash Flow", 
    "Diluted EPS", "Total Revenue", 
    
    # 基本面质量与高增长派生
    "ROE", "Net_Margin",
    "Net Income_YoY", "Total Assets_YoY", "Total Liabilities_YoY", 
    "Stockholders Equity_YoY", "Operating Cash Flow_YoY", 
    "Diluted EPS_YoY", "Total Revenue_YoY", "ROE_YoY", "Net_Margin_YoY"
]

FEATURE_GROUPS = {
    "Technical_Momentum": ["mom_1m", "mom_3m", "mom_6m", "mom_12m", "bias_20d", "bias_60d", "bias_120d", "rsi_14d", "rsi_28d", "macd_line", "macd_signal", "macd_hist", "bb_width", "bb_pct_b", "vol_trend_5_60"],
    "Price_Volatility": ["vol_20d", "vol_60d", "vol_120d", "amplitude_20d"],
    "Fundamental_Scale": ["Net Income", "Total Assets", "Total Liabilities", "Stockholders Equity", "Operating Cash Flow", "Diluted EPS", "Total Revenue"],
    "Fundamental_Growth": ["ROE", "Net_Margin", "Net Income_YoY", "Total Assets_YoY", "Total Liabilities_YoY", "Stockholders Equity_YoY", "Operating Cash Flow_YoY", "Diluted EPS_YoY", "Total Revenue_YoY", "ROE_YoY", "Net_Margin_YoY"]
}

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

def run_experiment(name: str, used_feats: list, train_df, val_df, test_df) -> float:
    print(f"\n[{name}] 开始训练，使用特征数: {len(used_feats)}")
    X_train, y_train, q_train, _ = prepare_data(train_df, used_feats)
    X_val,   y_val,   q_val,   _ = prepare_data(val_df, used_feats)
    X_test,  _,       _,       te_df = prepare_data(test_df, used_feats)

    lgb_train = lgb.Dataset(X_train, label=y_train, group=q_train, feature_name=used_feats)
    lgb_val   = lgb.Dataset(X_val,   label=y_val,   group=q_val,   feature_name=used_feats, reference=lgb_train)

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
    mean_ic = compute_rank_ic(te_df, pred_col="pred", label_col="relevance")
    print(f"  --> 测试集 IC: {mean_ic:.4f} (最优迭代: {model.best_iteration})")
    return mean_ic

def main():
    print("=======================================================")
    print("  AlphaRanker 因子消融实验 (Ablation Test)")
    print("=======================================================")
    
    df = pd.read_parquet(FEATURES_PATH)
    df["report_date"] = pd.to_datetime(df["report_date"])
    
    train_df, val_df, test_df = split_by_time(df)
    
    results = {}
    
    # 1. Baseline (All features)
    ic_all = run_experiment("Baseline (所有 39 因子)", FEATURE_COLS, train_df, val_df, test_df)
    results["Baseline"] = ic_all
    
    # 2. Leave-One-Group-Out (LOGO) Ablation
    for group_name, drop_feats in FEATURE_GROUPS.items():
        used_feats = [f for f in FEATURE_COLS if f not in drop_feats]
        ic_drop = run_experiment(f"消融: 剔除 {group_name}", used_feats, train_df, val_df, test_df)
        results[f"Drop_{group_name}"] = ic_drop
        
    print("\n\n=======================================================")
    print("  消融实验结果总结 (IC 衰减幅度越小说明该模块越无用，IC断崖下跌说明它是绝对核心)")
    print("=======================================================")
    baseline = results["Baseline"]
    print(f"{'Experiment':<25} | {'Mean IC':<10} | {'Drop from Baseline'}")
    print("-" * 60)
    for exp, ic in results.items():
        diff = ic - baseline
        print(f"{exp:<25} | {ic:.4f}     | {diff:+.4f}")
        
    print("\n[单独提取巨头因子看看其统御力]")
    # 3. Only Top 6 Features
    top_6_feats = ["Total Liabilities_YoY", "vol_60d", "vol_120d", "Total Assets", "mom_12m", "Stockholders Equity_YoY"]
    ic_top6 = run_experiment("Only Top 6 (仅保留重要性前6的因子)", top_6_feats, train_df, val_df, test_df)
    print(f"\n  --> 仅使用 6 个因子取得了: {ic_top6:.4f} 截面 IC！")

if __name__ == "__main__":
    main()
