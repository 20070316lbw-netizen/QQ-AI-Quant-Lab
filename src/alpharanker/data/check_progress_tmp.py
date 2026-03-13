import pandas as pd
import os
import baostock as bs
from tqdm import tqdm

PRICE_DIR = r'C:\Data\Market\cn\prices'

def get_status():
    bs.login()
    tickers = []
    for query_func in [bs.query_hs300_stocks, bs.query_zz500_stocks]:
        rs = query_func()
        while rs.next():
            r = rs.get_row_data()
            tickers.append(r[1].split(".")[1] + (".SS" if r[1].startswith("sh") else ".SZ"))
    bs.logout()
    
    tickers = list(set(tickers))
    total = len(tickers)
    ready_2014 = 0
    missing_files = 0
    
    for t in tqdm(tickers, desc="Auditing"):
        path = os.path.join(PRICE_DIR, f"{t}.parquet")
        if os.path.exists(path):
            try:
                df = pd.read_parquet(path)
                if not df.empty:
                    # Check if min date is at or before Jan 2014
                    if df.index.min() <= pd.Timestamp('2014-01-05'):
                        ready_2014 += 1
            except:
                pass
        else:
            missing_files += 1
            
    print(f"\nAudit Results:")
    print(f"Total Index Tickers (HS300+ZZ500): {total}")
    print(f"Missing Files: {missing_files}")
    print(f"Ready with 2014 Data: {ready_2014}")
    print(f"Completion Percentage (2014): {(ready_2014/total)*100:.1f}%")

if __name__ == "__main__":
    get_status()
