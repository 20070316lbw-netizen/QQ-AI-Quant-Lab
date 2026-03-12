"""
fetch_industry.py (v2 - Baostock Version)
=========================================
抓取全 A 股的行业分类（申万一级行业）。
由于 Akshare 在当前环境存在代理连通问题，改用 Baostock 接口。

输出：
  data/stock_industry_map.parquet
    columns: ticker, industry_name
"""

import os
import baostock as bs
import pandas as pd
from tqdm import tqdm

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import IND_MAP_PATH as SAVE_PATH

def _bs_to_std(bs_code: str) -> str:
    parts = bs_code.split(".")
    return f"{parts[1]}.{'SS' if parts[0] == 'sh' else 'SZ'}"

def fetch_industry_mapping():
    print("正在通过 Baostock 抓取全 A 股行业分类...")
    bs.login()
    try:
        # query_stock_industry 不传参数默认获取最新的全部股票行业分类
        rs = bs.query_stock_industry()
        rows = []
        while rs.next():
            rows.append(rs.get_row_data())
    finally:
        bs.logout()

    if not rows:
        print("❌ 未获取到行业数据。")
        return None

    # Baostock 返回列: updateDate, code, code_name, industry, industryClassification, ...
    # 我们主要取 code 和 industry (第四列)
    df = pd.DataFrame(rows)
    df = df[[1, 3]].rename(columns={1: "bs_code", 3: "industry_name"})
    
    # 转换代码格式
    df["ticker"] = df["bs_code"].apply(_bs_to_std)
    
    # 清洗：去掉行业为空的
    df = df[df["industry_name"] != ""]
    
    return df[["ticker", "industry_name"]]

def main():
    df = fetch_industry_mapping()
    if df is not None:
        print(f"\n行业映射构建完成！总计 {len(df)} 只股票。")
        df.to_parquet(SAVE_PATH, compression="snappy")
        print(f"数据已保存至: {SAVE_PATH}")
    else:
        print("❌ 行业抓取失败。")

if __name__ == "__main__":
    main()
