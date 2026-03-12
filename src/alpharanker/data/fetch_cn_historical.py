"""
fetch_cn_historical.py
======================
全量抓取 A 股 HS300 与 CSI500 成分股自 2014 年起的历史行情。
用于 2015 极值周期的回溯验证。
"""

import os
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

def fetch_historical_data(ticker_std, start_date, end_date):
    """
    抓取单只股票数据，假设外部已登录。
    """
    file_path = os.path.join(PRICE_DIR, f"{ticker_std}.parquet")
    
    try:
        rs = bs.query_history_k_data_plus(
            _std_to_bs(ticker_std),
            "date,open,high,low,close,volume,turn,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
            start_date=start_date, end_date=end_date,
            frequency="d", adjustflag="2"
        )
        
        if rs.error_code != '0':
            # 如果是连接断了，尝试在外面重连
            return "RECONNECT" if rs.error_code in ['-1', '10038'] else False

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
        
        if os.path.exists(file_path):
            existing_df = pd.read_parquet(file_path)
            combined_df = pd.concat([existing_df, new_df])
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')].sort_index()
        else:
            combined_df = new_df.sort_index()
        
        combined_df.to_parquet(file_path, compression="snappy")
        return True
    except Exception as e:
        if "10038" in str(e): return "RECONNECT"
        print(f"Error fetching {ticker_std}: {e}")
        return False

def get_index_tickers():
    bs.login()
    tickers = []
    # 获取成份股（当前成份股，对于历史追溯可能有生存偏误，但作为 Alpha Genome 验证足够）
    for query_func in [bs.query_hs300_stocks, bs.query_zz500_stocks]:
        rs = query_func()
        while rs.next():
            r = rs.get_row_data()
            tickers.append(r[1].split(".")[1] + (".SS" if r[1].startswith("sh") else ".SZ"))
    bs.logout()
    return list(set(tickers))

def main():
    bs.login()
    focus_tickers = get_index_tickers()
    start_date = "2014-01-01"
    end_date = "2021-01-01"
    
    print(f">> 开始补全历史数据 (稳健模式): {start_date} -> {end_date}")
    
    success_count = 0
    for i, ticker in enumerate(tqdm(focus_tickers, desc="Fetching Historical")):
        res = fetch_historical_data(ticker, start_date, end_date)
        
        if res == "RECONNECT":
            print(f"\n[!] 检测到连接断开，尝试重连 ({ticker})...")
            bs.logout()
            bs.login()
            # 重试一次
            if fetch_historical_data(ticker, start_date, end_date) == True:
                success_count += 1
        elif res == True:
            success_count += 1
        
        if (i + 1) % 100 == 0:
            print(f"Progress: {i+1}/{len(focus_tickers)} - Success: {success_count}")
            
    bs.logout()
    print(f"\n[DONE] 补全共 {success_count} 只股票的历史数据。")

if __name__ == "__main__":
    main()
