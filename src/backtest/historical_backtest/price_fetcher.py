"""
price_fetcher.py
=================
单 session 批量价格拉取（研究级回测）

设计重点：
  - 一次性 login → 循环 query → logout
  - 完全避免每支股票单独 login 的串行开销
  - 返回 {ticker: pd.Series(close, index=date)}
  - 前复权（adjustflag=2）
"""

import threading
import pandas as pd
from datetime import date

_BS_LOCK = threading.Lock()


def fetch_close_matrix(tickers: list[str],
                       start_date: str,
                       end_date: str) -> dict[str, pd.Series]:
    """
    批量获取所有标的的前复权收盘价序列。
    返回: {ticker: pd.Series(close, index=pd.DatetimeIndex)}
    失败的标的返回空 Series。

    使用单次 Baostock session 以获得最高效率。
    """
    import baostock as bs

    def _std_to_bs(sym: str) -> str:
        if sym.upper().endswith(".SS"):
            return f"sh.{sym[:-3]}"
        elif sym.upper().endswith(".SZ"):
            return f"sz.{sym[:-3]}"
        return sym

    result: dict[str, pd.Series] = {}

    with _BS_LOCK:
        bs.login()
        try:
            for ticker in tickers:
                bs_code = _std_to_bs(ticker)
                try:
                    rs = bs.query_history_k_data_plus(
                        bs_code, "date,close",
                        start_date=start_date,
                        end_date=end_date,
                        frequency="d",
                        adjustflag="2",
                    )
                    rows = []
                    while rs.next():
                        rows.append(rs.get_row_data())

                    if rows:
                        df = pd.DataFrame(rows, columns=["date", "close"])
                        df["date"]  = pd.to_datetime(df["date"])
                        df["close"] = pd.to_numeric(df["close"], errors="coerce")
                        df.dropna(inplace=True)
                        df.set_index("date", inplace=True)
                        result[ticker] = df["close"]
                    else:
                        result[ticker] = pd.Series(dtype=float)
                except Exception as e:
                    result[ticker] = pd.Series(dtype=float)
        finally:
            bs.logout()

    return result


def compute_forward_return(price_series: pd.Series,
                           signal_date: str,
                           hold_days: int) -> float | None:
    """
    计算从 signal_date 之后第 1 个交易日起、持有 hold_days 个交易日的收益率。
    返回: float 收益率 or None（数据不足）
    """
    sd = pd.Timestamp(signal_date)
    future = price_series[price_series.index > sd]

    if len(future) < hold_days:
        return None

    start_p = future.iloc[0]
    end_p   = future.iloc[hold_days - 1]

    if start_p == 0 or pd.isna(start_p) or pd.isna(end_p):
        return None

    return float(end_p / start_p) - 1.0


def get_market_cap_on_date(tickers: list[str], signal_date: str) -> dict[str, float]:
    """
    获取各标的在 signal_date 附近的流通市值（Baostock query_stock_basic 只有静态数据，
    此处用 circulating market cap 近似：前复权流通股数 × 收盘价，
    实用回测中以收盘价梯次切三等分代替精确市值）。
    返回: {ticker: float(市值代理值, 价格 × 1 即股价作排序代理)}
    注：此处直接用股价排序作大/中/小盘的区分代理（沪深300内相关性高）。
    """
    import baostock as bs

    def _std_to_bs(sym: str) -> str:
        if sym.upper().endswith(".SS"):
            return f"sh.{sym[:-3]}"
        return f"sz.{sym[:-3]}"

    caps = {}
    with _BS_LOCK:
        bs.login()
        try:
            for ticker in tickers:
                bs_code = _std_to_bs(ticker)
                try:
                    rs = bs.query_history_k_data_plus(
                        bs_code, "date,close,turn",
                        start_date=signal_date,
                        end_date=signal_date,
                        frequency="d",
                        adjustflag="2",
                    )
                    if rs.next():
                        row = rs.get_row_data()
                        caps[ticker] = float(row[1]) if row[1] else 0.0
                    else:
                        caps[ticker] = 0.0
                except Exception:
                    caps[ticker] = 0.0
        finally:
            bs.logout()

    return caps


def get_volatility_60d(tickers: list[str], signal_date: str,
                       price_matrix: dict[str, pd.Series]) -> dict[str, float]:
    """
    计算截至 signal_date 之前 60 个交易日的日收益率标准差（波动率代理）。
    """
    sd = pd.Timestamp(signal_date)
    vols = {}
    for ticker in tickers:
        series = price_matrix.get(ticker, pd.Series(dtype=float))
        hist = series[series.index <= sd]
        if len(hist) >= 2:
            daily_ret = hist.pct_change().dropna()
            hist_60 = daily_ret.iloc[-60:]
            vols[ticker] = float(hist_60.std()) if len(hist_60) > 1 else 0.0
        else:
            vols[ticker] = 0.0
    return vols
