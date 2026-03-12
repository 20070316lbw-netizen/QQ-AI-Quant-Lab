"""
train_us_neutral_model.py
=========================
用 LightGBM LambdaRank 训练纯净版 Alpha 模型。
所有核心特征已替换为其行业中性化版本 (`_sec_rank`)。
标签目标已替换为剥离市值漂移的横截面超额排序 (`label_excess_rank`)。

输入：  C:/Data/Market/us/us_features_neutral.parquet
输出：  models/us_lgbm_neutral.pkl
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "features")))
from validate_pipeline import l1_data_integrity_check

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import MODEL_DIR

FEATURES_PATH = r"C:\Data\Market\us\us_features_neutral.parquet"
MODEL_PATH    = os.path.join(MODEL_DIR, "us_lgbm_neutral.pkl")

# 使用行业中性化版本的特征
FEATURE_COLS = [
    "mom_1m_sec_rank", "mom_3m_sec_rank", "mom_6m_sec_rank", "mom_12m_sec_rank", 
    "vol_60d_res_sec_rank", "mom_1m_res_sec_rank", 
    "vol_20d_sec_rank", "vol_60d_sec_rank", "vol_120d_sec_rank", 
    "ROE_sec_rank", "Net_Margin_sec_rank", 
    "Total Assets_YoY_sec_rank", "Diluted EPS_YoY_sec_rank"
]

def prepare_data(df: pd.DataFrame):
    """返回 (df_clean, X, y, q_sizes, valid_feats)。
    标签：截面内的纯超额收益排名 -> label_excess_rank -> 转化为 5 档 0~4
    """
    df = df[df["label_excess_rank"].notna()].copy().sort_values("report_date").reset_index(drop=True)

    for col in FEATURE_COLS:
        if col in df.columns:
            df[col] = df.groupby('report_date')[col].transform(lambda x: x.fillna(x.median()))
            df[col] = df[col].fillna(0.5)

    # 转化为 5 档
    pct = df.groupby("report_date")["label_excess_rank"].transform(lambda x: x.rank(pct=True))
    df["relevance"] = pd.cut(pct, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                             labels=[0, 1, 2, 3, 4], include_lowest=True).astype(int)

    valid_feats = [c for c in FEATURE_COLS if c in df.columns]
    
    X = df[valid_feats].values.astype(np.float32)
    y = df["relevance"].values.astype(np.int32)
    q_sizes = df.groupby("report_date", sort=True).size().values

    return df, X, y, q_sizes, valid_feats

def split_by_time(df: pd.DataFrame):
    dates = sorted(df["report_date"].unique())
    n = len(dates)
    n_train, n_val = int(n * 0.70), int(n * 0.15)
    
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
    print("=" * 60)
    print("  AlphaRanker — 绝密：行业市值双重中性化模型训练 (Neutral)")
    print("=" * 60)

    if not os.path.exists(FEATURES_PATH):
        print(f"[ERR] 特征文件不存在: {FEATURES_PATH}")
        return

    df = pd.read_parquet(FEATURES_PATH)
    # L1 检查使用新的中性化 Target
    l1_data_integrity_check(df, min_sample_size=3000, label_col="label_excess_rank")
    
    df["report_date"] = pd.to_datetime(df["report_date"])

    train_df, val_df, test_df, train_dates, val_dates, test_dates = split_by_time(df)
    
    tr_df, X_train, y_train, q_train, valid_feats = prepare_data(train_df)
    va_df, X_val,   y_val,   q_val,   _           = prepare_data(val_df)
    te_df, X_test,  y_test,  q_test,  _           = prepare_data(test_df)

    print(f"\n特征数: {len(valid_feats)} | 训练集: {len(X_train)} | 测试集: {len(X_test)}")

    lgb_train = lgb.Dataset(X_train, label=y_train, group=q_train, feature_name=valid_feats)
    lgb_val   = lgb.Dataset(X_val,   label=y_val,   group=q_val,   feature_name=valid_feats, reference=lgb_train)

    params = {
        "objective":         "lambdarank",
        "metric":            "ndcg",
        "ndcg_eval_at":      [5, 10, 20],
        "learning_rate":     0.05,
        "num_leaves":        31,
        "min_child_samples": 20,
        "feature_fraction":  0.9,
        "bagging_fraction":  0.9,
        "bagging_freq":      1,
        "lambda_l1":         0.1,
        "lambda_l2":         0.1,
        "verbose":           -1,
        "seed":              42,
    }

    print("\n[Start Training] 正在拟合去偏后的纯净特征...")
    model = lgb.train(
        params,
        lgb_train,
        num_boost_round=100,
        valid_sets=[lgb_train, lgb_val],
        callbacks=[lgb.early_stopping(stopping_rounds=10), lgb.log_evaluation(50)]
    )

    # 保存模型
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    
    importance = model.feature_importance(importance_type="gain")
    imp_df = pd.DataFrame({"feature": valid_feats, "importance_gain": importance})
    imp_df = imp_df.sort_values("importance_gain", ascending=False)
    
    print("\n[模型表现] — 特征重要性排位 (Gain):")
    print(imp_df.head(10))

    # 计算测试集 Rank IC (基于连续 Excess Return 来评测)
    preds = model.predict(X_test)
    te_df["preds"] = preds
    ic_list = []
    for date, grp in te_df.groupby("report_date"):
        if len(grp) > 5 and grp['label_3m_excess'].std() > 1e-6:
            from scipy.stats import spearmanr
            ic, _ = spearmanr(grp['preds'], grp['label_3m_excess'])
            ic_list.append(ic)
            
    print(f"\n>> [验证完成] 纯净中立化模型测试集 Mean Rank IC: {np.mean(ic_list):.4f}")
    
    # 获取最高波跟最低波在预测分最高一组的表现
    best_preds = te_df[te_df.groupby('report_date')['preds'].transform(lambda x: pd.qcut(x, 5, labels=False, duplicates='drop')) == 4]
    
    print("\n>> 顶部分组中，最高波 vs 最低波的平均超额:")
    if 'vol_60d_res_sec_rank' in best_preds.columns:
        best_preds['vol_q'] = best_preds.groupby('report_date')['vol_60d_res_sec_rank'].transform(lambda x: pd.qcut(x, 3, labels=['Low', 'Mid', 'High'], duplicates='drop') if len(x)>10 else ['Mid']*len(x))
        vol_ret = best_preds.groupby('vol_q')['label_3m_excess'].mean() * 100
        print(vol_ret)

if __name__ == "__main__":
    main()
