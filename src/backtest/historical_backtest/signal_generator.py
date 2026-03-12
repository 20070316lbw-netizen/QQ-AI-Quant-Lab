"""
signal_generator.py
====================
月频信号生成器（研究级回测）

铁律遵守：
  - 每个信号日使用当时的沪深 300 成分股（Baostock Point-in-Time）
  - 历史数据截止于信号日，不偷看未来
  - 模型参数固定不变

并发设计：
  - ThreadPoolExecutor(8)：用于并发运行 Kronos 推理（CPU 密集）
  - Baostock 的成分股/价格查询走全局锁串行（单一 TCP 连接）
  - 断点续跑：每月完成后立即保存 signals_checkpoint/YYYY-MM.json
"""

import os
import json
import threading
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 全局 Baostock 锁 ─────────────────────────────────────────
_BS_LOCK = threading.Lock()

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "signals_checkpoint")
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


# ── Baostock 辅助 ────────────────────────────────────────────
def _bs_to_std(bs_code: str) -> str:
    """sh.600519 → 600519.SS"""
    parts = bs_code.split(".")
    if len(parts) != 2:
        return bs_code
    market, code = parts
    return f"{code}.{'SS' if market == 'sh' else 'SZ'}"


def get_hs300_on_date(signal_date: str) -> list:
    """返回 [(ticker, name), ...] 截至 signal_date 的沪深 300 成分股"""
    import baostock as bs
    with _BS_LOCK:
        bs.login()
        try:
            rs = bs.query_hs300_stocks(date=signal_date)
            rows = []
            while rs.next():
                r = rs.get_row_data()
                rows.append((_bs_to_std(r[1]), r[2]))
        finally:
            bs.logout()
    return rows


def get_last_trading_day(year: int, month: int) -> str:
    """获取指定年月最后一个交易日（通过 Baostock 交易日历）"""
    import baostock as bs
    import calendar
    # 先取当月最后一天
    last_day = calendar.monthrange(year, month)[1]
    start = f"{year}-{month:02d}-01"
    end   = f"{year}-{month:02d}-{last_day:02d}"
    with _BS_LOCK:
        bs.login()
        try:
            rs = bs.query_trade_dates(start_date=start, end_date=end)
            trading_days = []
            while rs.next():
                row = rs.get_row_data()
                # row[0] = date, row[1] = is_trading_day
                if row[1] == "1":
                    trading_days.append(row[0])
        finally:
            bs.logout()
    return trading_days[-1] if trading_days else end


def build_signal_dates(start_year: int, start_month: int,
                       end_year: int,   end_month: int) -> list:
    """生成所有月末最后交易日列表"""
    dates = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        dates.append(get_last_trading_day(y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return dates


# ── 单标的信号（线程安全）───────────────────────────────────
def _generate_one(ticker: str, name: str, signal_date: str) -> dict:
    """调用 generate_signal 并返回结构化结果（历史模式）"""
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from trading_signal import generate_signal

    result = {
        "signal_date": signal_date,
        "ticker":      ticker,
        "name":        name,
        "direction":   None,
        "z_score":     None,
        "regime":      None,
        "uncertainty": None,
        "adjusted_position_strength": None,
        "o_score":     None,
        "error":       None,
    }
    try:
        sig = generate_signal(ticker, as_of_date=signal_date)
        if isinstance(sig, str):
            sig = json.loads(sig)
        result.update({
            "direction":   sig.get("direction"),
            "z_score":     sig.get("z_score"),
            "regime":      sig.get("regime"),
            "uncertainty": sig.get("uncertainty"),
            "adjusted_position_strength": sig.get("adjusted_position_strength"),
            "o_score":     (sig.get("metadata") or {}).get("multi_factor_o_score"),
        })
    except Exception as e:
        result["error"] = str(e)
    return result


# ── 月频批量生成 ─────────────────────────────────────────────
def generate_monthly_signals(signal_date: str, max_workers: int = 8) -> list:
    """
    对 signal_date 当日的沪深 300 成分股生成信号。
    若该月检查点已存在，直接加载跳过。
    """
    ym = signal_date[:7]  # "2024-01"
    checkpoint_path = os.path.join(CHECKPOINT_DIR, f"{ym}.json")

    if os.path.exists(checkpoint_path):
        print(f"  [SKIP] {ym} 检查点已存在，加载中...")
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"\n  [SIGNAL] {signal_date} — 获取成分股...")
    tickers = get_hs300_on_date(signal_date)
    total   = len(tickers)
    print(f"           共 {total} 只，启动 {max_workers} 线程...")

    results = []
    done    = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_generate_one, t, n, signal_date): (t, n)
            for t, n in tickers
        }
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            done += 1
            status = "OK " if not res["error"] else "ERR"
            print(f"    [{status}] [{done:3d}/{total}] {res['ticker']}", flush=True)

    # 保存检查点
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"  [SAVED] {checkpoint_path}")

    return results
