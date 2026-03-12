"""
fetch_us_fundamentals.py
=========================
使用 yfinance 抓取 S&P 500 成分股的季度财报明细。

抓取内容：
  1. 季度利润表 (quarterly_financials): Revenue, Net Income, EBITDA, EPS 等
  2. 季度资产负债表 (quarterly_balance_sheet): Total Assets, Debt, Equity 等
  3. 季度现金流量表 (quarterly_cashflow): Operating CF, CapEx, Free CF 等
  4. 公司基本信息 (info): sector, industry, marketCap 等

输出：
  data/us_fundamentals/{TICKER}_income.parquet     — 季度利润表
  data/us_fundamentals/{TICKER}_balance.parquet    — 季度资产负债表
  data/us_fundamentals/{TICKER}_cashflow.parquet   — 季度现金流量表
  data/us_fundamentals/us_stock_info.parquet       — 全部公司基本信息汇总
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import US_FUND_DIR

import pandas as pd
import yfinance as yf
from tqdm import tqdm
import time


def get_sp500_tickers() -> list:
    """从 Wikipedia 爬取 S&P 500 成分股列表，失败时从本地已有文件推断"""
    import requests
    from io import StringIO
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            tables = pd.read_html(StringIO(r.text))
            df = tables[0]
            tickers = df["Symbol"].tolist()
            tickers = [t.replace(".", "-") for t in tickers]
            print(f"  从 Wikipedia 获取 {len(tickers)} 只成分股")
            return tickers
        except Exception as e:
            print(f"  [WARN] Wikipedia 请求失败（{attempt+1}/3）: {e}")
    # Fallback: 从本地财报文件名推断已有 tickers，并补全标准列表
    print("  [FALLBACK] 使用本地文件推断 ticker 列表...")
    existing = glob.glob(os.path.join(US_FUND_DIR, "*_income.parquet"))
    done_tickers = set(os.path.basename(f).replace("_income.parquet", "") for f in existing)
    # 硬编码 S&P 500 大部分常见成分（保底列表）
    fallback = list(done_tickers)  # 至少把已有的重跑一遍检查
    print(f"  本地已有 {len(fallback)} 只，将只处理这些")
    return fallback


def fetch_single_stock(ticker: str) -> dict:
    """抓取单只股票的季度财报三大表 + 基本信息"""
    result = {"info": None, "income": None, "balance": None, "cashflow": None}

    try:
        t = yf.Ticker(ticker)

        # 1. 季度利润表
        inc = t.quarterly_income_stmt
        if inc is not None and not inc.empty:
            result["income"] = inc.T  # 转置：行=季度，列=科目
            result["income"]["ticker"] = ticker

        # 2. 季度资产负债表
        bal = t.quarterly_balance_sheet
        if bal is not None and not bal.empty:
            result["balance"] = bal.T
            result["balance"]["ticker"] = ticker

        # 3. 季度现金流量表
        cf = t.quarterly_cashflow
        if cf is not None and not cf.empty:
            result["cashflow"] = cf.T
            result["cashflow"]["ticker"] = ticker

        # 4. 公司基本信息
        info = t.info
        if info:
            result["info"] = {
                "ticker": ticker,
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "marketCap": info.get("marketCap", 0),
                "trailingPE": info.get("trailingPE", 0),
                "forwardPE": info.get("forwardPE", 0),
                "priceToBook": info.get("priceToBook", 0),
                "dividendYield": info.get("dividendYield", 0),
                "beta": info.get("beta", 0),
                "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh", 0),
                "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow", 0),
                "shortName": info.get("shortName", ""),
            }

    except Exception as e:
        tqdm.write(f"  [ERR] {ticker}: {e}")

    return result


def main():
    print("AlphaRanker — S&P 500 美股季度财报抓取 (yfinance)")

    tickers = get_sp500_tickers()
    print(f"目标：{len(tickers)} 只 S&P 500 成分股\n")

    all_info = []
    errors = []
    skipped = 0

    for ticker in tqdm(tickers, desc="抓取美股财报"):
        # 断点续传：如果三张表都已存在则跳过
        inc_path = os.path.join(US_FUND_DIR, f"{ticker}_income.parquet")
        bal_path = os.path.join(US_FUND_DIR, f"{ticker}_balance.parquet")
        cf_path  = os.path.join(US_FUND_DIR, f"{ticker}_cashflow.parquet")

        if all(os.path.exists(p) for p in [inc_path, bal_path, cf_path]):
            skipped += 1
            continue

        data = fetch_single_stock(ticker)

        if data["income"] is not None:
            data["income"].to_parquet(inc_path, compression="snappy")
        if data["balance"] is not None:
            data["balance"].to_parquet(bal_path, compression="snappy")
        if data["cashflow"] is not None:
            data["cashflow"].to_parquet(cf_path, compression="snappy")
        if data["info"] is not None:
            all_info.append(data["info"])

        if data["income"] is None and data["balance"] is None:
            errors.append(ticker)

        time.sleep(0.5)  # 避免触发频率限制

    # 保存汇总公司信息
    if all_info:
        df_info = pd.DataFrame(all_info)
        info_path = os.path.join(US_FUND_DIR, "us_stock_info.parquet")
        # 如果已有旧的，合并去重
        if os.path.exists(info_path):
            old_info = pd.read_parquet(info_path)
            df_info = pd.concat([old_info, df_info]).drop_duplicates(subset="ticker", keep="last")
        df_info.to_parquet(info_path, compression="snappy", index=False)

    print(f"\n美股财报抓取完成！")
    print(f"  跳过(已存在): {skipped}")
    print(f"  新下载: {len(tickers) - skipped - len(errors)}")
    print(f"  失败: {len(errors)}")
    if errors:
        print(f"  失败列表: {errors}")


if __name__ == "__main__":
    main()
