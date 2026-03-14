import pandas as pd
import numpy as np
import os
from scipy.stats import spearmanr

OUTPUT_PATH = r'C:\Data\Market\cn\kronos_ic_results.parquet'

def summarize():
    if not os.path.exists(OUTPUT_PATH):
        print("Result file not found.")
        return
        
    df = pd.read_parquet(OUTPUT_PATH)
    print(f"Loaded {len(df)} samples.")
    
    ics = []
    for date, group in df.groupby('date'):
        if len(group) > 5:
            ic, _ = spearmanr(group['kronos_return'], group['actual_return'])
            ics.append(ic)
            print(f"  {date.date()}: IC = {ic:.4f} (n={len(group)})")
            
    if not ics:
        print("Insufficient data for monthly IC.")
        return
        
    mean_ic = np.mean(ics)
    std_ic = np.std(ics)
    t_stat = mean_ic / (std_ic / np.sqrt(len(ics)) + 1e-9)
    
    print("\n" + "="*40)
    print("  Final Kronos Factor IC Report")
    print("="*40)
    print(f"Average Rank IC: {mean_ic:.4f}")
    print(f"IC Std:          {std_ic:.4f}")
    print(f"T-Stat:          {t_stat:.2f}")
    print(f"IC > 0 Sessions: {np.mean(np.array(ics) > 0):.1%}")
    print("="*40)

if __name__ == "__main__":
    summarize()
