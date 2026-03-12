import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime
from threading import Lock

# 添加在上一级的模块搜索路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import DATA_ROOT

# EDGAR User-Agent 要求: 'CompanyName ContactEmail'
USER_AGENT = "AlphaRankerResearch data@alpharanker.local"
HEADERS = {'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip, deflate'}

# 限制速率：SEC 要求不超过 10 次请求/秒 (安全起见设置为 0.15s)
SEC_DELAY = 0.15

# 保存路径
EDGAR_DIR = os.path.join(DATA_ROOT, 'us', 'fundamentals', 'edgar')
S_P_500_FILE = os.path.join(DATA_ROOT, 'us', 'prices', 'sp500_tickers.json')
os.makedirs(EDGAR_DIR, exist_ok=True)

# 核心财务科目映射 (优先前面的标签)
GAAP_MAPPING = {
    'Net Income': ['NetIncomeLoss'],
    'Total Revenue': ['Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'RevenuesNetOfYear'],
    'Total Assets': ['Assets'],
    'Total Liabilities': ['Liabilities'],
    'Stockholders Equity': ['StockholdersEquity', 'PartnersCapital'],
    'Operating Cash Flow': ['NetCashProvidedByUsedInOperatingActivities'],
    'Diluted EPS': ['EarningsPerShareDiluted']
}

def get_cik_mapping():
    """从 SEC 获取最新的 Ticker -> CIK 映射表"""
    url = "https://www.sec.gov/files/company_tickers.json"
    print("获取 SEC Ticker->CIK 映射表...")
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        
        # Parse { "0": { "cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc." }, ... }
        mapping = {}
        for entry in data.values():
            mapping[entry['ticker']] = str(entry['cik_str']).zfill(10)
        print(f"成功获取 {len(mapping)} 个股票代码映射。")
        return mapping
    except Exception as e:
        print(f"获取 CIK 映射失败: {e}")
        return {}


def parse_company_facts(ticker, cik_str, facts_data):
    """解析 SEC 返回的 CompanyFacts JSON，提取我们需要的 7 大科目季度序列"""
    if 'facts' not in facts_data or 'us-gaap' not in facts_data['facts']:
        return None
        
    gaap_data = facts_data['facts']['us-gaap']
    
    # 建立一个以 (end_date, form) 为 primary_key 的长表
    # { "2024-03-31": {"Net Income": 1000, "form": "10-Q"} }
    quarterly_data = {}
    
    for concept_name, concept_aliases in GAAP_MAPPING.items():
        # 寻找匹配的标签
        matched_concept = None
        for alias in concept_aliases:
            if alias in gaap_data:
                matched_concept = gaap_data[alias]
                break
                
        if not matched_concept or 'units' not in matched_concept:
            continue
            
        # 大多是 USD 或 shares / USD/shares
        units = list(matched_concept['units'].keys())[0]
        points = matched_concept['units'][units]
        
        for point in points:
            # 只取 10-Q 或 10-K，排除修订产生的乱入
            form = point.get('form', '')
            if form not in ('10-Q', '10-K'):
                continue
                
            val = point.get('val')
            period_end = point.get('end')
            frame = point.get('frame', '') # e.g. CY2020Q1 or CY2020
            
            # 对于有 period 范围的数据（如利润表和现金流表, 指标有 startDate），只选符合完整单季/单年的，避免 YTD(年初至今) 与单季混淆
            # 通常利用 "frame" 作为标准化参照物。如果没有 frame 也可以使用 end_date。
            if not period_end:
                continue
                
            # 我们按照结束日期汇总
            if period_end not in quarterly_data:
                quarterly_data[period_end] = {'report_date': period_end, 'form': form}
            
            # 如果存在重述 (revision)，SEC的数据靠后的一般是最新版本，同日期覆盖即可。
            quarterly_data[period_end][concept_name] = val
            
    # 转 DataFrame
    if not quarterly_data:
        return None
        
    df = pd.DataFrame(quarterly_data.values())
    # 转换日期并按日期排序
    df['report_date'] = pd.to_datetime(df['report_date'])
    df = df.sort_values('report_date').drop_duplicates(subset=['report_date'], keep='last')
    
    # 将缺失科目补成 NaN
    for col in GAAP_MAPPING.keys():
        if col not in df.columns:
            df[col] = float('nan')
            
    # 设置索引
    df = df.set_index('report_date')
    return df


def fetch_and_save_edgar_data(ticker, cik_str):
    """请求接口并保存"""
    out_file = os.path.join(EDGAR_DIR, f"{ticker}_edgar.parquet")
    
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_str}.json"
    
    try:
        time.sleep(SEC_DELAY) # 限速
        r = requests.get(url, headers=HEADERS, timeout=15)
        
        if r.status_code == 404:
            print(f"[{ticker}] XBRL 数据不存在。")
            return False
            
        r.raise_for_status()
        data = r.json()
        
        df = parse_company_facts(ticker, cik_str, data)
        if df is not None and len(df) > 0:
            df['ticker'] = ticker
            df.to_parquet(out_file)
            print(f"[{ticker}] √ 成功提取 {len(df)} 份财务截面。 (最近一期: {df.index[-1].strftime('%Y-%m-%d')})")
            return True
        else:
            print(f"[{ticker}] 未能映射出我们所需的 GAAP 数据。")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[{ticker}] 网络/请求由于错误失败: {e}")
        return False
    except json.JSONDecodeError:
        print(f"[{ticker}] SEC 返回非 JSON 响应")
        return False
    except Exception as e:
        print(f"[{ticker}] 处理异常: {e}")
        return False


def main():
    print("==================================================")
    print("  AlphaRanker: SEC EDGAR 长期历史基本面抓取引擎")
    print("  接口: data.sec.gov/api/xbrl/companyfacts/CIK*.json")
    print("==================================================")
    
    cik_map = get_cik_mapping()
    if not cik_map:
        return
        
    # 获取标的池: 扫描 us_prices 目录的所有已存在价格数据的标的
    us_price_dir = os.path.join(DATA_ROOT, 'us', 'prices')
    if os.path.exists(us_price_dir):
        import glob
        files = glob.glob(os.path.join(us_price_dir, "*.parquet"))
        target_tickers = [os.path.basename(f).replace(".parquet", "") for f in files if "_" not in os.path.basename(f)]
        target_tickers = sorted(target_tickers)
    else:
        # Fallback to some prominent tech stocks if list varies
        target_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]
        
    if not target_tickers:
        print("未找到任何目标股票，请确认 us/prices 中是否有日线数据。")
        return
        
    print(f"目标下载清单: {len(target_tickers)} 只股票")
    
    success_count = 0
    fail_count = 0
    
    # 逐个抓取（不建议过度并行因为会直接触发 403 限频）
    for i, ticker in enumerate(target_tickers):
        print(f"[{i+1}/{len(target_tickers)}] 处理 {ticker} ...", end=" ")
        
        # Skip if already fetched today (or at all to save time)
        out_file = os.path.join(EDGAR_DIR, f"{ticker}_edgar.parquet")
        if os.path.exists(out_file):
            print(f"已存在 {ticker}_edgar.parquet，跳过。")
            success_count += 1
            continue
            
        if ticker not in cik_map:
            print(f"CIK 映射表中找不到 {ticker}。")
            fail_count += 1
            continue
            
        cik_str = cik_map[ticker]
        if fetch_and_save_edgar_data(ticker, cik_str):
            success_count += 1
        else:
            fail_count += 1
            # 如果可能是限频，多睡一会儿
            time.sleep(1)

    print("\n================== 抓取任务完成 ==================")
    print(f"成功: {success_count} | 失败/跳过: {fail_count} | 数据保存至: {EDGAR_DIR}")


if __name__ == "__main__":
    main()
