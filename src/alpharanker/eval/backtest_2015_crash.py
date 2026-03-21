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

def backtest_strategy(df, group="HS300", weights=None, rebalance_days=1):
    """
    简易回测：按 Alpha Score 排序，取前 20% 持有 1 个月 (步长适配月度面板)。
    """
    g_df = df[df['index_group'] == group].copy()
    if g_df.empty:
        return None
    
    dates = sorted(g_df['date'].unique())
    # 适配月度面板：如果 rebalance_days=20 会导致 20 个月才调仓一次
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
        portfolio_df = sect.sort_values('score', ascending=False).head(top_n)
        portfolio = portfolio_df['ticker'].tolist()
        
        # 持仓期收益计算 
        # p_start: 调仓起始日价格
        p_start = portfolio_df.set_index('ticker')['raw_close']
        
        # p_end: 调仓结束日价格 (寻找这些股票在下一个调仓日的价格)
        hold_df = g_df[(g_df['date'] == d_end) & (g_df['ticker'].isin(portfolio))]
        p_end = hold_df.set_index('ticker')['raw_close']
        
        # --- 核心修复: 幸存者偏差保护 (Survivor Bias Protection) ---
        # 如果股票在 d_end 缺失（停牌/退市），不能简单平均，否则会遗漏损失
        common_tickers = p_start.index.intersection(p_end.index)
        missing_tickers = p_start.index.difference(p_end.index)
        
        # 正常对齐部分的收益
        rets_aligned = p_end[common_tickers] / p_start[common_tickers] - 1
        
        # 缺失部分的收益 (视为退市或长期停牌无法卖出，计为 -1.0)
        # 在 2015 年极限测试中，这种处理能更真实地反映回撤
        rets_missing = pd.Series(-1.0, index=missing_tickers)
        
        if len(missing_tickers) > 0:
            print(f"  [!] {d_end.date()} 检测到 {len(missing_tickers)} 只选股成分缺失 (停牌/退市)，计入全损。")
            
        combined_rets = pd.concat([rets_aligned, rets_missing])
        ret = combined_rets.mean()
        
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
        index_map['ticker'] = index_map['code'].str.split(".").str[1] + np.where(index_map['code'].str.startswith("sh"), ".SS", ".SZ")
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
