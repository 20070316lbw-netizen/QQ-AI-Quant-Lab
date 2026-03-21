import os
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import statsmodels.api as sm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import CN_DIR
from alpharanker.configs.cap_aware_weights import get_weights

FEATURES_PATH = os.path.join(CN_DIR, 'cn_features_enhanced.parquet')
INDEX_MAP_PATH = os.path.join(CN_DIR, 'index_map.parquet')
MACRO_PATH = os.path.join(CN_DIR, 'macro_regime.parquet')

def calculate_ic(df, factor_col, target_col):
    ics = []
    for date, grp in df.groupby('date'):
        if len(grp) > 20:
            mask = grp[[factor_col, target_col]].notna().all(axis=1)
            if mask.sum() > 10:
                ic, _ = spearmanr(grp.loc[mask, factor_col], grp.loc[mask, target_col])
                ics.append(ic)
    return np.mean(ics) if ics else np.nan

def estimate_turnover(df, factor_col):
    """
    估算月度换手率。
    通过计算相邻截面（20d）持仓股票的 Rank 变动来估算。
    这里简化处理：计算同一股票在 T 和 T+1 截面的排名差。
    """
    turnovers = []
    dates = sorted(df['date'].unique())
    # 假设 20 个交易日调一次仓，我们取 20d 间隔的截面
    rebalance_dates = dates[::20] 
    
    for i in range(len(rebalance_dates) - 1):
        d1, d2 = rebalance_dates[i], rebalance_dates[i+1]
        g1 = df[df['date'] == d1][['ticker', factor_col]].dropna()
        g2 = df[df['date'] == d2][['ticker', factor_col]].dropna()
        
        # 仅考虑 Top 20% 的股票（模拟持仓）
        top_n1 = int(len(g1) * 0.2)
        top_n2 = int(len(g2) * 0.2)
        if top_n1 == 0 or top_n2 == 0: continue
        
        s1 = set(g1.sort_values(factor_col, ascending=False).head(top_n1)['ticker'])
        s2 = set(g2.sort_values(factor_col, ascending=False).head(top_n2)['ticker'])
        
        # 换手率 = (新进 - 留存) / 总持仓 (简化版)
        intersect = s1.intersection(s2)
        turnover = (len(s1) - len(intersect)) / len(s1)
        turnovers.append(turnover)
        
    return np.mean(turnovers) if turnovers else np.nan

def main():
    print("="*80)
    print("  Alpha Genome: A 股样本外一致性与压力测试 (Phase 12)")
    print("="*80)

    if not os.path.exists(FEATURES_PATH) or not os.path.exists(INDEX_MAP_PATH):
        print("❌ 缺少数据。")
        return

    df = pd.read_parquet(FEATURES_PATH)
    index_map = pd.read_parquet(INDEX_MAP_PATH)
    index_map['ticker'] = index_map['code'].str.split(".").str[1] + np.where(index_map['code'].str.startswith("sh"), ".SS", ".SZ")
    df = pd.merge(df, index_map[['ticker', 'index_group']], on='ticker', how='left')
    
    if os.path.exists(MACRO_PATH):
        macro = pd.read_parquet(MACRO_PATH)
        # 映射 regime (0: Bear, 1: Bull) 到 regime_label
        macro['regime_label'] = macro['regime'].map({0: 'Bear', 1: 'Bull'})
        df = pd.merge(df, macro[['date', 'regime_label']], on='date', how='left')
    else:
        df['regime_label'] = 'Neutral'

    # 时段划分
    split_date = pd.to_datetime('2024-01-01')
    df_is = df[df['date'] < split_date]
    df_oos = df[df['date'] >= split_date]

    print(f"\n[Regime Audit]")
    print(f"IS (2021-2023) Bull%: { (df_is['regime_label']=='Bull').mean()*100:.1f}%")
    print(f"OOS (2024-2026) Bull%: { (df_oos['regime_label']=='Bull').mean()*100:.1f}%")

    results = []
    regime_results = []

    for group in ["HS300", "ZZ500"]:
        print(f"\n>> 正在处理: {group}")
        # 权重固定在 20d 逻辑，但测试不同调仓频率的效果
        weights = get_weights(group, horizon_days=20)
        
        # 计算复合 Alpha
        def calc_alpha(sub_df, w):
            alpha = 0
            for f, val in w.items():
                if f in sub_df.columns:
                    alpha += sub_df[f] * val
            return alpha

        for horizon in [20, 60]:
            label_col = f'label_{horizon}d'
            print(f"   --- Testing Horizon: {horizon}d ---")
            
            for period_name, p_df in [("IS", df_is), ("OOS", df_oos)]:
                g_df = p_df[p_df['index_group'] == group].copy()
                if g_df.empty: continue
                
                g_df['alpha_score'] = calc_alpha(g_df, weights)
                
                # 1. 基础 IC 汇总
                ic_val = calculate_ic(g_df, 'alpha_score', label_col)
                # 换手率估算：按对应 horizon 间隔
                turnover = estimate_turnover_by_horizon(g_df, 'alpha_score', horizon)
                
                results.append({
                    "Group": group,
                    "Horizon": f"{horizon}d",
                    "Period": period_name,
                    "Mean IC": ic_val,
                    "Turnover": turnover
                })

                # 2. 时段 x 状态交叉审计 (仅针对 20d 频率)
                if horizon == 20:
                    for regime in ['Bull', 'Bear']:
                        r_df = g_df[g_df['regime_label'] == regime]
                        if not r_df.empty:
                            r_ic = calculate_ic(r_df, 'alpha_score', label_col)
                            regime_results.append({
                                "Group": group,
                                "Period": period_name,
                                "Regime": regime,
                                "IC": r_ic,
                                "Samples": len(r_df)
                            })

    # 输出汇总
    res_df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("  IS vs OOS 多周期对比汇总")
    print("="*80)
    print(res_df.to_string(index=False))

    reg_df = pd.DataFrame(regime_results)
    print("\n" + "="*80)
    print("  时段 × 状态交叉 IC 审计 (Regime-Conditional IC)")
    print("="*80)
    if not reg_df.empty:
        pivot = reg_df.pivot_table(index=['Group', 'Regime'], columns='Period', values='IC')
        print(pivot.to_string())
    else:
        print("No regime data found.")

def estimate_turnover_by_horizon(df, factor_col, horizon):
    dates = sorted(df['date'].unique())
    rebalance_dates = dates[::horizon] 
    
    turnovers = []
    for i in range(len(rebalance_dates) - 1):
        d1, d2 = rebalance_dates[i], rebalance_dates[i+1]
        g1 = df[df['date'] == d1][['ticker', factor_col]].dropna()
        g2 = df[df['date'] == d2][['ticker', factor_col]].dropna()
        
        top_n1 = int(len(g1) * 0.2)
        top_n2 = int(len(g2) * 0.2)
        if top_n1 <= 5 or top_n2 <= 5: continue
        
        s1 = set(g1.sort_values(factor_col, ascending=False).head(top_n1)['ticker'])
        s2 = set(g2.sort_values(factor_col, ascending=False).head(top_n2)['ticker'])
        
        intersect = s1.intersection(s2)
        turnover = (len(s1) - len(intersect)) / len(s1)
        turnovers.append(turnover)
        
    return np.mean(turnovers) if turnovers else np.nan

if __name__ == "__main__":
    main()
