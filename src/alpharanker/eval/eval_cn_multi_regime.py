"""
eval_cn_multi_regime.py
=======================
A 股 Alpha Genome 长周期分状态验证脚本。
1. 加载 2019-2026 的增强特征库。
2. 合并无未来函数的宏观状态标签 (Bull/Bear)。
3. 分状态计算核心因子的 Rank IC，验证基因的普适性。
"""

import os
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import CN_DIR

FEATURES_PATH = os.path.join(CN_DIR, 'cn_features_enhanced.parquet')
MACRO_PATH    = os.path.join(CN_DIR, 'macro_regime.parquet')

def calculate_regime_ics(df, factor_cols, target_col):
    regimes = sorted(df["regime"].unique())
    results = []
    
    for r in regimes:
        r_label = "Bull (1)" if r == 1 else "Bear (0)"
        r_df = df[df["regime"] == r]
        
        dates = sorted(r_df["date"].unique())
        print(f"\n>> 分析状态: {r_label} (样本数: {len(r_df)}, 截面数: {len(dates)})")
        
        for f in factor_cols:
            ics = []
            for d in dates:
                grp = r_df[r_df["date"] == d]
                if len(grp) > 20:
                    ic, _ = spearmanr(grp[f], grp[target_col])
                    ics.append(ic)
            
            if ics:
                results.append({
                    "Regime": r_label,
                    "Factor": f,
                    "Mean Rank IC": np.mean(ics),
                    "IC Std": np.std(ics),
                    "IR": np.mean(ics) / (np.std(ics) + 1e-6),
                    "Positive Ratio": np.mean(np.array(ics) > 0)
                })
                
    return pd.DataFrame(results)

def main():
    print("="*60)
    print("  Alpha Genome: A 股多状态长周期实证 (2019-2026)")
    print("="*60)
    
    if not os.path.exists(FEATURES_PATH) or not os.path.exists(MACRO_PATH):
        print("❌ 缺少必要的数据文件。请先运行特征工程和宏观抓取脚本。")
        return

    # 1. 加载数据
    print("Loading data...")
    df = pd.read_parquet(FEATURES_PATH)
    macro = pd.read_parquet(MACRO_PATH)
    
    df["date"] = pd.to_datetime(df["date"])
    macro["date"] = pd.to_datetime(macro["date"])
    
    # 2. 合并
    df = pd.merge(df, macro[["date", "regime"]], on="date", how="left")
    df["regime"] = df["regime"].ffill().fillna(0).astype(int)
    
    # 3. 核心基因
    factors = [
        "mom_60d_rank", "mom_20d_rank", 
        "vol_60d_res_rank", "sp_ratio_rank", 
        "roe_rank", "turn_20d_rank"
    ]
    
    # 4. 统计
    # 我们测试主要的下一月预测标签
    target = "label_next_month"
    df = df.dropna(subset=[target])
    
    res_df = calculate_regime_ics(df, factors, target)
    
    # 5. 展示
    print("\n" + "="*80)
    print("  分状态因子表现汇总表")
    print("="*80)
    
    pivot_ic = res_df.pivot(index="Factor", columns="Regime", values="Mean Rank IC")
    pivot_ir = res_df.pivot(index="Factor", columns="Regime", values="IR")
    
    print("\n[Mean Rank IC Comparison]")
    print(pivot_ic.to_string())
    
    print("\n[Information Ratio (IR) Comparison]")
    print(pivot_ir.to_string())
    
    # 结论分析
    print("\n>> 因子敏感度分析:")
    for f in factors:
        bull_ic = pivot_ic.loc[f, "Bull (1)"]
        bear_ic = pivot_ic.loc[f, "Bear (0)"]
        diff = bull_ic - bear_ic
        print(f"- {f:20}: Bull IC={bull_ic:+.4f}, Bear IC={bear_ic:+.4f}, Diff={diff:+.4f}")

    print("\n="*80)

if __name__ == "__main__":
    main()
