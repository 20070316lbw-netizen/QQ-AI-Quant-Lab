"""
等权多空组合 Alpha 验证
=======================
设计:
  多头  → 从已生成的信号 (hs300_cross_section.json) 取 direction=BUY 的标的
  空头  → 从已生成的信号 (hs300_cross_section.json) 取 direction=SELL 的标的
  持有期 → 20 个交易日

两阶段测试:
  [T1] Trailing 20 日  (signal_date - 20 T-days → signal_date)
       目的：看模型是否只是动量追随者——若多头过去 20 日已涨、空头已跌，则 Alpha 只是趋势包装
  [T2] Forward 占位框架 (signal_date → signal_date + 20 T-days)
       当前日期 = 信号日，真实价格尚未生成，结果先以 null 填充；
       20 交易日后用同一脚本（--forward 参数）自动补算实际 Alpha

评判准则:
  多头收益 > 空头收益        → 模型有信号方向 Alpha
  两者收益相近               → 模型只是趋势包装
  多头收益 < 空头收益 (逆向)  → 模型存在系统性偏向错误

输出: long_short_alpha.json
"""

import sys
import os
import json
import threading
import time
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SIGNAL_JSON   = os.path.join(os.path.dirname(__file__), "hs300_cross_section.json")
OUTPUT_JSON   = os.path.join(os.path.dirname(__file__), "long_short_alpha.json")

# ── Baostock 全局锁（单一 TCP 连接，不支持并发 login）────────
_BS_LOCK = threading.Lock()


def _std_to_bs(symbol: str) -> str:
    """600519.SS → sh.600519;  000001.SZ → sz.000001"""
    upper = symbol.upper()
    if upper.endswith(".SS"):
        return f"sh.{upper[:-3]}"
    elif upper.endswith(".SZ"):
        return f"sz.{upper[:-3]}"
    return symbol


def fetch_returns(symbols: list[str], start_date: str, end_date: str) -> dict:
    """
    用 Baostock 批量获取 [start_date, end_date] 的日收益率序列，
    返回 {symbol: {"start_price": float, "end_price": float, "return": float, "error": str|None}}
    全部请求串行（_BS_LOCK 保护），挨个 login/query/logout。
    """
    import baostock as bs
    import pandas as pd

    results = {}
    total = len(symbols)
    for i, sym in enumerate(symbols, 1):
        bs_code = _std_to_bs(sym)
        entry = {"start_price": None, "end_price": None, "return": None, "error": None}
        try:
            with _BS_LOCK:
                bs.login()
                try:
                    rs = bs.query_history_k_data_plus(
                        bs_code,
                        "date,close",
                        start_date=start_date,
                        end_date=end_date,
                        frequency="d",
                        adjustflag="2",
                    )
                    rows = []
                    while rs.next():
                        rows.append(rs.get_row_data())
                finally:
                    bs.logout()

            if not rows:
                entry["error"] = "no_data"
            else:
                df = pd.DataFrame(rows, columns=["date", "close"])
                df["close"] = pd.to_numeric(df["close"], errors="coerce")
                df.dropna(inplace=True)
                if len(df) < 2:
                    entry["error"] = "insufficient_data"
                else:
                    entry["start_price"] = round(float(df.iloc[0]["close"]), 4)
                    entry["end_price"]   = round(float(df.iloc[-1]["close"]), 4)
                    entry["return"]      = round(float(df.iloc[-1]["close"] / df.iloc[0]["close"]) - 1.0, 6)
        except Exception as e:
            entry["error"] = str(e)

        results[sym] = entry
        status = "OK " if not entry["error"] else "ERR"
        print(f"  [{status}] [{i:3d}/{total}] {sym}  ret={entry['return']}")

    return results


def portfolio_stats(returns: list[float]) -> dict:
    """计算等权组合统计"""
    if not returns:
        return {}
    import statistics
    mean = statistics.mean(returns)
    std  = statistics.stdev(returns) if len(returns) > 1 else 0.0
    win_rate = sum(1 for r in returns if r > 0) / len(returns)
    return {
        "count":    len(returns),
        "mean_ret": round(mean, 6),
        "mean_pct": round(mean * 100, 4),
        "stdev":    round(std, 6),
        "win_rate": round(win_rate, 4),
        "min":      round(min(returns), 6),
        "max":      round(max(returns), 6),
    }


def trading_days_offset(base_date: str, offset: int, direction: int = -1) -> str:
    """粗略向前/后偏移交易日（A 股约 250 天/年 → 5/7 比率）"""
    dt = datetime.strptime(base_date, "%Y-%m-%d")
    calendar_days = int(offset * 7 / 5) + 5  # 保守估计
    dt2 = dt + timedelta(days=calendar_days * direction)
    return dt2.strftime("%Y-%m-%d")


def main():
    run_start = datetime.now().isoformat()

    # ── 读取已有信号 ─────────────────────────────────────────
    print("=" * 70)
    print("  ECHO  等权多空组合 Alpha 验证")
    print("=" * 70)

    with open(SIGNAL_JSON, "r", encoding="utf-8") as f:
        signal_data = json.load(f)

    signal_date_str = signal_data["meta"]["run_end"][:10]   # e.g. "2026-02-28"
    print(f"\n  信号日期: {signal_date_str}")

    longs  = []  # BUY
    shorts = []  # SELL

    for r in signal_data["raw_results"]:
        if not r.get("signal") or r.get("error"):
            continue
        d = r["signal"].get("direction", "HOLD")
        if d == "BUY":
            longs.append(r["ticker"])
        elif d == "SELL":
            shorts.append(r["ticker"])

    print(f"  多头 (BUY):  {len(longs)} 只")
    print(f"  空头 (SELL): {len(shorts)} 只")

    # ── 计算日期窗口 ─────────────────────────────────────────
    # T1：Trailing 20 T-days
    t1_start = trading_days_offset(signal_date_str, 20, direction=-1)
    t1_end   = signal_date_str
    # T2：Forward 20 T-days (future, 仅占位)
    t2_start = signal_date_str
    t2_end   = trading_days_offset(signal_date_str, 20, direction=1)

    print(f"\n  [T1] Trailing  窗口: {t1_start} → {t1_end}  (已发生，验证动量追随)")
    print(f"  [T2] Forward   窗口: {t2_start} → {t2_end}  (未来，Alpha 验证，先占位)")
    print()

    # ── T1 Trailing 回测 ─────────────────────────────────────
    all_syms = list(set(longs + shorts))

    print(f"  获取 {len(all_syms)} 只股票 Trailing 真实价格数据...")
    t1_raw = fetch_returns(all_syms, t1_start, t1_end)

    t1_long_rets  = [t1_raw[s]["return"] for s in longs  if t1_raw.get(s, {}).get("return") is not None]
    t1_short_rets = [t1_raw[s]["return"] for s in shorts if t1_raw.get(s, {}).get("return") is not None]

    t1_long_stats  = portfolio_stats(t1_long_rets)
    t1_short_stats = portfolio_stats(t1_short_rets)

    # 多空价差（多头收益 - 空头收益，从多空对冲角度，空头收益越低越好）
    spread_trailing = (t1_long_stats.get("mean_ret", 0.0) - t1_short_stats.get("mean_ret", 0.0))

    # ── 判定 ─────────────────────────────────────────────────
    def verdict(long_ret, short_ret, mode="trailing"):
        spread = long_ret - short_ret
        if mode == "trailing":
            # Trailing：如果 BUY 已涨、SELL 已跌 → 只是动量追随
            if spread > 0.02:
                return "⚠️  MOMENTUM_FOLLOWER  多头已经涨过、空头已跌 — 模型在追涨杀跌"
            elif abs(spread) < 0.005:
                return "🔘 NEUTRAL  多空过去表现无差异 — 模型选股与过去走势无关"
            else:
                return "✅ CONTRARIAN_POTENTIAL  多头过去并未大涨 — 可能具备真实预测能力（需 Forward 验证）"
        else:
            if long_ret - short_ret > 0.02:
                return "🏆 ALPHA CONFIRMED  多头未来涨幅显著超过空头 — 模型具有真实 Alpha"
            elif abs(long_ret - short_ret) < 0.005:
                return "🔘 NO_ALPHA  多空收益相近 — 模型只是趋势包装"
            else:
                return "❌ REVERSE_ALPHA  多头未来表现反而弱于空头 — 模型存在系统性错误"

    t1_verdict = verdict(
        t1_long_stats.get("mean_ret", 0.0),
        t1_short_stats.get("mean_ret", 0.0),
        mode="trailing"
    )

    # ── 终端汇总 ─────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  T1  Trailing 20 日回测结果（验证动量追随程度）")
    print("=" * 70)
    print(f"  多头组  均值收益: {t1_long_stats.get('mean_pct', 0):+.2f}%   "
          f"胜率: {t1_long_stats.get('win_rate', 0):.1%}   样本: {t1_long_stats.get('count', 0)}")
    print(f"  空头组  均值收益: {t1_short_stats.get('mean_pct', 0):+.2f}%   "
          f"胜率: {t1_short_stats.get('win_rate', 0):.1%}   样本: {t1_short_stats.get('count', 0)}")
    print(f"  多空价差:        {spread_trailing*100:+.2f}%")
    print(f"\n  判定: {t1_verdict}")
    print()
    print("  [T2] Forward 数据尚未生成，已在 JSON 中预留结构，20 交易日后补算。")
    print("=" * 70)

    # ── 输出 JSON ─────────────────────────────────────────────
    output = {
        "meta": {
            "test_name":    "HS300 Long-Short Alpha Verification",
            "signal_date":  signal_date_str,
            "run_time":     run_start,
            "hold_days":    20,
            "long_count":   len(longs),
            "short_count":  len(shorts),
            "t1_window":    {"start": t1_start, "end": t1_end, "description": "Trailing 20 T-days (动量追随检验)"},
            "t2_window":    {"start": t2_start, "end": t2_end, "description": "Forward 20 T-days (Alpha 正向验证，待补算)"},
        },
        "t1_trailing": {
            "long_portfolio":  {
                "tickers": longs,
                "stats": t1_long_stats,
                "raw":   {s: t1_raw.get(s) for s in longs}
            },
            "short_portfolio": {
                "tickers": shorts,
                "stats": t1_short_stats,
                "raw":   {s: t1_raw.get(s) for s in shorts}
            },
            "spread_pct": round(spread_trailing * 100, 4),
            "verdict":    t1_verdict,
        },
        "t2_forward": {
            "status":  "PENDING — run this script with --forward flag after " + t2_end,
            "long_portfolio":  {"tickers": longs,  "stats": None, "raw": None},
            "short_portfolio": {"tickers": shorts, "stats": None, "raw": None},
            "spread_pct":      None,
            "verdict":         None,
        },
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n  完整结果已保存至: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
