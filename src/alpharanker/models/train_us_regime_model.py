"""
train_us_regime_model.py
=========================
多模态量化模型 (Regime-aware LambdaRank)。
核心思想：将我们在 Market World Model 中计算确定的 `regime_label` (Bull/Bear/Volatile/Neutral)
作为 LightGBM 原生的 Categorical Feature 输入。让决策树在分割节点时，自动依据当前宏观环境
选取更适合的因子，动态调整高低波与动量因子的权重，完成端到端的「状态自适应」。

由于树模型的天然特性，这就是一种隐式的 Mixture of Experts 系统。
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

FEATURES_PATH = r"C:\Data\Market\us\us_features_enhanced.parquet"
MODEL_PATH    = os.path.join(MODEL_DIR, "us_lgbm_regime_v2.pkl")

# 正式集结 Alpha Genome 扩展军团
FEATURE_COLS = [
    # 动量片段
    "mom_1m_sec_rank", "mom_3m_sec_rank", "mom_6m_sec_rank", "mom_12m_sec_rank", 
    # 纯净波动率片段
    "vol_60d_res_sec_rank", "mom_1m_res_sec_rank", 
    # 质量(Quality)片段 - 经评估正向
    "Asset_Turnover_sec_rank", "ROA_sec_rank", "Cash_to_Liabilities_sec_rank",
    # 价值(Value)片段 - 经评估正向
    "SP_sec_rank",
    # 宏观天气制导
    "regime_label"
]

def prepare_data(df: pd.DataFrame):
     
    df = df[df["label_excess_rank"].notna()].copy().sort_values("report_date").reset_index(drop=True)

    # 填充数值型特征
    numeric_cols = [c for c in FEATURE_COLS if c != "regime_label"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df.groupby('report_date')[col].transform(lambda x: x.fillna(x.median()))
            df[col] = df[col].fillna(0.5)

    # 将文本类别转化为 categorical
    if "regime_label" in df.columns:
        df["regime_label"] = df["regime_label"].astype('category')

    # 转化为 5 档
    pct = df.groupby("report_date")["label_excess_rank"].transform(lambda x: x.rank(pct=True))
    df["relevance"] = pd.cut(pct, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                             labels=[0, 1, 2, 3, 4], include_lowest=True).astype(int)

    valid_feats = [c for c in FEATURE_COLS if c in df.columns]
    
    # 抽取 X (此时包含数值及 category 类容)
    X = df[valid_feats]
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
    print("  AlphaRanker — 多模态演化: 环境自适应排序模型 (Regime-Aware)")
    print("=" * 60)

    if not os.path.exists(FEATURES_PATH):
        print(f"[ERR] 特征文件不存在: {FEATURES_PATH}")
        return

    df = pd.read_parquet(FEATURES_PATH)
    l1_data_integrity_check(df, min_sample_size=3000, label_col="label_excess_rank")
    df["report_date"] = pd.to_datetime(df["report_date"])

    train_df, val_df, test_df, train_dates, val_dates, test_dates = split_by_time(df)
    
    tr_df, X_train, y_train, q_train, valid_feats = prepare_data(train_df)
    va_df, X_val,   y_val,   q_val,   _           = prepare_data(val_df)
    te_df, X_test,  y_test,  q_test,  _           = prepare_data(test_df)

    print(f"\n训练特征结构包含了 1 个 Market Regime 分类标签与 13 个中性化底层因子。")
    print(f"训练集: {len(X_train)} | 测试集: {len(X_test)}")

    # 必须明确告知 LightGBM 分类特征
    categorical_features = ['regime_label'] if 'regime_label' in valid_feats else []

    lgb_train = lgb.Dataset(X_train, label=y_train, group=q_train, feature_name=valid_feats, categorical_feature=categorical_features, free_raw_data=False)
    lgb_val   = lgb.Dataset(X_val,   label=y_val,   group=q_val,   feature_name=valid_feats, reference=lgb_train, categorical_feature=categorical_features, free_raw_data=False)

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

    print("\n[Start Training] 启动状态感知神经键组拟合...")
    model = lgb.train(
        params,
        lgb_train,
        num_boost_round=100,
        valid_sets=[lgb_train, lgb_val],
        callbacks=[lgb.early_stopping(stopping_rounds=10), lgb.log_evaluation(0)]
    )

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    
    # 因为有 categorical feature，importance 可以显示 regime_label 是否被选中
    importance = model.feature_importance(importance_type="gain")
    imp_df = pd.DataFrame({"feature": valid_feats, "importance_gain": importance}).sort_values("importance_gain", ascending=False)
    
    print("\n[模型表现] — 特征重要性排位 (Gain):")
    print(imp_df.head(10).to_string(index=False))

    # Test set Rank IC
    preds = model.predict(X_test)
    te_df["preds"] = preds
    ic_list = []
    
    # 评测全时通用的 Mean Rank IC
    for date, grp in te_df.groupby("report_date"):
        if len(grp) > 5 and grp['label_3m_excess'].std() > 1e-6:
            from scipy.stats import spearmanr
            ic, _ = spearmanr(grp['preds'], grp['label_3m_excess'])
            ic_list.append(ic)
            
    # 按 Regime 分割看能否稳住熊市退潮
    print(f"\n>> [验证完成] 宏观自适应模型 全时段 Mean Rank IC: {np.mean(ic_list):.4f}")
    
    print("\n>> 宏观自适应模型 分 Regime Mean Rank IC (防止某一时段大幅溃败):")
    for regime in ['Bull', 'Bear', 'Volatile']:
        sub_te = te_df[te_df['regime_label'] == regime]
        r_ic_list = []
        for date, grp in sub_te.groupby("report_date"):
            if len(grp) > 5 and grp['label_3m_excess'].std() > 1e-6:
                from scipy.stats import spearmanr
                ic, _ = spearmanr(grp['preds'], grp['label_3m_excess'])
                r_ic_list.append(ic)
        val = np.mean(r_ic_list) if r_ic_list else np.nan
        print(f"   [{regime:8s}]: {val:.4f}")

if __name__ == "__main__":
    main()
