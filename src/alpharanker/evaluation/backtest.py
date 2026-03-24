"""
backtest.py
===========
基于 AlphaRanker 预测排名进行简单的 Top-K 模拟回测。
支持：
  - 月度调仓模拟
  - 累计收益率计算
  - 夏普比率、最大回撤
  - 与等权基准对比
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def run_backtest(df, top_k=50, label_col="label_next_month"):
    """
    运行 Top-K 回测
    df 必须包含: date, ticker, pred_rank, 以及实际收益率列 (label_col)
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    # 1. 筛选每月 Top-K 标的
    # 使用向量化的 sort_values().groupby().head() 代替原生的 groupby().apply()
    portfolio_ret = (
        df.sort_values(['date', 'pred_rank'], ascending=[True, False])
        .groupby('date')
        .head(top_k)
        .groupby('date')[label_col]
        .mean()
    )
    
    # 2. 计算基准 (全样本等权)
    benchmark_ret = df.groupby('date')[label_col].mean()
    
    # 3. 计算累计收益
    results = pd.DataFrame({
        'portfolio': (1 + portfolio_ret).cumprod(),
        'benchmark': (1 + benchmark_ret).cumprod()
    })
    
    # 4. 计算指标
    strategy_ret = results['portfolio'].pct_change().dropna()
    sharpe = np.sqrt(12) * strategy_ret.mean() / strategy_ret.std()
    
    cum_ret = results['portfolio']
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / running_max
    mdd = drawdown.min()
    
    print("\n" + "="*40)
    print("      AlphaRanker 回测报告 (Top-K)")
    print("="*40)
    print(f"调仓频率:  每月")
    print(f"持仓数量:  {top_k}")
    print(f"累计收益:  {results['portfolio'].iloc[-1]-1:.2%}")
    print(f"超额收益:  {results['portfolio'].iloc[-1] - results['benchmark'].iloc[-1]:.2%}")
    print(f"夏普比率:  {sharpe:.2f}")
    print(f"最大回撤:  {mdd:.2%}")
    print("="*40)
    
    return results

if __name__ == "__main__":
    print("回测引擎就绪。请在模型评估阶段调用 run_backtest(pred_df)。")
