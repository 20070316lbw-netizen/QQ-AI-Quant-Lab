import os
import pandas as pd
from tqdm import tqdm

DATA_ROOT = r'C:\Data\Market'
PRICE_DIR = os.path.join(DATA_ROOT, 'cn', 'prices')

def audit_data():
    files = [f for f in os.listdir(PRICE_DIR) if f.endswith('.parquet')]
    if not files:
        print("No parquet files found in", PRICE_DIR)
        return

    results = {
        '2014': 0,
        '2015': 0,
        '2016': 0
    }
    
    # Sample up to 800 files (the full count for HS300+ZZ500)
    sample_size = min(len(files), 800)
    print(f"Auditing {sample_size} files in {PRICE_DIR}...")
    
    import random
    sampled_files = random.sample(files, sample_size)
    
    for f in tqdm(sampled_files):
        try:
            df = pd.read_parquet(os.path.join(PRICE_DIR, f))
            if df.empty:
                continue
            
            years_in_file = df.index.year.unique()
            for year in results.keys():
                if int(year) in years_in_file:
                    results[year] += 1
        except Exception as e:
            pass

    print("\n" + "="*40)
    print("  Fresh Data Coverage Audit")
    print("="*40)
    for year, count in results.items():
        print(f"  Year {year}: {count}/{sample_size} ({count/sample_size:.1%})")
    print("="*40)

if __name__ == "__main__":
    audit_data()
