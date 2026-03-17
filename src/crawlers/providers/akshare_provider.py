"""
A 股数据提供商 (Baostock 引擎)
==========================================
主路由: Baostock —— 使用专属 TCP 协议 (端口 9876)，完全绕过 HTTP 代理/TUN 干扰。

Baostock 代码格式:
  沪市: sh.600519 (贵州茅台)
  深市: sz.000001 (平安银行)
  输入: "600519.SS" 或 "000001.SZ" → 自动转换

线程安全:
  Baostock 底层使用全局单一 TCP 连接，不支持并发 login/logout。
  本模块使用 _BS_LOCK 全局锁将所有 baostock 调用序列化，确保多线程安全。
"""

import re
import threading
import pandas as pd

# 全局锁：保护 Baostock 单一 TCP 连接在多线程场景下不被踩踏
_BS_LOCK = threading.Lock()


def _strip_and_classify(symbol: str) -> tuple:
    """从 "000001.SZ" / "600519.SS" 提取代码和交易所"""
    upper = symbol.upper()
    if ".SZ" in upper:
        code = re.sub(r"\.SZ$", "", upper, flags=re.I)
        market = "sz"
    elif ".SS" in upper:
        code = re.sub(r"\.SS$", "", upper, flags=re.I)
        market = "sh"
    else:
        raw = symbol.strip()
        market = "sh" if raw.startswith("6") else "sz"
        code = raw
    return code, market


def _to_baostock_code(symbol: str) -> str:
    """将 "600519.SS" 转换为 baostock 格式 "sh.600519" """
    code, market = _strip_and_classify(symbol)
    return f"{market}.{code}"


def get_ak_stock_data(symbol: str, start_date: str, end_date: str) -> str:
    """
    获取 A 股日线 OHLCV 历史数据 (Baostock 引擎)。
    使用全局锁确保多线程环境下 Baostock 连接不冲突。
    """
    import baostock as bs

    bs_code = _to_baostock_code(symbol)

    with _BS_LOCK:   # ← 序列化，防止多线程同时 login 踩踏 socket
        lg = bs.login()
        try:
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2"   # 前复权
            )

            rows = []
            while rs.next():
                rows.append(rs.get_row_data())

        finally:
            bs.logout()

    if not rows:
        return f"No data returned from Baostock for {symbol}"

    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    df.set_index("Date", inplace=True)
    df.index = pd.to_datetime(df.index)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    header = f"# Baostock A-Share data for {symbol.upper()} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(df)}\n\n"
    return header + df.to_csv()


def get_ak_realtime_snapshot(symbol: str) -> dict:
    """获取 A 股最新一条数据作为实时快照（轻量版）"""
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    try:
        raw = get_ak_stock_data(symbol, today, today)
        lines = [l for l in raw.strip().split("\n") if not l.startswith("#") and l.strip()]
        if len(lines) < 2:
            return {"error": f"No realtime data for {symbol}"}
        parts = lines[-1].split(",")
        return {
            "symbol":     symbol.upper(),
            "last_price": float(parts[4]) if len(parts) > 4 else 0.0,
            "volume":     float(parts[5]) if len(parts) > 5 else 0.0,
        }
    except Exception as e:
        return {"error": str(e)}


def get_ak_fundamental_snapshot(symbol: str) -> dict:
    """获取 A 股关键基本面数据占位快照"""
    return {
        "is_valid":     True,
        "debtToEquity": 0.0,
        "currentRatio": 1.5,
    }
