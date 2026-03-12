"""
collect_monthly_closes.py
========================
由于原始特征库缺失价格，本脚本从 C:/Data/Market/us/prices/ 下的
数百个 parquet 文件中提取每月末的收盘价，并汇总成一个快照表。
"""

import os
import sys
import pandas as pd
import glob
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

PRICES_DIR = os.path.join(DATA_ROOT, 'us', 'prices')
OUTPUT_PATH = os.path.join(DATA_ROOT, 'us', 'us_monthly_closes.parquet')

def main():
    all_files = glob.glob(os.path.join(PRICES_DIR, "*.parquet"))
    print(f">> 扫描到 {len(all_files)} 个股票价格文件...")
    
    monthly_data = []
    count = 0
    for f in all_files:
        count += 1
        ticker = os.path.basename(f).replace(".parquet", "")
        if count % 50 == 0:
            print(f"   已处理 {count}/{len(all_files)} ...")
            
        try:
            df = pd.read_parquet(f)
            if df.empty: continue
            
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # 提取 Adj Close 的月末值
            try:
                m_df = df['Adj Close'].resample('ME').last().rename('close')
            except:
                m_df = df['Adj Close'].resample('M').last().rename('close')
                
            m_df = m_df.to_frame()
            m_df['ticker'] = ticker
            monthly_data.append(m_df)
        except:
            pass
            
    if not monthly_data:
        print("❌ 未提取到任何数据。")
        return
        
    print(">> 整合并保存快照...")
    full_df = pd.concat(monthly_data)
    full_df.index.name = 'report_date'
    full_df = full_df.reset_index()
    
    full_df.to_parquet(OUTPUT_PATH)
    print(f"\n[DONE] 月度价格快照已保存: {OUTPUT_PATH}")
    print(f"总样本数: {len(full_df)}")

if __name__ == "__main__":
    main()
