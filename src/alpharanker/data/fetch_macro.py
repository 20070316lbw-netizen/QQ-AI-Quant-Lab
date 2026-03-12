"""
fetch_macro.py
==============
抓取宏观市场数据（Market World Model 的基石），建立美股的 Regime 状态机。
核心指标：
- ^GSPC (S&P 500 指数) -> 用于判断长线多空趋势 (MA200过滤)
- ^VIX  (波动率指数) -> 用于判定市场恐慌/波动环境

判断逻辑：
- Bull (牛市): S&P 500 收盘价 > 200日均线, 并且 VIX < 20
- Volatile (震荡/恐慌): VIX > 25
- Bear (熊市/下行): 若非 Volatile 且 S&P 500 收盘价 < 200日均线
- Neutral: 其他情况
"""

import os
import sys
import yfinance as yf
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

OUTPUT_PATH = os.path.join(DATA_ROOT, 'us', 'macro_regime.parquet')

def fetch_and_build_regimes(start_date="2014-01-01"):
    print(f">> 开始抓取宏观市场数据 (从 {start_date} 至今)...")
    
    # 抓取标普500
    sp500 = yf.download("^GSPC", start=start_date, progress=False)
    if isinstance(sp500.columns, pd.MultiIndex):
        sp500.columns = sp500.columns.get_level_values(0)
    sp500 = sp500[['Close']].rename(columns={'Close': 'sp500_close'})
    
    # 抓取VIX
    vix = yf.download("^VIX", start=start_date, progress=False)
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
    vix = vix[['Close']].rename(columns={'Close': 'vix_close'})
    
    # 合并
    macro_df = pd.merge(sp500, vix, left_index=True, right_index=True, how='left')
    
    # 处理缺失值（如果有节假日不一致）
    macro_df.ffill(inplace=True)
    
    print(">> 计算趋势指标与状态机标签...")
    # 计算 MA200
    macro_df['sp500_ma200'] = macro_df['sp500_close'].rolling(window=200).mean()
    
    # 构建状态机 Regime Tags
    # 默认 Neutral
    macro_df['regime_label'] = 'Neutral'
    
    # 先打上 Bear 基础标签
    bear_mask = macro_df['sp500_close'] < macro_df['sp500_ma200']
    macro_df.loc[bear_mask, 'regime_label'] = 'Bear'
    
    # 叠加 Bull 标签
    bull_mask = (macro_df['sp500_close'] > macro_df['sp500_ma200']) & (macro_df['vix_close'] < 20)
    macro_df.loc[bull_mask, 'regime_label'] = 'Bull'
    
    # 最优先级：Volatile (恐慌震荡)，覆盖所有底层趋势
    volatile_mask = macro_df['vix_close'] > 25
    macro_df.loc[volatile_mask, 'regime_label'] = 'Volatile'
    
    # 删除 MA200 构建期（前 200 天）的无效数据
    macro_df.dropna(subset=['sp500_ma200'], inplace=True)
    macro_df.reset_index(inplace=True)
    macro_df.rename(columns={'Date': 'date'}, inplace=True)
    
    # 保存结果
    macro_df.to_parquet(OUTPUT_PATH)
    
    # 打印简报
    print(f"\n[DONE] 宏观状态机数据已生成: {OUTPUT_PATH}")
    print("\n--- 历史 Regime 分布统计 ---")
    dist = macro_df['regime_label'].value_counts(normalize=True) * 100
    for label, pct in dist.items():
        print(f"{label:10}: {pct:>5.1f}%")
        
    print(f"\n时间范围: {macro_df['date'].min().date()} -> {macro_df['date'].max().date()}")

if __name__ == "__main__":
    fetch_and_build_regimes()
