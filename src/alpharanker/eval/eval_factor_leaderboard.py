import os
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import lightgbm as lgb
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import CN_DIR

FEATURES_PATH = os.path.join(CN_DIR, 'cn_features_enhanced.parquet')
SAVE_LEADERBOARD_PATH = os.path.join(CN_DIR, 'factor_leaderboard.parquet')

def calculate_ic_metrics(df, factor_cols, target_col='label_next_month'):
    """计算因子的 Rank IC 指标"""
    ic_results = []
    dates = sorted(df["date"].unique())
    
    for f in tqdm(factor_cols, desc="Calculating ICs"):
        ics = []
        for d in dates:
            grp = df[df["date"] == d]
            mask = grp[[f, target_col]].notna().all(axis=1)
            if mask.sum() > 20:
                ic, _ = spearmanr(grp.loc[mask, f], grp.loc[mask, target_col])
                ics.append(ic)
        
        if ics:
            ic_mean = np.mean(ics)
            ic_std = np.std(ics)
            ir = ic_mean / ic_std if ic_std != 0 else 0
            ic_series = pd.Series(ics)
            winning_rate = (ic_series > 0).mean()
            ic_results.append({
                "factor": f,
                "ic_mean": ic_mean,
                "ir": ir,
                "winning_rate": winning_rate,
                "ic_std": ic_std
            })
            
    return pd.DataFrame(ic_results)

def get_feature_importance(df, feature_cols, target_col='label_next_month_rank'):
    """使用 LightGBM LambdaRank 训练并提取特征重要性 (Gain)"""
    # 优先使用预计算好的 Rank Label
    if target_col not in df.columns:
        if 'label_next_month' in df.columns:
            # 回退逻辑：如果没找到预计算标签，实时进行 5 分箱
            print(f"Warning: {target_col} not found, calculating on-the-fly...")
            df = df.copy()
            df[target_col] = df.groupby('date')['label_next_month'].transform(
                lambda x: pd.qcut(x, 5, labels=False, duplicates='drop') if len(x) >= 5 else 0
            )
        else:
            return pd.Series(0, index=feature_cols)

    print(f"Training LightGBM LambdaRank to extract feature importance (Target: {target_col})...")
    
    # 必须按日期排序以构造分组信息 (query/group sizes)
    train_df = df.dropna(subset=feature_cols + [target_col]).sort_values("date")
    if len(train_df) < 1000:
        return pd.Series(0, index=feature_cols)
        
    X = train_df[feature_cols].values.astype(np.float32)
    y = train_df[target_col].values.astype(np.int32)
    q_sizes = train_df.groupby("date", sort=False).size().values
    
    # 采用与 Alpha Genome 主模型一致的参数
    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "random_state": 42,
        "label_gain": [0, 1, 2, 3, 4] # 对应 [0-4] Rank Label
    }
    
    dtrain = lgb.Dataset(X, label=y, group=q_sizes)
    model = lgb.train(params, dtrain, num_boost_round=100)
    
    importance = model.feature_importance(importance_type='gain')
    return pd.Series(importance, index=feature_cols)

def main():
    print("="*80)
    print("  Alpha Genome: 全维因子排行榜 (Alpha Leaderboard)")
    print("="*80)

    if not os.path.exists(FEATURES_PATH):
        print(f"❌ 缺少特征数据: {FEATURES_PATH}")
        return

    df = pd.read_parquet(FEATURES_PATH)
    
    # 筛选待评价的因子 (带 _rank 的即为中性化后的主基因)
    candidate_factors = [c for c in df.columns if c.endswith("_rank") and c != "label_next_month_rank"]
    
    # 1. 计算 IC 指标
    ic_df = calculate_ic_metrics(df, candidate_factors)
    
    # 2. 计算特征重要性 (Gain) - 使用 LambdaRank 模式对齐主逻辑
    importance_series = get_feature_importance(df, candidate_factors, target_col='label_next_month_rank')
    ic_df["importance_gain"] = ic_df["factor"].map(importance_series)
    
    # 3. 综合评分 (权重分配: 0.4*IC + 0.3*IR + 0.3*Importance)
    # 先做归一化处理
    for col in ["ic_mean", "ir", "importance_gain"]:
        col_abs = ic_df[col].abs()
        denom = col_abs.max() - col_abs.min()
        ic_df[f"{col}_norm"] = (col_abs - col_abs.min()) / (denom + 1e-9)
    
    ic_df["composite_score"] = (
        0.4 * ic_df["ic_mean_norm"] + 
        0.3 * ic_df["ir_norm"] + 
        0.3 * ic_df["importance_gain_norm"]
    )
    
    leaderboard = ic_df.sort_values("composite_score", ascending=False).reset_index(drop=True)
    
    print("\n" + "="*80)
    print("  因子排行榜 TOP 10 (LambdaRank Gain 对齐版)")
    print("="*80)
    print(leaderboard[["factor", "ic_mean", "ir", "importance_gain", "composite_score"]].head(10).to_string())
    
    # 保存结果
    leaderboard.to_parquet(SAVE_LEADERBOARD_PATH)
    print(f"\n✅ 排行榜已保存至: {SAVE_LEADERBOARD_PATH}")

if __name__ == "__main__":
    main()
