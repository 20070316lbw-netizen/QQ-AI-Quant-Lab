"""
search_best_genome_us.py
========================
Alpha Genome 集成与消融实验 (Ablation Study)。
目标：通过组合不同的因子簇，寻找美股全时段及特定 Regime 下的最佳特征组合。

因子簇定义：
- Momentum (M): mom_1m_sec_rank, ..., mom_12m_sec_rank
- Volatility (V): vol_60d_res_sec_rank, mom_1m_res_sec_rank
- Quality (Q): Asset_Turnover_sec_rank, ROA_sec_rank, Cash_to_Liabilities_sec_rank
- Value (L): SP_sec_rank
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import spearmanr

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

FEAT_PATH = r"C:\Data\Market\us\us_features_enhanced.parquet"

GENOMES = {
    "Base_Momentum": ["mom_1m_sec_rank", "mom_3m_sec_rank", "mom_6m_sec_rank", "mom_12m_sec_rank"],
    "Gen_V1 (M+V)": ["mom_1m_sec_rank", "mom_3m_sec_rank", "mom_6m_sec_rank", "mom_12m_sec_rank", 
                    "vol_60d_res_sec_rank", "mom_1m_res_sec_rank"],
    "Gen_V2_Q (M+V+Q)": ["mom_1m_sec_rank", "mom_3m_sec_rank", "mom_6m_sec_rank", "mom_12m_sec_rank", 
                         "vol_60d_res_sec_rank", "mom_1m_res_sec_rank",
                         "Asset_Turnover_sec_rank", "ROA_sec_rank", "Cash_to_Liabilities_sec_rank"],
    "Gen_V2_V (M+V+L)": ["mom_1m_sec_rank", "mom_3m_sec_rank", "mom_6m_sec_rank", "mom_12m_sec_rank", 
                         "vol_60d_res_sec_rank", "mom_1m_res_sec_rank", "SP_sec_rank"],
    "Gen_Full (M+V+Q+L)": ["mom_1m_sec_rank", "mom_3m_sec_rank", "mom_6m_sec_rank", "mom_12m_sec_rank", 
                           "vol_60d_res_sec_rank", "mom_1m_res_sec_rank",
                           "Asset_Turnover_sec_rank", "ROA_sec_rank", "Cash_to_Liabilities_sec_rank",
                           "SP_sec_rank"]
}

def train_and_eval(df, features, genome_name):
    # 类别特征处理
    df_train = df[df['data_split'] == 'train'].copy()
    df_val = df[df['data_split'] == 'val'].copy()
    df_test = df[df['data_split'] == 'test'].copy()
    
    # 包含 regime_label 的话
    use_features = features + ["regime_label"]
    
    for col in features:
        df_train[col] = df_train[col].fillna(0.5)
        df_val[col] = df_val[col].fillna(0.5)
        df_test[col] = df_test[col].fillna(0.5)
        
    df_train["regime_label"] = df_train["regime_label"].astype('category')
    df_val["regime_label"] = df_val["regime_label"].astype('category')
    df_test["regime_label"] = df_test["regime_label"].astype('category')
    
    # Label
    df_train['relevance'] = pd.cut(df_train.groupby("report_date")["label_excess_rank"].transform(lambda x: x.rank(pct=True)), 
                                 bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=[0,1,2,3,4], include_lowest=True).astype(int)
    df_val['relevance'] = pd.cut(df_val.groupby("report_date")["label_excess_rank"].transform(lambda x: x.rank(pct=True)), 
                               bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=[0,1,2,3,4], include_lowest=True).astype(int)

    params = {
        "objective": "lambdarank", "metric": "ndcg", "learning_rate": 0.03,
        "num_leaves": 15, "min_child_samples": 5, "verbose": -1, "seed": 42
    }
    
    # 填补 & 确保类型
    X_train = df_train[use_features].fillna(0.5)
    X_val = df_val[use_features].fillna(0.5)
    X_test = df_test[use_features].fillna(0.5)
    
    lgb_train = lgb.Dataset(X_train, label=df_train['relevance'], group=df_train.groupby("report_date").size().values, categorical_feature=["regime_label"])
    lgb_val = lgb.Dataset(X_val, label=df_val['relevance'], group=df_val.groupby("report_date").size().values, reference=lgb_train, categorical_feature=["regime_label"])
    
    model = lgb.train(params, lgb_train, num_boost_round=150, valid_sets=[lgb_val], 
                      callbacks=[lgb.early_stopping(20), lgb.log_evaluation(0)])
    
    preds = model.predict(X_test)
    df_test['preds'] = preds
    
    # 计算全时段 IC
    ic_list = []
    for date, grp in df_test.groupby("report_date"):
        valid = grp.dropna(subset=['preds', 'label_3m_excess'])
        if len(valid) > 50 and valid['label_3m_excess'].std() > 1e-6:
            ic, _ = spearmanr(valid['preds'], valid['label_3m_excess'])
            ic_list.append(ic)
    
    # 分 Regime IC
    regime_results = {}
    for r in ['Bull', 'Bear']:
        r_grp = df_test[df_test['regime_label'] == r]
        ric_list = []
        for date, grp in r_grp.groupby("report_date"):
            valid = grp.dropna(subset=['preds', 'label_3m_excess'])
            if len(valid) > 50 and valid['label_3m_excess'].std() > 1e-6:
                ic, _ = spearmanr(valid['preds'], valid['label_3m_excess'])
                ric_list.append(ic)
        regime_results[r] = np.mean(ric_list) if ric_list else np.nan
        
    return np.mean(ic_list), regime_results

def main():
    print("="*60)
    print("  Alpha Genome: 因子组合消融实验 (Ablation Study)")
    print("="*60)
    
    df = pd.read_parquet(FEAT_PATH)
    df["report_date"] = pd.to_datetime(df["report_date"])
    dates = sorted(df["report_date"].unique())
    n = len(dates)
    train_dates = dates[:int(n*0.7)]
    val_dates = dates[int(n*0.7):int(n*0.85)]
    test_dates = dates[int(n*0.85):]
    
    df.loc[df["report_date"].isin(train_dates), "data_split"] = "train"
    df.loc[df["report_date"].isin(val_dates), "data_split"] = "val"
    df.loc[df["report_date"].isin(test_dates), "data_split"] = "test"
    
    final_results = []
    
    for name, feats in GENOMES.items():
        print(f">> 正在测试组合: {name} ...")
        mean_ic, r_ic = train_and_eval(df, feats, name)
        final_results.append({
            "Genome": name,
            "Total_IC": mean_ic,
            "Bull_IC": r_ic['Bull'],
            "Bear_IC": r_ic['Bear']
        })
        print(f"   [DONE] IC: {mean_ic:.4f} | Bull: {r_ic['Bull']:.4f} | Bear: {r_ic['Bear']:.4f}")
        
    print("\n" + "="*60)
    print("  Alpha Genome 消融实验最终榜单")
    print("="*60)
    res_df = pd.DataFrame(final_results).sort_values("Total_IC", ascending=False)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    main()
