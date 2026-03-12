import pandas as pd
import numpy as np
import os
import json
from scipy.stats import spearmanr

class FactorMonitor:
    def __init__(self):
        # 尝试加载注册表
        self.registry_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "factor_registry.json")
        self.registry = {}
        if os.path.exists(self.registry_path):
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)

    def generate_ic_report(self, df, feature_cols, target_col="label_next_month"):
        print("\n" + "="*50)
        print(" 🔍 [Factor IC Report] 自动因子监控与评测单")
        print("="*50)
        
        results = []
        for feature in feature_cols:
            mask = df[[feature, target_col]].notna().all(axis=1)
            valid_df = df[mask]
            
            if len(valid_df) < 20:
                ic = np.nan
            else:
                # 截面 IC 均值
                try:
                    ics = []
                    for d, grp in valid_df.groupby("date"):
                        if len(grp) > 10:
                            ic_val, _ = spearmanr(grp[feature], grp[target_col])
                            ics.append(ic_val)
                    ic = np.nanmean(ics)
                except Exception:
                    ic = np.nan
            
            # 从注册表获取中文名称与类别
            meta = self.registry.get(feature, {})
            zh_name = meta.get("name", feature)
            category = meta.get("category", "Unknown")
            
            results.append({
                "因子/特征": feature,
                "中文名称": zh_name,
                "派系": category,
                "Rank IC": ic
            })
            
            # 控制台即刻打印
            ic_str = f"{ic:+.4f}" if not np.isnan(ic) else "N/A"
            print(f" 🎯 [{category}] {zh_name} ({feature}): IC = {ic_str}")

        print("="*50 + "\n")
        return pd.DataFrame(results)

if __name__ == "__main__":
    # Test stub
    fm = FactorMonitor()
    print("监控引擎已挂载并就绪。注册表载入状态：", len(fm.registry), "个因子条目")
