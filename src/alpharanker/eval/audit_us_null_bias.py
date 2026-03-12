"""
audit_us_null_bias.py
======================
深度审计美股特征宽表 (us_features_regime.parquet) 中的空值情况。
重点核实：
1. concat 引入的空值是否偏向特定截面或特征。
2. 熊市 (Bear) Regime 下 vol_60d_res 的有效样本量。
3. 重跑 Bear Regime 下的 Rank IC，与 0.1809 对比。
"""
import os
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import statsmodels.api as sm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import DATA_ROOT

FEAT_PATH = os.path.join(DATA_ROOT, 'us', 'us_features_regime.parquet')
ALL_FACTORS = ['mom_12m', 'vol_60d_res', 'sp_ratio', 'asset_turnover']

def newey_west_t(series):
    if len(series) < 5: return np.nan
    y = series.values
    X = np.ones(len(y))
    model = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': min(len(y)-1, 4)})
    return model.tvalues[0]

def main():
    if not os.path.exists(FEAT_PATH):
        print(f"❌ 找不到宽表: {FEAT_PATH}")
        return

    df = pd.read_parquet(FEAT_PATH)
    print(f">> 宽表总行数: {len(df):,}  |  列数: {len(df.columns)}")
    print(f">> 日期范围: {df['report_date'].min()} ~ {df['report_date'].max()}")
    print(f">> Regime 分布:\n{df['regime_label'].value_counts()}\n")

    # ──────────────────────────────────────────────────
    # 1. 空值分布检查
    # ──────────────────────────────────────────────────
    print("="*70)
    print("  1. 空值率审计")
    print("="*70)
    audit_cols = ALL_FACTORS + ['label_3m_return', 'regime_label']
    null_stats = []
    for col in audit_cols:
        if col in df.columns:
            total = len(df)
            null_n = df[col].isna().sum()
            null_stats.append({'Column': col, 'Total': total, 'NullCount': null_n, 'NullRate': f"{null_n/total*100:.1f}%"})
    print(pd.DataFrame(null_stats).to_string(index=False))

    # ──────────────────────────────────────────────────
    # 2. 熊市截面有效样本量验证
    # ──────────────────────────────────────────────────
    BEAR = df[df['regime_label'] == 'Bear']
    print(f"\n>> Bear Regime 行数: {len(BEAR):,}")
    print(f">> Bear Regime 截面数: {BEAR['report_date'].nunique()}")
    print(f">> Bear Regime vol_60d_res 空值率: {BEAR['vol_60d_res'].isna().mean()*100:.1f}%")

    # ──────────────────────────────────────────────────
    # 3. 重跑 Bear Regime Rank IC（含 NW t-stat）
    # ──────────────────────────────────────────────────
    print("\n" + "="*70)
    print("  2. Bear Regime 重跑 Rank IC (vs 原始结论 0.1809)")
    print("="*70)
    label_col = 'label_3m_return'
    BEAR_CLEAN = BEAR.dropna(subset=['vol_60d_res', label_col])
    print(f">> 去空后 Bear 有效样本: {len(BEAR_CLEAN):,}")

    ic_list = []
    for date, grp in BEAR_CLEAN.groupby('report_date'):
        if len(grp) > 10 and grp['vol_60d_res'].std() > 1e-6 and grp[label_col].std() > 1e-6:
            ic, _ = spearmanr(grp['vol_60d_res'], grp[label_col])
            ic_list.append((date, ic))

    ic_series = pd.Series(dict(ic_list))
    mean_ic = ic_series.mean()
    nw_t = newey_west_t(ic_series)
    print(f"\n  vol_60d_res | Bear Regime")
    print(f"  Mean Rank IC  : {mean_ic:.4f}")
    print(f"  NW t-stat     : {nw_t:.4f}")
    print(f"  Periods used  : {len(ic_series)}")
    print(f"\n  [原始结论: IC≈0.1809] — 本次结论: IC≈{mean_ic:.4f}")
    delta = abs(mean_ic - 0.1809)
    if delta < 0.01:
        print("  ✅ 结论稳健：与原始发现极为接近，空值未影响关键结论。")
    elif delta < 0.05:
        print(f"  ⚠️  结论轻微偏差 {delta:.4f}：建议留意，但核心方向不变。")
    else:
        print(f"  ❌ 结论显著偏差 {delta:.4f}：原始结论受空值污染，需报告修正！")

    # ──────────────────────────────────────────────────
    # 4. 全因子全 Regime 重跑
    # ──────────────────────────────────────────────────
    print("\n" + "="*70)
    print("  3. 全因子 × 全 Regime IC 稳健性重跑")
    print("="*70)
    rows = []
    for regime in df['regime_label'].dropna().unique():
        rdf = df[df['regime_label'] == regime]
        for fcol in ALL_FACTORS:
            if fcol not in df.columns: continue
            clean = rdf.dropna(subset=[fcol, label_col])
            if len(clean) < 50: continue
            ic_lst = []
            for d, grp in clean.groupby('report_date'):
                if len(grp) > 5 and grp[fcol].std() > 1e-6:
                    ic, _ = spearmanr(grp[fcol], grp[label_col])
                    ic_lst.append(ic)
            if ic_lst:
                s = pd.Series(ic_lst)
                rows.append({'Regime': regime, 'Factor': fcol, 'MeanIC': round(s.mean(), 4), 'NW_t': round(newey_west_t(s), 3), 'N': len(ic_lst)})

    result = pd.DataFrame(rows)
    pivot = result.pivot(index='Factor', columns='Regime', values='MeanIC')
    print(pivot.to_string())
    print("\n  [t-stat]")
    pivot_t = result.pivot(index='Factor', columns='Regime', values='NW_t')
    print(pivot_t.to_string())

if __name__ == "__main__":
    main()
