"""
fetch_us_prices.py
===================
使用 yfinance 批量下载 S&P 500 成分股的日线历史数据。

输出：
  data/us_prices/{TICKER}.parquet
    columns: Date, Open, High, Low, Close, Adj Close, Volume
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import US_PRICE_DIR

import argparse
import pandas as pd
import yfinance as yf
from tqdm import tqdm
import time
import glob


def get_sp500_tickers() -> list:
    """从 Wikipedia 爬取 S&P 500 成分股列表，失败时使用本地已有文件"""
    import requests
    from io import StringIO
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            tables = pd.read_html(StringIO(r.text))
            tickers = [t.replace(".", "-") for t in tables[0]["Symbol"].tolist()]
            print(f"  从 Wikipedia 获取 {len(tickers)} 只成分股")
            return tickers
        except Exception as e:
            print(f"  [WARN] Wikipedia 请求失败({attempt+1}/3): {e}")
            time.sleep(2)
    # Fallback：从本地文件推断
    existing = glob.glob(os.path.join(US_PRICE_DIR, "*.parquet"))
    tickers = [os.path.basename(f).replace(".parquet", "") for f in existing if "_" not in os.path.basename(f)]
    print(f"  [FALLBACK] 使用本地已有 {len(tickers)} 只")
    return tickers if tickers else []


def main(start_date: str, end_date: str):
    print("AlphaRanker — S&P 500 美股日线数据抓取 (yfinance)")
    print(f"时间范围：{start_date} ~ {end_date}")

    tickers = get_sp500_tickers()
    print(f"目标：{len(tickers)} 只 S&P 500 成分股\n")

    errors = []
    skipped = 0
    merged = 0

    for ticker in tqdm(tickers, desc="下载美股日线"):
        out_path = os.path.join(US_PRICE_DIR, f"{ticker}.parquet")

        # 检查现有数据的时间范围
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
            try:
                existing_df = pd.read_parquet(out_path)
                existing_df.index = pd.to_datetime(existing_df.index)
                existing_start = existing_df.index.min()
                target_start = pd.Timestamp(start_date)

                # 如果现有数据已经覆盖目标起始日期，则跳过
                if existing_start <= target_start + pd.Timedelta(days=30):
                    skipped += 1
                    continue

                # 否则只下载缺失的早期数据（start ~ existing_start 前一天）
                fetch_end = (existing_start - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
                tqdm.write(f"  [MERGE] {ticker}: 补充 {start_date} ~ {fetch_end}")

                new_df = yf.download(
                    ticker,
                    start=start_date,
                    end=fetch_end,
                    progress=False,
                    auto_adjust=False
                )

                if new_df.empty:
                    skipped += 1
                    continue

                # 合并新旧数据
                if isinstance(new_df.columns, pd.MultiIndex):
                    new_df.columns = [col[0] for col in new_df.columns]

                new_df["ticker"] = ticker
                combined = pd.concat([new_df, existing_df])
                combined = combined[~combined.index.duplicated(keep="last")]
                combined = combined.sort_index()
                combined.to_parquet(out_path, compression="snappy")
                merged += 1
                time.sleep(0.3)
                continue

            except Exception as e:
                tqdm.write(f"  [WARN] {ticker} 读取现有文件失败，将重新下载: {e}")

        # 全量下载
        try:
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=False
            )

            if df.empty:
                tqdm.write(f"  [WARN] {ticker} - 无数据")
                errors.append(ticker)
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]

            df["ticker"] = ticker
            df.to_parquet(out_path, compression="snappy")
            time.sleep(0.3)  # 避免触发频率限制

        except Exception as e:
            tqdm.write(f"  [ERR] {ticker} - {e}")
            errors.append(ticker)
            time.sleep(1)

    print(f"\n美股价格抓取完成！")
    print(f"  跳过(已覆盖): {skipped}")
    print(f"  补充合并:    {merged}")
    print(f"  新下载:      {len(tickers) - skipped - merged - len(errors)}")
    print(f"  失败:        {len(errors)}")
    if errors:
        print(f"  失败列表: {errors}")


if __name__ == "__main__":
    from datetime import date
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default=str(date.today()))
    args = parser.parse_args()
    main(args.start, args.end)
