import pandas as pd
import os
import numpy as np
from tqdm import tqdm

# Path from config
FEATURES_PATH = r'C:\Data\Market\cn\cn_features_enhanced.parquet'

def verify_neutralization():
    if not os.path.exists(FEATURES_PATH):
        print(f"File not found: {FEATURES_PATH}")
        return

    df = pd.read_parquet(FEATURES_PATH)
    
    # 选取一个因子进行验证，例如 mom_60d_rank
    factor = "mom_60d_rank"
    
    if factor not in df.columns:
        print(f"Factor {factor} not found in columns: {df.columns}")
        return
        
    # 检查行业中性化：每个截面每个行业的均值是否接近 0 (或者 rank 的均值是否接近 0.5)
    print(f"Checking Industry Neutralization for {factor}...")
    industry_means = df.groupby(["date", "industry_name"])[factor].mean()
    print(f"Mean of Industry-grouped means: {industry_means.mean():.4f} (Expected near 0.5 for rank)")
    print(f"Std of Industry-grouped means: {industry_means.std():.4f} (Expected very low)")
    
    # 检查市值中性化：因子与 size_proxy 的相关性
    if "size_proxy" in df.columns:
        print(f"\nChecking Size Neutralization for {factor}...")
        corrs = []
        for d, grp in df.groupby("date"):
            mask = grp[[factor, "size_proxy"]].notna().all(axis=1)
            if mask.sum() > 20:
                corr = grp.loc[mask, factor].corr(grp.loc[mask, "size_proxy"])
                corrs.append(corr)
        print(f"Average Correlation with Size: {np.mean(corrs):.4f} (Expected near 0)")
    else:
        print("\nsize_proxy column not found.")

if __name__ == "__main__":
    verify_neutralization()
