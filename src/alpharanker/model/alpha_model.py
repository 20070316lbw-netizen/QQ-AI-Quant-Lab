"""
alpha_model.py
==============
封装 LightGBM LambdaRanker 的训练、验证与推理逻辑。

核心功能:
  - 按日期 (Group) 划分训练集与测试集
  - 自动化训练 LambdaRank (LTR) 模型
  - 多因子排名预测 (Cross-sectional Ranking)
"""

import os
import joblib
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import ndcg_score

class AlphaRanker:
    def __init__(self, model_params=None):
        self.params = model_params or {
            'objective': 'lambdarank',
            'metric': 'ndcg',
            'ndcg_at': [1, 3, 5, 10],
            'learning_rate': 0.05,
            'num_leaves': 31,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'n_estimators': 500,
            'importance_type': 'gain',
            'verbose': -1
        }
        self.model = None
        self.feature_cols = []
        self.categorical_cols = []

    def prepare_data(self, df, feature_cols, label_col='label_rank'):
        """
        准备 LightGBM 数据集：按日期排序并记录 Group 信息
        """
        # 必须按日期排序，LambdaRank 需要相同日期的行连在一起
        df = df.sort_values('date').reset_index(drop=True)
        
        # 处理类别特征 (Label Encoding)
        X = df[feature_cols].copy()
        for col in self.categorical_cols:
            if col in X.columns:
                X[col] = X[col].astype('category').cat.codes
        
        y = df[label_col]
        
        # 记录每个日期的行数 (Groups)
        group_counts = df.groupby('date').size().to_list()
        
        return X, y, group_counts

    def train(self, train_df, val_df, feature_cols, label_col='label_rank', categorical_cols=None):
        self.feature_cols = feature_cols
        self.categorical_cols = categorical_cols or []
        
        X_train, y_train, group_train = self.prepare_data(train_df, feature_cols, label_col)
        X_val, y_val, group_val = self.prepare_data(val_df, feature_cols, label_col)
        
        print(f"训练集: {len(X_train)} 行, {len(group_train)} 组")
        print(f"验证集: {len(X_val)} 行, {len(group_val)} 组")
        if self.categorical_cols:
            print(f"类别特征: {self.categorical_cols}")

        self.model = lgb.LGBMRanker(**self.params)
        self.model.fit(
            X_train, y_train,
            group=group_train,
            eval_set=[(X_val, y_val)],
            eval_group=[group_val],
            categorical_feature=self.categorical_cols if self.categorical_cols else 'auto',
            callbacks=[lgb.early_stopping(stopping_rounds=50)]
        )
        return self

    def predict(self, df):
        """对输入的横截面数据进行排名预测"""
        if self.model is None:
            raise ValueError("模型未训练！")
        
        X = df[self.feature_cols]
        # 获取原始预测分 (Score)
        scores = self.model.predict(X)
        
        # 将分数转化为横截面排名百分比 (0-1)
        res_df = df.copy()
        res_df['rank_score'] = scores
        res_df['pred_rank'] = res_df.groupby('date')['rank_score'].rank(pct=True)
        
        return res_df

    def save(self, path):
        joblib.dump(self.model, path)
        print(f"模型已保存至: {path}")

    def load(self, path):
        self.model = joblib.load(path)
        print(f"模型已从 {path} 加载")

# ---------------------------------------------------------
# 使用示例与测试逻辑
if __name__ == "__main__":
    print("AlphabetRanker Model Core Module Loaded.")
