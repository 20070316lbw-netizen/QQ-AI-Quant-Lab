"""
stress_test.py
==============
三种压力测试（研究级回测）

1. 市场分段（牛/熊/震荡）
   按沪深 300 指数月涨跌幅划分：
     牛: >+3%  震荡: [-3%, +3%]  熊: <-3%

2. 市值分组（大/中/小盘）
   调用 price_fetcher.split_by_market_cap

3. 去除高波动
   调用 portfolio_builder.apply_volatility_filter (排除前 10%)
"""

from __future__ import annotations


# ── 沪深 300 指数月涨跌幅 ─────────────────────────────────────
def get_index_monthly_return(month_start: str, month_end: str) -> float | None:
    """
    用 Baostock 查询沪深 300 指数（000300.XSHG → sh.000300）
    在 [month_start, month_end] 的涨跌幅。
    """
    import threading
    import baostock as bs

    _lock = threading.Lock()
    idx_code = "sh.000300"

    try:
        with _lock:
            bs.login()
            try:
                rs = bs.query_history_k_data_plus(
                    idx_code, "date,close",
                    start_date=month_start,
                    end_date=month_end,
                    frequency="m",   # 月频
                    adjustflag="3",
                )
                rows = []
                while rs.next():
                    rows.append(rs.get_row_data())
            finally:
                bs.logout()

        if not rows:
            return None

        # 如果是月频只会有一行; 若用日频取首尾也行
        # 这里用首行 close 和尾行 close 计算区间收益
        # 简化：直接查日频首尾
        with _lock:
            bs.login()
            try:
                rs2 = bs.query_history_k_data_plus(
                    idx_code, "date,close",
                    start_date=month_start,
                    end_date=month_end,
                    frequency="d",
                    adjustflag="3",
                )
                daily = []
                while rs2.next():
                    daily.append(rs2.get_row_data())
            finally:
                bs.logout()

        if len(daily) < 2:
            return None

        start_close = float(daily[0][1])
        end_close   = float(daily[-1][1])
        return (end_close / start_close) - 1.0

    except Exception:
        return None


def classify_regime(monthly_ret: float | None,
                    bull_thresh: float = 0.03,
                    bear_thresh: float = -0.03) -> str:
    """牛/震荡/熊 分段"""
    if monthly_ret is None:
        return "unknown"
    if monthly_ret > bull_thresh:
        return "bull"
    elif monthly_ret < bear_thresh:
        return "bear"
    else:
        return "ranging"


def split_records_by_regime(monthly_records: list[dict],
                             regime_map: dict[str, str]) -> dict[str, list]:
    """
    将月度记录按市场机制分组。
    regime_map: {signal_date: "bull"/"bear"/"ranging"}
    """
    groups: dict[str, list] = {"bull": [], "bear": [], "ranging": [], "unknown": []}
    for rec in monthly_records:
        r = regime_map.get(rec["signal_date"], "unknown")
        groups[r].append(rec)
    return groups


def split_records_by_cap(monthly_records: list[dict],
                          cap_tier_map: dict[str, str]) -> dict[str, list]:
    """
    按市值分组（large/mid/small），每条 record 对应多头/空头的 ticker list，
    此处按每个 ticker 的 cap tier 拆分独立收益记录。
    cap_tier_map: {ticker: "large"/"mid"/"small"}
    用于 split_by_market_cap 后单独计算各 tier 的统计。
    """
    groups: dict[str, list] = {"large": [], "mid": [], "small": []}
    for rec in monthly_records:
        tier = cap_tier_map.get(rec.get("ticker", ""), "small")
        groups.setdefault(tier, []).append(rec)
    return groups
