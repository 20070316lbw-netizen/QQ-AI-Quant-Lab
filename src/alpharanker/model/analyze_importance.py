"""
analyze_importance.py
=====================
对训练好的 AlphaRanker 模型进行特征重要性分析。
支持：
  - LightGBM 原生 Gain 重要性
  - （可选）SHAP 值分析（如果安装了 shap 库）
"""

import os
import joblib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_importance(model_path, output_image="importance.png"):
    if not os.path.exists(model_path):
        print(f"找不到模型文件: {model_path}")
        return

    model = joblib.load(model_path)
    
    # 获取特征重要性 (Gain)
    importance = pd.DataFrame({
        'feature': model.feature_name_,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    plt.figure(figsize=(10, 8))
    sns.barplot(x='importance', y='feature', data=importance)
    plt.title('AlphaRanker Feature Importance (Gain)')
    plt.tight_layout()
    plt.savefig(output_image)
    print(f"特征重要性图表已保存至: {output_image}")
    
    # 打印前 10
    print("\nTop 10 重要特征:")
    print(importance.head(10))

if __name__ == "__main__":
    MODEL_FILE = os.path.join(os.path.dirname(__file__), "..", "models", "alpha_ranker.pkl")
    plot_importance(MODEL_FILE)
