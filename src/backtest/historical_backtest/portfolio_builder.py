"""
portfolio_builder.py
=====================
三种组合构建规则（研究级回测）

组合 A：全体多空（等权）
  多头 = 所有 direction=BUY
  空头 = 所有 direction=SELL

组合 B：强信号多空
  |z_score| > 1.5 才纳入

组合 C：排序 30%
  按 z_score 从高到低排序
  前 30% 做多，后 30% 做空
"""

from __future__ import annotations


def _valid(sig: dict) -> bool:
    return (sig.get("direction") in ("BUY", "SELL")
            and sig.get("z_score") is not None
            and not sig.get("error"))


def build_portfolio_a(signals: list[dict]) -> dict:
    """组合 A：全体多空"""
    longs  = [s["ticker"] for s in signals if _valid(s) and s["direction"] == "BUY"]
    shorts = [s["ticker"] for s in signals if _valid(s) and s["direction"] == "SELL"]
    return {"long": longs, "short": shorts, "label": "A_all_longshort"}


def build_portfolio_b(signals: list[dict], z_threshold: float = 1.5) -> dict:
    """组合 B：强信号多空 (|z|>threshold)"""
    longs = [
        s["ticker"] for s in signals
        if _valid(s) and s["direction"] == "BUY"
        and abs(s["z_score"]) > z_threshold
    ]
    shorts = [
        s["ticker"] for s in signals
        if _valid(s) and s["direction"] == "SELL"
        and abs(s["z_score"]) > z_threshold
    ]
    return {"long": longs, "short": shorts, "label": f"B_strong_z{z_threshold}"}


def build_portfolio_c(signals: list[dict], pct: float = 0.30) -> dict:
    """组合 C：Top/Bottom pct% by z_score 排序"""
    valid = [s for s in signals if _valid(s)]
    if not valid:
        return {"long": [], "short": [], "label": f"C_top_bottom_{int(pct*100)}pct"}

    sorted_by_z = sorted(valid, key=lambda x: x["z_score"], reverse=True)
    n = len(sorted_by_z)
    k = max(1, int(n * pct))
    longs  = [s["ticker"] for s in sorted_by_z[:k]]
    shorts = [s["ticker"] for s in sorted_by_z[-k:]]
    return {"long": longs, "short": shorts, "label": f"C_top_bottom_{int(pct*100)}pct"}


def build_all_portfolios(signals: list[dict]) -> list[dict]:
    return [
        build_portfolio_a(signals),
        build_portfolio_b(signals),
        build_portfolio_c(signals),
    ]


def apply_volatility_filter(portfolio: dict, vol_dict: dict,
                            top_pct_exclude: float = 0.10) -> dict:
    """
    去除过去 60 日波动率前 top_pct_exclude 的标的（压力测试用）。
    返回过滤后的新组合 dict。
    """
    if not vol_dict:
        return portfolio

    all_vols = sorted(vol_dict.values())
    threshold_idx = int(len(all_vols) * (1 - top_pct_exclude))
    threshold = all_vols[threshold_idx] if threshold_idx < len(all_vols) else float("inf")

    filtered_long  = [t for t in portfolio["long"]  if vol_dict.get(t, 0) < threshold]
    filtered_short = [t for t in portfolio["short"] if vol_dict.get(t, 0) < threshold]

    return {**portfolio,
            "long":  filtered_long,
            "short": filtered_short,
            "label": portfolio["label"] + "_vol_filtered"}


def split_by_market_cap(portfolio: dict, cap_dict: dict) -> dict[str, dict]:
    """
    按市值三等份切分大/中/小盘，返回三个子组合。
    """
    all_caps = [(t, cap_dict.get(t, 0))
                for t in portfolio["long"] + portfolio["short"]]
    sorted_caps = sorted(all_caps, key=lambda x: x[1], reverse=True)
    n = len(sorted_caps)
    k = max(1, n // 3)

    large_set  = {t for t, _ in sorted_caps[:k]}
    mid_set    = {t for t, _ in sorted_caps[k:2*k]}
    small_set  = {t for t, _ in sorted_caps[2*k:]}

    segments = {"large": large_set, "mid": mid_set, "small": small_set}
    result   = {}
    for name, tick_set in segments.items():
        result[name] = {
            "long":  [t for t in portfolio["long"]  if t in tick_set],
            "short": [t for t in portfolio["short"] if t in tick_set],
            "label": f"{portfolio['label']}_{name}_cap",
        }
    return result
