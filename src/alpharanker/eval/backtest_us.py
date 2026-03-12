"""
backtest_us.py
===============
美股 AlphaRanker 回测脚本。

策略逻辑：
  - 每个季度财报发布后，用模型对全部 503 只股票打分
  - 买入 Top-N 只，持有到下一个季度末（约 63 个交易日）
  - 等权重持仓，不考虑交易成本

输出：
  - IC 时间序列（柱状图）
  - 五分位分组收益柱状图
  - Top20 vs 等权基准净值曲线
  - backtest_report.png
"""

import os
import sys
import pickle
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import MODEL_DIR

FEATURES_PATH = r"C:\Data\Market\us\us_features.parquet"
MODEL_PATH    = os.path.join(MODEL_DIR, "us_lgbm.pkl")
REPORT_PATH   = os.path.join(MODEL_DIR, "backtest_report.png")

FEATURE_COLS = [
    "gross_margin", "operating_margin", "net_margin", "ebitda_margin", "roe", "roa", "asset_turnover",
    "revenue_growth_yoy", "ni_growth_yoy", "eps_growth_yoy", "op_income_growth_yoy", "gross_profit_growth",
    "fcf_margin", "ocf_to_ni", "capex_to_revenue",
    "current_ratio", "debt_to_equity", "cash_to_assets",
    "mom_1m", "mom_3m", "mom_6m", "mom_12m", "vol_20d", "vol_60d",
    "pe_ratio", "ps_ratio", "pb_ratio", "ev_ebitda",
]

TOP_N = 20      # 每期买入的股票数
N_GROUPS = 5    # 分组数（五分位）


def run_backtest():
    print("=" * 55)
    print("  AlphaRanker — 美股回测")
    print("=" * 55)

    # ── 加载数据和模型 ────────────────────────────────────────────────────────
    df = pd.read_parquet(FEATURES_PATH)
    df["report_date"] = pd.to_datetime(df["report_date"])

    with open(MODEL_PATH, "rb") as f:
        payload = pickle.load(f)
    model   = payload["model"]
    features = payload["features"]

    # 只保留有标签的样本（model 对没标签的也可以预测，但评估需要标签）
    df_eval = df[df["label_3m_return"].notna()].copy()
    print(f"\n有效样本: {len(df_eval)} 行 | 截面: {df_eval['report_date'].nunique()} | 股票: {df_eval['ticker'].nunique()}")

    dates = sorted(df_eval["report_date"].unique())

    # ── 逐截面预测 ────────────────────────────────────────────────────────────
    ic_records = []       # 每期IC
    quintile_rets = []    # 每期各分位组收益
    top_rets = []         # 每期 Top-N 组合收益
    bench_rets = []       # 每期等权基准收益

    for date in dates:
        grp = df_eval[df_eval["report_date"] == date].copy()
        if len(grp) < N_GROUPS * 2:
            continue

        valid_feats = [c for c in features if c in grp.columns]
        X = grp[valid_feats].values.astype(np.float32)
        grp["score"] = model.predict(X)

        # IC
        ic, _ = spearmanr(grp["score"], grp["label_3m_return"])
        ic_records.append({"date": date, "ic": ic, "n": len(grp)})

        # 五分位分组
        grp["quintile"] = pd.qcut(grp["score"], N_GROUPS, labels=False, duplicates="drop")
        for q in range(N_GROUPS):
            q_ret = grp[grp["quintile"] == q]["label_3m_return"].mean()
            quintile_rets.append({"date": date, "quintile": q + 1, "ret": q_ret})

        # Top-N 组合收益
        top_grp = grp.nlargest(TOP_N, "score")
        top_ret = top_grp["label_3m_return"].mean()
        bench_ret = grp["label_3m_return"].mean()
        top_rets.append(top_ret)
        bench_rets.append(bench_ret)

    if not ic_records:
        print("❌ 没有可评估的截面（需要有 label_3m_return 的样本）")
        return

    ic_df = pd.DataFrame(ic_records)
    qr_df = pd.DataFrame(quintile_rets)

    # ── 汇总指标 ──────────────────────────────────────────────────────────────
    mean_ic   = ic_df["ic"].mean()
    std_ic    = ic_df["ic"].std()
    icir      = mean_ic / (std_ic + 1e-8)
    ic_pos_pct = (ic_df["ic"] > 0).mean()

    # 净值曲线（累计复利）
    top_nav   = np.cumprod([1 + r for r in top_rets])
    bench_nav = np.cumprod([1 + r for r in bench_rets])
    final_alpha = top_nav[-1] - bench_nav[-1] if len(top_nav) > 0 else 0

    print(f"\n{'─'*40}")
    print(f"  均值 IC   : {mean_ic:.4f}")
    print(f"  IC 标准差 : {std_ic:.4f}")
    print(f"  ICIR      : {icir:.4f}")
    print(f"  IC>0 比例 : {ic_pos_pct:.1%}")
    print(f"  Top{TOP_N} 累计收益 : {top_nav[-1]-1:.2%}")
    print(f"  等权基准累计收益  : {bench_nav[-1]-1:.2%}")
    print(f"  超额收益          : {final_alpha:.2%}")
    print(f"{'─'*40}")

    # ── 绘图 ──────────────────────────────────────────────────────────────────
    date_labels = [str(d)[:7] for d in ic_df["date"]]
    fig = plt.figure(figsize=(16, 12))
    fig.patch.set_facecolor("#0d1117")
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)

    ACCENT = "#6366f1"
    GREEN  = "#10b981"
    RED    = "#ef4444"
    MUTED  = "#94a3b8"
    BG     = "#161b22"

    def style_ax(ax, title):
        ax.set_facecolor(BG)
        ax.set_title(title, color="white", fontsize=12, pad=10)
        ax.tick_params(colors=MUTED, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)

    # 1. IC 柱状图
    ax1 = fig.add_subplot(gs[0, 0])
    colors = [GREEN if v > 0 else RED for v in ic_df["ic"]]
    ax1.bar(range(len(ic_df)), ic_df["ic"], color=colors, alpha=0.85)
    ax1.axhline(0, color=MUTED, lw=0.8, linestyle="--")
    ax1.axhline(mean_ic, color=ACCENT, lw=1.5, linestyle="--", label=f"Mean IC={mean_ic:.3f}")
    ax1.set_xticks(range(len(ic_df)))
    ax1.set_xticklabels(date_labels, rotation=45, ha="right")
    ax1.legend(fontsize=8, labelcolor="white", facecolor=BG, edgecolor="#30363d")
    style_ax(ax1, f"IC by Quarter (ICIR={icir:.2f})")

    # 2. 五分位分组平均收益
    ax2 = fig.add_subplot(gs[0, 1])
    q_mean = qr_df.groupby("quintile")["ret"].mean()
    bar_colors = [RED, "#f59e0b", MUTED, "#34d399", GREEN]
    ax2.bar(q_mean.index, q_mean.values * 100, color=bar_colors, alpha=0.9)
    ax2.set_xlabel("Quintile (1=Lowest Score, 5=Highest)")
    ax2.set_ylabel("Avg 3-Month Return (%)")
    ax2.axhline(0, color=MUTED, lw=0.8)
    for i, (q, v) in enumerate(q_mean.items()):
        ax2.text(q, v * 100 + 0.1, f"{v:.1%}", ha="center", fontsize=8, color="white")
    style_ax(ax2, "Quintile Group Returns")

    # 3. 净值曲线
    ax3 = fig.add_subplot(gs[1, :])
    x = range(len(top_nav))
    ax3.plot(x, top_nav, color=ACCENT, lw=2, label=f"Top{TOP_N} Portfolio")
    ax3.plot(x, bench_nav, color=MUTED, lw=1.5, linestyle="--", label="Equal-Weight Benchmark")
    ax3.fill_between(x, top_nav, bench_nav, where=[t > b for t, b in zip(top_nav, bench_nav)],
                     color=ACCENT, alpha=0.15, label="Alpha")
    ax3.set_xticks(x)
    ax3.set_xticklabels(date_labels, rotation=45, ha="right")
    ax3.set_ylabel("Cumulative Return (×1)")
    ax3.legend(fontsize=9, labelcolor="white", facecolor=BG, edgecolor="#30363d")
    ax3.axhline(1.0, color=MUTED, lw=0.5)
    style_ax(ax3, f"Top-{TOP_N} Portfolio vs Equal-Weight Benchmark")

    fig.suptitle("US AlphaRanker — Backtest Report", color="white", fontsize=15, fontweight="bold", y=0.98)

    plt.savefig(REPORT_PATH, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"\n✅ 回测报告已保存: {REPORT_PATH}")
    return ic_df, q_mean


if __name__ == "__main__":
    run_backtest()
