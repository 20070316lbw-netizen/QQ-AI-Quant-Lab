"""
performance.py
==============
研究级统计评估指标

指标:
  1. 月均多空价差 mean(spread)
  2. 胜率 P(spread > 0)
  3. 波动率 std(spread)
  4. 年化夏普 mean/std × sqrt(12)
  5. t-统计量 mean / (std/sqrt(N))
  6. 最大回撤 (累计净值曲线)
  7. 正收益月数 / 负收益月数
"""

from __future__ import annotations
import math
import statistics


def compute_portfolio_spread(long_returns: list[float | None],
                             short_returns: list[float | None]) -> list[float]:
    """等权多空价差（剔除 None）"""
    paired = [(l, s) for l, s in zip(long_returns, short_returns)
              if l is not None and s is not None]
    return [l - s for l, s in paired] if paired else []


def compute_leg_return(returns: list[float | None]) -> float | None:
    """等权平均（剔除 None）"""
    valid = [r for r in returns if r is not None]
    return statistics.mean(valid) if valid else None


def cumulative_nav(spreads: list[float]) -> list[float]:
    """从等权多空价差序列构建累计净值（初始 = 1）"""
    nav = [1.0]
    for r in spreads:
        nav.append(nav[-1] * (1 + r))
    return nav


def max_drawdown(nav: list[float]) -> float:
    """最大回撤（正数，如 0.15 = -15%）"""
    if not nav:
        return 0.0
    peak = nav[0]
    dd   = 0.0
    for v in nav:
        if v > peak:
            peak = v
        drawdown = (peak - v) / peak
        if drawdown > dd:
            dd = drawdown
    return round(dd, 6)


def full_stats(spreads: list[float], freq: int = 12) -> dict:
    """
    完整统计，freq = 信号频率（12 = 月频）。
    """
    n = len(spreads)
    if n == 0:
        return {
            "n": 0, "mean_spread": None, "mean_pct": None,
            "win_rate": None, "stdev": None, "sharpe": None,
            "t_stat": None, "max_drawdown": None,
            "positive_months": 0, "negative_months": 0,
        }

    mean_s = statistics.mean(spreads)
    std_s  = statistics.stdev(spreads) if n > 1 else 0.0
    win    = sum(1 for s in spreads if s > 0)
    nav    = cumulative_nav(spreads)
    mdd    = max_drawdown(nav)

    sharpe = (mean_s / std_s * math.sqrt(freq)) if std_s > 1e-9 else None
    t_stat = (mean_s / (std_s / math.sqrt(n))) if std_s > 1e-9 else None

    return {
        "n":               n,
        "mean_spread":     round(mean_s, 6),
        "mean_pct":        round(mean_s * 100, 4),
        "win_rate":        round(win / n, 4),
        "stdev":           round(std_s, 6),
        "sharpe":          round(sharpe, 4) if sharpe is not None else None,
        "t_stat":          round(t_stat, 4) if t_stat is not None else None,
        "max_drawdown":    round(mdd * 100, 4),   # as %
        "positive_months": win,
        "negative_months": n - win,
        "nav_series":      [round(v, 6) for v in nav],
    }


def summarize_results(monthly_records: list[dict]) -> dict:
    """
    将所有月份的 per-portfolio 收益汇总为统计对象。
    monthly_records: [{signal_date, portfolio_label, hold_days, long_ret, short_ret}, ...]
    """
    from collections import defaultdict
    groups = defaultdict(list)
    for rec in monthly_records:
        key = (rec["portfolio_label"], rec["hold_days"])
        groups[key].append(rec)

    output = {}
    for (label, hold), records in sorted(groups.items()):
        long_rets  = [r.get("long_ret")  for r in records]
        short_rets = [r.get("short_ret") for r in records]
        spreads    = compute_portfolio_spread(long_rets, short_rets)
        stats      = full_stats(spreads)
        output[f"{label}__hold{hold}d"] = {
            "portfolio": label,
            "hold_days": hold,
            "stats":     stats,
            "monthly":   records,
        }
    return output
