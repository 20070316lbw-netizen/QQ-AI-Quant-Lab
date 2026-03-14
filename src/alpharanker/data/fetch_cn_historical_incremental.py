import os
import baostock as bs
import pandas as pd
from tqdm import tqdm
import sys
import time

# 路径配置
DATA_ROOT = r'C:\Data\Market'
PRICE_DIR = os.path.join(DATA_ROOT, 'cn', 'prices')

def _std_to_bs(symbol: str) -> str:
    if symbol.upper().endswith(".SS"): return f"sh.{symbol[:-3]}"
    if symbol.upper().endswith(".SZ"): return f"sz.{symbol[:-3]}"
    return symbol

def fetch_chunk(ticker_std, start_date, end_date):
    """
    抓取指定时段的数据。
    """
    file_path = os.path.join(PRICE_DIR, f"{ticker_std}.parquet")
    
    rs = bs.query_history_k_data_plus(
        _std_to_bs(ticker_std),
        "date,open,high,low,close,volume,turn,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
        start_date=start_date, end_date=end_date,
        frequency="d", adjustflag="3"
    )
    
    if rs.error_code != '0':
        return rs.error_code

    rows = []
    while rs.next(): rows.append(rs.get_row_data())
    
    if not rows:
        return "EMPTY"
        
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
    return "SUCCESS"

def get_index_tickers():
    bs.login()
    tickers = []
    for query_func in [bs.query_hs300_stocks, bs.query_zz500_stocks]:
        rs = query_func()
        while rs.next():
            r = rs.get_row_data()
            tickers.append(r[1].split(".")[1] + (".SS" if r[1].startswith("sh") else ".SZ"))
    bs.logout()
    return list(set(tickers))

def main():
    focus_tickers = get_index_tickers()
    years = ["2014", "2015", "2016"]
    
    print(f">> 开始补全历史数据 (增量模式): {years}")
    
    for year in years:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        print(f"\n--- 正在抓取年度: {year} ---")
        
        bs.login()
        for i, ticker in enumerate(tqdm(focus_tickers, desc=f"Year {year}")):
            try:
                res = fetch_chunk(ticker, start_date, end_date)
                if res in ['-1', '10038']:
                    print(f"\n[!] 连接断开 ({res})，尝试重连...")
                    bs.logout()
                    time.sleep(1)
                    bs.login()
                    fetch_chunk(ticker, start_date, end_date)
            except Exception as e:
                print(f"Error for {ticker}: {e}")
            
            if (i+1) % 100 == 0:
                print(f"[{year}] Progress: {i+1}/{len(focus_tickers)}")
        bs.logout()

if __name__ == "__main__":
    main()
