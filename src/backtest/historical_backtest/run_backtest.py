"""
run_backtest.py — 研究级历史回测主入口
=========================================
用法:
  python run_backtest.py [--start 2024-01] [--end 2025-12] [--workers 8]

流程:
  1. 生成每月末信号（断点续跑）
  2. 单 session 批量拉取全部标的完整日线价格
  3. 计算三种组合 × 三种持有期的月度收益
  4. 统计评估（Sharpe / t-stat / 最大回撤 ...）
  5. 压力测试（牛熊分段 / 市值分组 / 去高波动）
  6. 输出 backtest_result.json + backtest_summary.txt
"""

import sys
import os
import json
import argparse
import statistics
from datetime import datetime, timedelta
from collections import defaultdict

# ── 路径设置 ─────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, ROOT)

from backtest.historical_backtest.signal_generator  import build_signal_dates, generate_monthly_signals
from backtest.historical_backtest.price_fetcher     import fetch_close_matrix, compute_forward_return, get_volatility_60d
from backtest.historical_backtest.portfolio_builder import build_all_portfolios, apply_volatility_filter
from backtest.historical_backtest.performance       import full_stats, compute_portfolio_spread, summarize_results
from backtest.historical_backtest.stress_test       import (
    get_index_monthly_return, classify_regime, split_records_by_regime
)

HERE          = os.path.dirname(__file__)
OUTPUT_JSON   = os.path.join(HERE, "backtest_result.json")
SUMMARY_TXT   = os.path.join(HERE, "backtest_summary.txt")
HOLD_PERIODS  = [10, 20, 30]


# ── 月份边界辅助 ─────────────────────────────────────────────
def month_start(ym: str) -> str:
    return ym + "-01"


def next_month_end(ym: str, price_matrix_all_dates: list) -> str | None:
    """获取 ym 所在月之后的第 30 个日历日（覆盖最长持有窗口）"""
    y, m = int(ym[:4]), int(ym[5:7])
    m += 1
    if m > 12:
        m = 1
        y += 1
    # 取下下个月初以确保覆盖 30 T-days
    m2 = m + 2
    y2 = y
    if m2 > 12:
        m2 -= 12
        y2 += 1
    return f"{y2}-{m2:02d}-01"


# ── 主函数 ────────────────────────────────────────────────────
def main(start_ym: str, end_ym: str, workers: int):
    run_start = datetime.now().isoformat()
    print("=" * 72)
    print("  ECHO  研究级历史回测  — Kronos A 股 Alpha 验证")
    print(f"  区间: {start_ym} → {end_ym}   持有期: {HOLD_PERIODS}   线程: {workers}")
    print("=" * 72)

    # ─ Step 1: 生成信号日列表 ──────────────────────────────────
    sy, sm = int(start_ym[:4]), int(start_ym[5:])
    ey, em = int(end_ym[:4]),   int(end_ym[5:])
    print("\n[1/5] 生成信号日列表...")
    signal_dates = build_signal_dates(sy, sm, ey, em)
    print(f"      共 {len(signal_dates)} 个信号日: {signal_dates[0]} → {signal_dates[-1]}")

    # ─ Step 2: 逐月生成/加载信号 ──────────────────────────────
    print("\n[2/5] 生成月频信号（断点续跑）...")
    all_signals_by_date: dict[str, list] = {}
    all_tickers_set: set = set()

    for sd in signal_dates:
        sigs = generate_monthly_signals(sd, max_workers=workers)
        all_signals_by_date[sd] = sigs
        for s in sigs:
            if not s.get("error") and s.get("ticker"):
                all_tickers_set.add(s["ticker"])

    print(f"\n      信号生成完毕，涉及 {len(all_tickers_set)} 只唯一标的")

    # ─ Step 3: 批量拉取价格矩阵 ───────────────────────────────
    print("\n[3/5] 单 session 批量拉取全历史价格...")
    # 时间窗口：start_ym 往前多取 90 天（供 60 日波动率计算），
    # end_ym 往后多取 45 天（供最后一个信号的 30 T-day 持有期）
    price_start = f"{sy - 1 if sm == 1 else sy}-{12 if sm == 1 else sm - 1:02d}-01"
    price_start = f"{sy}-01-01"   # 简化：直接从 2024-01-01
    # end_ym + 2 months
    end_m2 = em + 2
    end_y2 = ey
    if end_m2 > 12:
        end_m2 -= 12
        end_y2 += 1
    price_end = f"{end_y2}-{end_m2:02d}-28"

    all_tickers = sorted(all_tickers_set)
    price_matrix = fetch_close_matrix(all_tickers, price_start, price_end)
    print(f"      价格矩阵加载完毕，{sum(1 for v in price_matrix.values() if not v.empty)} 只有效")

    # ─ Step 4: 计算月度组合收益 ───────────────────────────────
    print("\n[4/5] 计算月度组合收益...")
    monthly_records: list[dict] = []
    regime_map:      dict[str, str] = {}

    for sd in signal_dates:
        sigs = all_signals_by_date[sd]
        portfolios = build_all_portfolios(sigs)

        ym = sd[:7]
        # 计算该月市场机制
        mstart = sd[:8] + "01"  # 月初
        index_ret = get_index_monthly_return(mstart, sd)
        regime_map[sd] = classify_regime(index_ret)

        # 波动率过滤器（用于压力测试，不改变主组合）
        vols = get_volatility_60d(all_tickers, sd, price_matrix)

        for port in portfolios:
            for hold in HOLD_PERIODS:
                # 主组合
                long_rets  = [compute_forward_return(price_matrix.get(t, __import__("pandas").Series(dtype=float)), sd, hold)
                              for t in port["long"]]
                short_rets = [compute_forward_return(price_matrix.get(t, __import__("pandas").Series(dtype=float)), sd, hold)
                              for t in port["short"]]

                valid_long  = [r for r in long_rets  if r is not None]
                valid_short = [r for r in short_rets if r is not None]
                long_ret_mean  = statistics.mean(valid_long)  if valid_long  else None
                short_ret_mean = statistics.mean(valid_short) if valid_short else None

                monthly_records.append({
                    "signal_date":    sd,
                    "regime":         regime_map[sd],
                    "portfolio_label": port["label"],
                    "hold_days":      hold,
                    "long_count":     len(valid_long),
                    "short_count":    len(valid_short),
                    "long_ret":       round(long_ret_mean,  6) if long_ret_mean  is not None else None,
                    "short_ret":      round(short_ret_mean, 6) if short_ret_mean is not None else None,
                })

                # 去高波动版本
                filt_port  = apply_volatility_filter(port, vols)
                fl_rets    = [compute_forward_return(price_matrix.get(t, __import__("pandas").Series(dtype=float)), sd, hold)
                              for t in filt_port["long"]]
                fs_rets    = [compute_forward_return(price_matrix.get(t, __import__("pandas").Series(dtype=float)), sd, hold)
                              for t in filt_port["short"]]
                fl_mean    = statistics.mean([r for r in fl_rets if r is not None]) if any(r is not None for r in fl_rets) else None
                fs_mean    = statistics.mean([r for r in fs_rets if r is not None]) if any(r is not None for r in fs_rets) else None

                monthly_records.append({
                    "signal_date":    sd,
                    "regime":         regime_map[sd],
                    "portfolio_label": filt_port["label"],
                    "hold_days":      hold,
                    "long_count":     len([r for r in fl_rets if r is not None]),
                    "short_count":    len([r for r in fs_rets if r is not None]),
                    "long_ret":       round(fl_mean,  6) if fl_mean  is not None else None,
                    "short_ret":      round(fs_mean,  6) if fs_mean  is not None else None,
                })

        print(f"    完成: {sd}  机制={regime_map[sd]}  组合×持有={len(portfolios)*len(HOLD_PERIODS)}", flush=True)

    # ─ Step 5: 统计汇总 + 压力测试 ───────────────────────────
    print("\n[5/5] 汇总统计与压力测试...")
    summary = summarize_results(monthly_records)

    # 市场机制分段汇总
    regime_summary = {}
    for (label, hold), key in [(k.rsplit("__hold", 1)[0], k.rsplit("d", 1)[0].split("hold")[1])
                                 for k in summary]:
        pass  # 在 JSON 里已按 regime 字段可以二次分析
    # 简化：对每个 key，按 regime 切分并单独统计
    regime_detail = {}
    groups_by_key: dict[str, list] = defaultdict(list)
    for rec in monthly_records:
        key = f"{rec['portfolio_label']}__hold{rec['hold_days']}d"
        groups_by_key[key].append(rec)

    for key, records in groups_by_key.items():
        by_regime = split_records_by_regime(records, regime_map)
        regime_detail[key] = {}
        for r_name, r_recs in by_regime.items():
            spreads = compute_portfolio_spread(
                [r["long_ret"] for r in r_recs],
                [r["short_ret"] for r in r_recs],
            )
            regime_detail[key][r_name] = full_stats(spreads)

    # ─ 输出 JSON ─────────────────────────────────────────────
    output = {
        "meta": {
            "test_name":      "Kronos HS300 Historical Backtest",
            "backtest_range": f"{start_ym} → {end_ym}",
            "signal_dates":   signal_dates,
            "hold_periods":   HOLD_PERIODS,
            "run_start":      run_start,
            "run_end":        datetime.now().isoformat(),
            "total_tickers":  len(all_tickers_set),
        },
        "portfolio_stats":  summary,
        "regime_breakdown": regime_detail,
        "monthly_records":  monthly_records,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    # ─ 输出易读摘要 ───────────────────────────────────────────
    lines = []
    lines.append("=" * 72)
    lines.append("  Kronos HS300 历史回测摘要")
    lines.append(f"  区间: {start_ym} → {end_ym}")
    lines.append("=" * 72)
    for key, val in summary.items():
        s = val["stats"]
        lines.append(f"\n  [{key}]")
        lines.append(f"    月数 N={s['n']}  均多空价差={s.get('mean_pct','—')}%  胜率={s.get('win_rate','—')}")
        lines.append(f"    Sharpe={s.get('sharpe','—')}  t-stat={s.get('t_stat','—')}  最大回撤={s.get('max_drawdown','—')}%")

    summary_text = "\n".join(lines)
    with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(summary_text)
    print(f"\n  完整结果: {OUTPUT_JSON}")
    print(f"  摘要报告: {SUMMARY_TXT}")
    print("=" * 72)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start",   default="2024-01", help="回测开始年月 YYYY-MM")
    parser.add_argument("--end",     default="2025-12", help="回测结束年月 YYYY-MM")
    parser.add_argument("--workers", type=int, default=8, help="并发线程数")
    args = parser.parse_args()
    main(args.start, args.end, args.workers)
