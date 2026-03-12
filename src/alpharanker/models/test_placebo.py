"""
train_us_model.py
==================
用 LightGBM LambdaRank 训练美股股票排名模型（纯量价/技术面版）。

输入：  C:/Data/Market/us/us_features.parquet
输出：  models/us_lgbm.pkl
        models/us_lgbm_feature_importance.csv
        models/us_feature_importance.png
"""

import os
import sys
import pickle
import warnings
import numpy as np
import pandas as pd
import lightgbm as lgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import MODEL_DIR

FEATURES_PATH = r"C:\Data\Market\us\us_features.parquet"
MODEL_PATH    = os.path.join(MODEL_DIR, "us_lgbm.pkl")
IMPORTANCE_CSV = os.path.join(MODEL_DIR, "us_lgbm_feature_importance.csv")

FEATURE_COLS = [
    # ---------------- 量价与技术指标 ----------------
    "mom_1m", "mom_3m", "mom_6m", "mom_12m", 
    "bias_20d", "bias_60d", "bias_120d", 
    "vol_20d", "vol_60d", "vol_120d", "amplitude_20d", 
    "rsi_14d", "rsi_28d", 
    "macd_line", "macd_signal", "macd_hist", 
    "bb_width", "bb_pct_b", 
    "vol_trend_5_60",
    
    # ---------------- EDGAR 十年基础财报科目 ----------------
    "Net Income", "Total Assets", "Total Liabilities", 
    "Stockholders Equity", "Operating Cash Flow", 
    "Diluted EPS", "Total Revenue", 
    
    # ---------------- 基本面衍生派生池 ----------------
    "ROE", "Net_Margin",
    "Net Income_YoY", "Total Assets_YoY", "Total Liabilities_YoY", 
    "Stockholders Equity_YoY", "Operating Cash Flow_YoY", 
    "Diluted EPS_YoY", "Total Revenue_YoY", "ROE_YoY", "Net_Margin_YoY"
]

def prepare_data(df: pd.DataFrame):
    """返回 (df_clean, X, y, q_sizes, valid_feats)。
    标签：截面内百分位排名 → 5档整数 (0=最差, 4=最佳)。
    """
    df = df[df["label_rank"].notna()].copy().sort_values("report_date").reset_index(drop=True)

    # 填充少量 NaN (如上市初期的某些长周期因子), 防止 lgbm 直接丢弃
    for col in FEATURE_COLS:
        if col in df.columns:
            df[col] = df.groupby('report_date')[col].transform(lambda x: x.fillna(x.median()))
            df[col] = df[col].fillna(0) # 如果整个截面都缺失则填0

    # transform 保留列结构，不改变 index
    pct = df.groupby("report_date")["label_rank"].transform(lambda x: x.rank(pct=True))
    df["relevance"] = pd.cut(pct, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                             labels=[0, 1, 2, 3, 4], include_lowest=True).astype(int)

    valid_feats = [c for c in FEATURE_COLS if c in df.columns]
    
    # 类别特征（若存在 sector/industry）目前脚本暂未加入，保持纯 float 数组
    X = df[valid_feats].values.astype(np.float32)
    y = df["relevance"].values.astype(np.int32)
    q_sizes = df.groupby("report_date", sort=True).size().values

    return df, X, y, q_sizes, valid_feats


def split_by_time(df: pd.DataFrame):
    dates = sorted(df["report_date"].unique())
    n = len(dates)
    # 按月频，共有 130 多个月。划分：前 70% 训练，中 15% 验证，后 15% 测试
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)
    
    train_dates = dates[: n_train]
    val_dates   = dates[n_train : n_train + n_val]
    test_dates  = dates[n_train + n_val : ]
    
    return (
        df[df["report_date"].isin(train_dates)],
        df[df["report_date"].isin(val_dates)],
        df[df["report_date"].isin(test_dates)],
        train_dates, val_dates, test_dates,
    )


def main():
    print("=" * 55)
    print("  AlphaRanker — 美股 LightGBM LambdaRank 训练 (10年月频量价模型)")
    print("=" * 55)

    if not os.path.exists(FEATURES_PATH):
        print(f"[ERR] 特征文件不存在: {FEATURES_PATH}")
        return

    df = pd.read_parquet(FEATURES_PATH)
    df["report_date"] = pd.to_datetime(df["report_date"])
    print(f"\n总样本: {len(df)} | 截面: {df['report_date'].nunique()} | 股票: {df['ticker'].nunique()}")

    train_df, val_df, test_df, train_dates, val_dates, test_dates = split_by_time(df)
    print(f"\n训练集: {len(train_dates)} 截面 ({str(train_dates[0])[:7]} ~ {str(train_dates[-1])[:7]})")
    print(f"验证集: {len(val_dates)} 截面 ({str(val_dates[0])[:7]} ~ {str(val_dates[-1])[:7]})")
    print(f"测试集: {len(test_dates)} 截面 ({str(test_dates[0])[:7]} ~ {str(test_dates[-1])[:7]})")

    tr_df, X_train, y_train, q_train, valid_feats = prepare_data(train_df)
    
    print("\n[!!!] 正在进行安慰剂测试 (Placebo Test)：随机打乱训练集和验证集标签 [!!!]")
    np.random.seed(42)
    np.random.shuffle(y_train)
    
    va_df, X_val,   y_val,   q_val,   _           = prepare_data(val_df)
    np.random.shuffle(y_val)
    
    te_df, X_test,  y_test,  q_test,  _           = prepare_data(test_df)

    print(f"\n特征: {len(valid_feats)} | 训练: {len(X_train)} | 验证: {len(X_val)} | 测试: {len(X_test)}")

    lgb_train = lgb.Dataset(X_train, label=y_train, group=q_train, feature_name=valid_feats)
    lgb_val   = lgb.Dataset(X_val,   label=y_val,   group=q_val,   feature_name=valid_feats, reference=lgb_train)

    params = {
        "objective":         "lambdarank",
        "metric":            "ndcg",
        "ndcg_eval_at":      [5, 10, 20],
        "learning_rate":     0.03,
        "num_leaves":        31,
        "min_child_samples": 20,
        "feature_fraction":  0.8,
        "bagging_fraction":  0.8,
        "bagging_freq":      1,
        "lambda_l1":         0.1,
        "lambda_l2":         0.1,
        "verbose":           -1,
        "seed":              42,
    }

    print("\n开始训练...")
    
    callbacks = [
        lgb.early_stopping(stopping_rounds=50, verbose=False),
        lgb.log_evaluation(period=50),
    ]

    model = lgb.train(
        params, lgb_train,
        num_boost_round=800,
        valid_sets=[lgb_train, lgb_val],
        valid_names=["train", "val"],
        callbacks=callbacks
    )
    print(f"\n最优轮次: {model.best_iteration}")

    # ── 评估 ──────────────────────────────────────────────────────────────────
    if len(X_test) > 0:
        test_pred = model.predict(X_test)
        
        # 填充 NaN 的预测值以防止 spearmanr 失败
        if np.isnan(test_pred).any():
            test_pred = np.nan_to_num(test_pred)
            
        ic_total, _ = spearmanr(test_pred, y_test)
        print(f"\n测试集 IC (Spearman): {ic_total:.4f}")

        te_df = te_df.copy()
        te_df["pred"] = test_pred
        ic_rows = []
        for date, grp in te_df.groupby("report_date"):
            if len(grp) > 5:
                # 只有方差非零才能计算 IC
                if grp["pred"].std() > 1e-6 and grp["relevance"].std() > 1e-6:
                    ic_d, _ = spearmanr(grp["pred"], grp["relevance"])
                    ic_rows.append({"date": date, "ic": ic_d})
        
        if ic_rows:
            ic_df = pd.DataFrame(ic_rows).dropna()
            mean_ic = ic_df['ic'].mean()
            std_ic = ic_df['ic'].std() + 1e-8
            ir = mean_ic / std_ic
            ic_pos = (ic_df['ic'] > 0).mean()
            
            print(f"平均 IC: {mean_ic:.4f} | ICIR: {ir:.4f} | IC>0胜率: {ic_pos:.1%}")
    else:
        print("\n(测试集为空，跳过评估)")

    # ── 特征重要性 ────────────────────────────────────────────────────────────
    importance = pd.DataFrame({
        "feature":          valid_feats,
        "importance_gain":  model.feature_importance(importance_type="gain"),
        "importance_split": model.feature_importance(importance_type="split"),
    }).sort_values("importance_gain", ascending=False)

    os.makedirs(MODEL_DIR, exist_ok=True)
    importance.to_csv(IMPORTANCE_CSV, index=False)
    print(f"\n特征重要性 (Top 10):\n{importance.head(10).to_string(index=False)}")

    # ── 保存模型 ──────────────────────────────────────────────────────────────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": model, "features": valid_feats}, f)
    print(f"\n[DONE] 模型已保存: {MODEL_PATH}")

    # ── 特征重要性图 ──────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))
    top = importance.head(15)
    ax.barh(top["feature"].iloc[::-1], top["importance_gain"].iloc[::-1], color="#6366f1")
    ax.set_xlabel("Importance (Gain)")
    ax.set_title("US AlphaRanker — Feature Importance")
    plt.tight_layout()
    plot_path = os.path.join(MODEL_DIR, "us_feature_importance.png")
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    print(f"[DONE] 特征重要性图已更新: {plot_path}")


if __name__ == "__main__":
    main()
