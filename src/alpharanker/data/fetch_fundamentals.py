"""
fetch_fundamentals.py
======================
从 Baostock 抓取沪深 300 成分股的季度财务报表数据（ROE, 净利润增长）。

输出：
  data/fundamentals/{ticker}_fundamental.parquet
    columns: pubDate, statDate, roe, np_growth (YOYNI)
"""

import os
import argparse
from datetime import date

import baostock as bs
import pandas as pd
from tqdm import tqdm

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import FUND_DIR as DATA_DIR

def _std_to_bs(symbol: str) -> str:
    if symbol.upper().endswith(".SS"): return f"sh.{symbol[:-3]}"
    if symbol.upper().endswith(".SZ"): return f"sz.{symbol[:-3]}"
    return symbol

def get_hs300_tickers():
    rs = bs.query_hs300_stocks()
    rows = []
    while rs.next():
        r = rs.get_row_data()
        rows.append((r[1], r[2])) # sh.600519, 贵州茅台
    return rows


def get_all_a_tickers(start_year: int):
    """获取所有 A 股列表，过滤掉在起始年份前已退市的"""
    rs = bs.query_stock_basic()
    rows = []
    start_date = f"{start_year}-01-01"
    while rs.next():
        r = rs.get_row_data()
        # fields: code,code_name,ipoDate,outDate,type,status
        # r[3]: outDate, r[4]: type, r[5]: status
        is_stock = (r[4] == "1")
        is_active = (r[5] == "1")
        out_date = r[3]
        if is_stock:
            if is_active or (out_date and out_date > start_date):
                rows.append((r[0], r[1]))
    return rows

def fetch_stock_fundamentals(bs_code: str, start_year: int, end_year: int):
    """抓取单只股票从 start_year 到 end_year 的所有季度财报"""
    all_data = []
    for y in range(start_year, end_year + 1):
        for q in [1, 2, 3, 4]:
            if y == date.today().year and q > (date.today().month-1)//3: break
            
            # 1. 盈利能力 (ROE)
            rs_p = bs.query_profit_data(code=bs_code, year=y, quarter=q)
            # 2. 成长能力 (NetProfit Growth)
            rs_g = bs.query_growth_data(code=bs_code, year=y, quarter=q)
            
            p_data = rs_p.get_row_data()
            g_data = rs_g.get_row_data()
            
            if p_data and g_data:
                all_data.append({
                    "pubDate":  p_data[1],
                    "statDate": p_data[2],
                    "roe":      float(p_data[3]) if p_data[3] else 0.0,
                    "np_growth":float(g_data[5]) if g_data[5] else 0.0  # YOYNI
                })
    return pd.DataFrame(all_data)

def main(start_year: int, all_a: bool = False):
    print(f"AlphaRanker — 季度基本面抓取 (Baostock Stability Mode)")
    
    bs.login()
    if all_a:
        print(f"正在获取全 A 股列表 (过滤 {start_year} 前退市股票)...")
        tickers = get_all_a_tickers(start_year)
    else:
        tickers = get_hs300_tickers()
        
    print(f"目标：{len(tickers)} 只股票\n")

    current_year = date.today().year
    errors = []

    for bs_code, name in tqdm(tickers, desc="抓取财报"):
        ticker_std = bs_code.split(".")[1] + (".SS" if bs_code.startswith("sh") else ".SZ")
        out_path = os.path.join(DATA_DIR, f"{ticker_std}_fundamental.parquet")
        
        if os.path.exists(out_path): continue

        df = fetch_stock_fundamentals(bs_code, start_year, current_year)
        if df.empty:
            errors.append(ticker_std)
            continue
            
        df.to_parquet(out_path, compression="snappy")
    
    bs.logout()
    print(f"\n财报抓取完成！失败: {len(errors)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_year", type=int, default=2021)
    parser.add_argument("--all-a", action="store_true", help="抓取全 A 股而非仅沪深 300")
    args = parser.parse_args()
    main(args.start_year, all_a=args.all_a)
