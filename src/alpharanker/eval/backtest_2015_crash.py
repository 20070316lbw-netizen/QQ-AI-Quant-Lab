import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import CN_DIR
from alpharanker.configs.cap_aware_weights import get_weights

FEATURES_PATH = os.path.join(CN_DIR, 'cn_features_enhanced.parquet')
MACRO_PATH = os.path.join(CN_DIR, 'macro_regime.parquet')

def backtest_strategy(df, group="HS300", weights=None, rebalance_days=20):
    """
    简易回测：按 Alpha Score 排序，取前 20% 持有 20 天。
    """
    g_df = df[df['index_group'] == group].copy()
    if g_df.empty:
        return None
    
    dates = sorted(g_df['date'].unique())
    rebalance_dates = dates[::rebalance_days]
    
    portfolio_returns = []
    
    for i in range(len(rebalance_dates) - 1):
        d_start = rebalance_dates[i]
        d_end = rebalance_dates[i+1]
        
        # 截面选择
        sect = g_df[g_df['date'] == d_start].copy()
        
        # 计算 Alpha
        sect['score'] = 0
        for f, w in weights.items():
            if f in sect.columns:
                sect['score'] += sect[f] * w
        
        # 选股 Top 20%
        top_n = max(1, int(len(sect) * 0.2))
        portfolio = sect.sort_values('score', ascending=False).head(top_n)['ticker'].tolist()
        
        # 计算持仓期收益 (简单平均)
        # 寻找这些股票在下一个调仓日的价格
        hold_df = g_df[(g_df['date'] == d_end) & (g_df['ticker'].isin(portfolio))]
        if not hold_df.empty:
            # 这里简化，用 label_20d 或者实际价格差
            # 我们用实际价格差来更真实一点
            p_start = sect[sect['ticker'].isin(portfolio)].set_index('ticker')['raw_close']
            p_end = hold_df.set_index('ticker')['raw_close']
            
            # 对齐数据
            ret = (p_end / p_start - 1).mean()
            portfolio_returns.append({
                'date': d_end,
                'return': ret,
                'regime': sect['regime_label'].iloc[0] if 'regime_label' in sect.columns else 'Unknown'
            })
            
    return pd.DataFrame(portfolio_returns)

def main():
    print("="*80)
    print("  Alpha Genome: 2015 极值周期生存压力回测 (Phase 13)")
    print("="*80)

    if not os.path.exists(FEATURES_PATH):
        print("❌ 特征库不存在，请先运行 build_enhanced_features_cn.py")
        return

    df = pd.read_parquet(FEATURES_PATH)
    # 过滤 2015 年数据
    df = df[(df['date'] >= '2015-01-01') & (df['date'] <= '2016-01-01')]
    if df.empty:
        print("⚠️ 2015 年数据尚未抓取完成或处理完成。")
        return

    # 合并指数分层和宏观标签 (此处假设已经由构建脚本完成，如未完成则需在此补足)
    # ... 类似 eval_cn_oos_consistency.py 的逻辑 ...
    
    # 实际上 build_enhanced_features_cn.py 已经处理了大部分，但 index_group 需外部读取
    INDEX_MAP_PATH = os.path.join(CN_DIR, 'index_map.parquet')
    if os.path.exists(INDEX_MAP_PATH):
        index_map = pd.read_parquet(INDEX_MAP_PATH)
        index_map['ticker'] = index_map['code'].apply(lambda x: x.split(".")[1] + (".SS" if x.startswith("sh") else ".SZ"))
        df = pd.merge(df, index_map[['ticker', 'index_group']], on='ticker', how='left')

    if os.path.exists(MACRO_PATH):
        macro = pd.read_parquet(MACRO_PATH)
        macro['regime_label'] = macro['regime'].map({0: 'Bear', 1: 'Bull'})
        df = pd.merge(df, macro[['date', 'regime_label']], on='date', how='left')

    for group in ["HS300", "ZZ500"]:
        print(f"\n>> 正在对 {group} 进行 2015 雪崩回测...")
        weights = get_weights(group, horizon_days=20)
        
        bt_res = backtest_strategy(df, group=group, weights=weights)
        if bt_res is not None and not bt_res.empty:
            bt_res['cum_ret'] = (1 + bt_res['return']).cumprod()
            print(bt_res)
            
            final_nav = bt_res['cum_ret'].iloc[-1]
            max_drawdown = (bt_res['cum_ret'] / bt_res['cum_ret'].expanding().max() - 1).min()
            
            print(f"[{group}] Final NAV: {final_nav:.4f}")
            print(f"[{group}] Max Drawdown: {max_drawdown*100:.2f}%")
        else:
            print(f"⚠️ {group} 样本量不足，无法回测。")

if __name__ == "__main__":
    main()
