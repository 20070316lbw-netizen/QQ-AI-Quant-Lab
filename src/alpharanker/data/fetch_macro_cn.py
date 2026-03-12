"""
fetch_macro_cn.py
=================
提取沪深 300 宽基指数数据，并且建立无未来函数（Look-ahead bias free）的宏观状态机标签。

核心逻辑：
1. 提取 sh.000300 每日收盘价。
2. 计算过去 250 个交易日的收盘均价 (MA250)。
3. 严格使用 `shift(1)` 将 T 日指标向后平移，使模型在预测 T 日收益时，只能看见 T-1 日的宏观状态。
"""

import os
import sys
import pandas as pd
import numpy as np
import baostock as bs

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

OUTPUT_PATH = os.path.join(DATA_ROOT, 'cn', 'macro_regime.parquet')

def fetch_and_build_cn_regimes(start_date="2014-01-01"):
    print(f">> 开始抓取 A 股宏观市场数据 (从 {start_date} 至今)...")
    bs.login()
    
    # 抓取沪深300指数
    rs = bs.query_history_k_data_plus("sh.000300",
                                      "date,close",
                                      start_date=start_date, frequency="d", adjustflag="3")
    
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    
    bs.logout()
    
    df = pd.DataFrame(data_list, columns=rs.fields)
    df["close"] = pd.to_numeric(df["close"])
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    
    print(">> 计算趋势指标与无未来函数的状态标签...")
    
    # 计算均线
    df['hs300_ma250'] = df['close'].rolling(window=250).mean()
    
    # 【核心：防止未来函数】
    # 将 close 和 ma250 下移一天。这样在 T 日提取到的 hs300_close_prev 实际上是 T-1 日的收盘数据。
    df['hs300_close_prev'] = df['close'].shift(1)
    df['hs300_ma250_prev'] = df['hs300_ma250'].shift(1)
    
    # 定义状态标签 (0: Bear, 1: Bull)
    # 考虑到之前定义的 regime：1 (Bull) / 0 (Bear/Volatile)
    df['regime'] = 0 # 默认熊市/震荡避险
    
    bull_mask = df['hs300_close_prev'] > df['hs300_ma250_prev']
    df.loc[bull_mask, 'regime'] = 1
    
    # 清理前 250 天的无效数据
    df.dropna(subset=['hs300_ma250_prev'], inplace=True)
    df.reset_index(inplace=True)
    
    # 只保留必需的字段
    res_df = df[['date', 'hs300_close_prev', 'hs300_ma250_prev', 'regime']].copy()
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    res_df.to_parquet(OUTPUT_PATH)
    
    print(f"\n[DONE] A 股宏观状态机数据已生成: {OUTPUT_PATH}")
    print("\n--- 历史 Regime 分布统计 ---")
    dist = res_df['regime'].value_counts(normalize=True) * 100
    for label, pct in dist.items():
        label_str = "Bull (1)" if label == 1 else "Bear (0)"
        print(f"{label_str:10}: {pct:>5.1f}%")
        
    print(f"\n时间范围: {res_df['date'].min().date()} -> {res_df['date'].max().date()}")

if __name__ == "__main__":
    fetch_and_build_cn_regimes()
