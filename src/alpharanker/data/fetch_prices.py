"""
fetch_prices.py
================
从 Baostock 批量下载沪深 300 成分股日线数据及关键估值指标。

输出：
  data/prices/{ticker}.parquet
    columns: date, open, high, low, close, volume, turn, pe, pb, ps, pcf, is_st
"""

import os
import argparse
import threading
from datetime import date

import baostock as bs
import pandas as pd
from tqdm import tqdm

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import PRICE_DIR as DATA_DIR

def _bs_to_std(bs_code: str) -> str:
    parts = bs_code.split(".")
    return f"{parts[1]}.{'SS' if parts[0] == 'sh' else 'SZ'}"

def _std_to_bs(symbol: str) -> str:
    if symbol.upper().endswith(".SS"): return f"sh.{symbol[:-3]}"
    if symbol.upper().endswith(".SZ"): return f"sz.{symbol[:-3]}"
    return symbol

def get_hs300_tickers():
    rs = bs.query_hs300_stocks()
    rows = []
    while rs.next():
        r = rs.get_row_data()
        rows.append((_bs_to_std(r[1]), r[2]))
    return rows

def get_all_a_tickers(start_date: str):
    """获取所有 A 股主板、创业板代码，过滤掉在 start_date 之前已退市的"""
    rs = bs.query_stock_basic()
    rows = []
    while rs.next():
        r = rs.get_row_data()
        # fields: code,code_name,ipoDate,outDate,type,status
        # r[3]: outDate, r[4]: type, r[5]: status
        is_stock = (r[4] == "1")
        is_active = (r[5] == "1")
        out_date = r[3]
        
        if is_stock:
            # 如果是上市中，或者退市日期晚于数据起始日，则保留
            if is_active or (out_date and out_date > start_date):
                rows.append((_bs_to_std(r[0]), r[1]))
    return rows

def main(start_date: str, end_date: str, all_a: bool = False):
    print(f"AlphaRanker — 价格+估值指标同步抓取 (High Reliability)")
    
    bs.login()
    try:
        if all_a:
            print(f"正在获取全 A 股列表 (过滤 {start_date} 前退市股票)...")
            tickers = get_all_a_tickers(start_date)
        else:
            tickers = get_hs300_tickers()
            
        print(f"目标：{len(tickers)} 只股票\n")

        errors = []
        for ticker, name in tqdm(tickers, desc="下载中"):
            out_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
            
            # 只有当文件不存在或非法小时才重新下载
            if os.path.exists(out_path) and os.path.getsize(out_path) > 2048:
                continue

            rs = bs.query_history_k_data_plus(
                _std_to_bs(ticker),
                "date,open,high,low,close,volume,turn,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="2"
            )
            
            rows = []
            while rs.next(): rows.append(rs.get_row_data())

            if not rows:
                tqdm.write(f"  [ERR] {ticker} {name} - 无数据")
                errors.append(ticker)
                continue

            df = pd.DataFrame(rows, columns=["date","open","high","low","close","volume","turn","pe","pb","ps","pcf","is_st"])
            df["date"] = pd.to_datetime(df["date"])
            df["ticker"] = ticker
            for c in ["open","high","low","close","volume","turn","pe","pb","ps","pcf"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            
            df.set_index("date", inplace=True)
            df.to_parquet(out_path, compression="snappy")
            
    finally:
        bs.logout()
    print(f"\n价格抓取完成！失败: {len(errors)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--end", default=str(date.today()))
    parser.add_argument("--all-a", action="store_true", help="抓取全 A 股而非仅沪深 300")
    args = parser.parse_args()
    main(args.start, args.end, all_a=args.all_a)
