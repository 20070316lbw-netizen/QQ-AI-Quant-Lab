"""
fetch_cn_latest.py
===================
增量抓取 A 股最新行情 (2026-02-27 至今)。
"""

import os
from datetime import date, timedelta
import baostock as bs
import pandas as pd
from tqdm import tqdm
import sys

# 路径配置
DATA_ROOT = r'C:\Data\Market'
PRICE_DIR = os.path.join(DATA_ROOT, 'cn', 'prices')

def _std_to_bs(symbol: str) -> str:
    if symbol.upper().endswith(".SS"): return f"sh.{symbol[:-3]}"
    if symbol.upper().endswith(".SZ"): return f"sz.{symbol[:-3]}"
    return symbol

def update_stock_data(ticker_std, end_date):
    file_path = os.path.join(PRICE_DIR, f"{ticker_std}.parquet")
    if not os.path.exists(file_path):
        # 如果文件不存在，跳过（本脚本只做增量）
        return False
        
    try:
        existing_df = pd.read_parquet(file_path)
        last_date = existing_df.index.max()
        start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        if start_date > end_date:
            return False
            
        rs = bs.query_history_k_data_plus(
            _std_to_bs(ticker_std),
            "date,open,high,low,close,volume,turn,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
            start_date=start_date, end_date=end_date,
            frequency="d", adjustflag="2"
        )
        
        rows = []
        while rs.next(): rows.append(rs.get_row_data())
        
        if not rows:
            return False
            
        new_df = pd.DataFrame(rows, columns=["date","open","high","low","close","volume","turn","pe","pb","ps","pcf","is_st"])
        new_df["date"] = pd.to_datetime(new_df["date"])
        new_df["ticker"] = ticker_std
        for c in ["open","high","low","close","volume","turn","pe","pb","ps","pcf"]:
            new_df[c] = pd.to_numeric(new_df[c], errors="coerce")
        
        new_df.set_index("date", inplace=True)
        
        # 合并
        combined_df = pd.concat([existing_df, new_df])
        # 去重
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')].sort_index()
        
        combined_df.to_parquet(file_path, compression="snappy")
        return True
    except Exception as e:
        print(f"Error updating {ticker_std}: {e}")
        return False

def get_index_tickers():
    """获取沪深 300 和 中证 500 股票列表"""
    bs.login()
    # HS300
    rs_hs300 = bs.query_hs300_stocks()
    tickers = []
    while rs_hs300.next():
        r = rs_hs300.get_row_data()
        tickers.append(r[1].split(".")[1] + (".SS" if r[1].startswith("sh") else ".SZ"))
    
    # CSI500
    rs_zz500 = bs.query_zz500_stocks()
    while rs_zz500.next():
        r = rs_zz500.get_row_data()
        tickers.append(r[1].split(".")[1] + (".SS" if r[1].startswith("sh") else ".SZ"))
    
    return list(set(tickers))

def main():
    bs.login()
    today = date.today().strftime("%Y-%m-%d")
    print(f"Fetching focus tickers (HS300 + CSI500)...")
    focus_tickers = get_index_tickers()
    print(f"Target: {len(focus_tickers)} focus stocks.")
    
    updated_count = 0
    for i, ticker in enumerate(tqdm(focus_tickers, desc="Updating Focus Tickers")):
        if update_stock_data(ticker, today):
            updated_count += 1
        
        if (i + 1) % 50 == 0:
            print(f"Progress: {i+1}/{len(focus_tickers)} - Updated: {updated_count}")
            
    bs.logout()
    print(f"Update complete. {updated_count} focus stocks updated.")

if __name__ == "__main__":
    main()
