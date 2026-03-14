import os
import pandas as pd
import baostock as bs
from tqdm import tqdm

DATA_ROOT = r'C:\Data\Market'
PRICE_DIR = os.path.join(DATA_ROOT, 'cn', 'prices')

def get_target_tickers():
    bs.login()
    tickers = []
    # Fetch HS300 and ZZ500 components
    for query_func in [bs.query_hs300_stocks, bs.query_zz500_stocks]:
        rs = query_func()
        while rs.next():
            r = rs.get_row_data()
            # Convert sz.000001 to 000001.SZ
            code = r[1]
            standard_code = code.split(".")[1] + (".SS" if code.startswith("sh") else ".SZ")
            tickers.append(standard_code)
    bs.logout()
    return list(set(tickers))

def audit_target_coverage():
    targets = get_target_tickers()
    print(f"Total Unique Target Stocks: {len(targets)}")
    
    results = {
        '2014': 0,
        '2015': 0,
        '2016': 0
    }
    
    missing_any = []
    
    for ticker in tqdm(targets):
        file_path = os.path.join(PRICE_DIR, f"{ticker}.parquet")
        if not os.path.exists(file_path):
            missing_any.append(ticker)
            continue
            
        try:
            df = pd.read_parquet(file_path)
            if df.empty:
                missing_any.append(ticker)
                continue
            
            years_in_file = df.index.year.unique()
            for year in results.keys():
                if int(year) in years_in_file:
                    results[year] += 1
        except Exception:
            missing_any.append(ticker)

    print("\n" + "="*40)
    print("  Target Stocks Data Coverage Audit")
    print(f"  (HS300 + ZZ500, n={len(targets)})")
    print("="*40)
    for year, count in results.items():
        print(f"  Year {year}: {count}/{len(targets)} ({count/len(targets):.1%})")
    print("="*40)
    print(f"  Completely Missing Target Files: {len(missing_any)}")
    if missing_any:
        print(f"  Sample Missing: {missing_any[:10]}")

if __name__ == "__main__":
    audit_target_coverage()
