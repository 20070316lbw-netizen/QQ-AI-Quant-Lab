"""
eval_realtime_cn.py
====================
对增量同步后的 A 股最新行情进行样本外验证。
计算最近 10 天各因子的 Rank IC，验证 Alpha Genome 的时效性。
"""

import os
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import CN_DIR

FEATURES_PATH = os.path.join(CN_DIR, 'cn_features_enhanced.parquet')

def main():
    print("="*60)
    print("  Alpha Genome: A 股实时行情极限验证 (2026-03)")
    print("="*60)
    
    if not os.path.exists(FEATURES_PATH):
        print(f"❌ 未找到特征文件: {FEATURES_PATH}，请先运行 build_enhanced_features_cn.py")
        return

    df = pd.read_parquet(FEATURES_PATH)
    df["date"] = pd.to_datetime(df["date"])
    
    # 获取最近的数据日期
    max_date = df["date"].max()
    print(f"特征数据最后截面: {max_date.date()}")
    
    # 锁定验证截面: 使用最新的这个横截面
    # 因为这个截面的 label_next_month 实际上反映了该日之后至今（即 3月1日-10日）的收益！
    val_window = df[df["date"] == max_date].copy()
    
    if val_window.empty:
        print("⚠️ 警告：在此日期下未找到有效验证集。")
        return

    factors = ["mom_60d_rank", "vol_60d_res_rank", "sp_ratio_rank"]
    
    print(f"\n[实时测试样本数]: {len(val_window)}")
    print(f"周期跨度: {val_window['date'].min().date()} 至 {val_window['date'].max().date()}")
    
    # --- 挂载自动化因子监控 ---
    from factor_monitor import FactorMonitor
    fm = FactorMonitor()
    
    # 为了展示多周期，现在我们评估不同标签周期下的单因子 IC
    from alpharanker.utils.experiment_tracker import ExperimentTracker
    from config import LOG_SYNC_JSON
    tracker = ExperimentTracker(sync_path=LOG_SYNC_JSON)

    labels_to_eval = [col for col in val_window.columns if col.startswith("label_")]
    if not labels_to_eval:
        labels_to_eval = ["label_next_month"]
    
    all_res = {}
    for t_col in labels_to_eval:
        print(f"\n📈 评估前瞻预测周期: {t_col}")
        res_df = fm.generate_ic_report(val_window, factors, target_col=t_col)
        
        if not res_df.empty:
            res_dict = res_df.set_index("因子/特征")["Rank IC"].to_dict()
            all_res[t_col] = res_dict
            
            # 使用 JSON Tracker 记录每次实验
            tracker.log_experiment(
                dataset_name="A股_实时池 (HS300+CSI500)",
                horizon=t_col.replace('label_', ''),
                features=factors,
                questions="探讨美股沉淀的 M+V+L 基因序列在最新 A 股市场环境（26年3月）下的防守与进攻表现。是否存在统计学显著性？",
                methodology="将特征数据对齐至 2026-02-27 横截面，利用 shift(-d) 构建基于未来的前瞻收益率，然后对单一截面中的因子暴露度与收益率进行 Spearman Rank IC 相关性测试。",
                results=res_dict,
                notes=f"实时窗口验证 {max_date.date()} 截面，多周期自动化评定产出。"
            )

if __name__ == "__main__":
    main()

