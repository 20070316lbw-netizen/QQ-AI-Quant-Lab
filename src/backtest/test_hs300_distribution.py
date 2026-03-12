"""
沪深 300 横截面分布测试
========================
测试目标：
  验证 Kronos 模型的信号分布是否健康——
  健康模型需具备强弱分化能力，而不是全部输出强趋势或全是弱信号。

核心指标（输出于 JSON + 终端）：
  - BUY / HOLD / SELL 比例
  - Z-Score 分布（均值、标准差、分位点）
  - adjusted_position_strength 分布
  - O-Score 分布
  - 预测振幅分布

数据源：
  - 成分股列表：Baostock query_hs300_stocks()
  - 信号生成：trading_signal.generate_signal（Kronos 引擎）
"""

import sys
import os
import json
import multiprocessing
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from trading_signal import generate_signal

OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "hs300_cross_section.json")

# ── 格式转换 ──────────────────────────────────────────────────
def baostock_to_std(bs_code: str) -> str:
    """sh.600519 → 600519.SS,   sz.000001 → 000001.SZ"""
    parts = bs_code.split(".")
    if len(parts) != 2:
        return bs_code
    market, code = parts
    suffix = "SS" if market == "sh" else "SZ"
    return f"{code}.{suffix}"


def get_hs300_tickers() -> list:
    """通过 baostock 获取当前沪深 300 成分股列表"""
    import baostock as bs
    today = date.today().strftime("%Y-%m-%d")
    with __import__("threading").Lock():
        pass  # 只是占位，实际在下面 login
    bs.login()
    try:
        rs = bs.query_hs300_stocks(date=today)
        tickers = []
        while rs.next():
            row = rs.get_row_data()
            # row = [date, code, code_name, ...]
            bs_code = row[1]   # e.g. "sh.600519"
            name    = row[2]   # e.g. "贵州茅台"
            std_code = baostock_to_std(bs_code)
            tickers.append((std_code, name))
    finally:
        bs.logout()
    return tickers


# ── 单标的执行 ────────────────────────────────────────────────
def run_single(args) -> dict:
    ticker, name = args
    result = {
        "ticker": ticker,
        "name":   name,
        "signal": None,
        "error":  None,
        "run_at": datetime.now().isoformat(),
    }
    try:
        raw = generate_signal(ticker)
        result["signal"] = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        result["error"] = str(e)
    return result


# ── 分布统计 ──────────────────────────────────────────────────
def compute_distribution_stats(values: list, label: str) -> dict:
    if not values:
        return {"label": label, "count": 0}
    sorted_v = sorted(values)
    n = len(sorted_v)
    return {
        "label":  label,
        "count":  n,
        "mean":   round(statistics.mean(values), 4),
        "stdev":  round(statistics.stdev(values) if n > 1 else 0.0, 4),
        "min":    round(sorted_v[0], 4),
        "p10":    round(sorted_v[int(n * 0.10)], 4),
        "p25":    round(sorted_v[int(n * 0.25)], 4),
        "p50":    round(sorted_v[int(n * 0.50)], 4),
        "p75":    round(sorted_v[int(n * 0.75)], 4),
        "p90":    round(sorted_v[int(n * 0.90)], 4),
        "max":    round(sorted_v[-1], 4),
    }


def bucket_z_scores(values: list) -> dict:
    """将 Z-Score 分桶统计"""
    buckets = {
        "strong_sell (<-1.5)":  0,
        "mild_sell (-1.5~-0.5)": 0,
        "neutral (-0.5~0.5)":   0,
        "mild_buy (0.5~1.5)":   0,
        "strong_buy (>1.5)":    0,
    }
    for z in values:
        if z < -1.5:
            buckets["strong_sell (<-1.5)"] += 1
        elif z < -0.5:
            buckets["mild_sell (-1.5~-0.5)"] += 1
        elif z <= 0.5:
            buckets["neutral (-0.5~0.5)"] += 1
        elif z <= 1.5:
            buckets["mild_buy (0.5~1.5)"] += 1
        else:
            buckets["strong_buy (>1.5)"] += 1
    total = len(values)
    return {k: {"count": v, "pct": round(v / total * 100, 1)} for k, v in buckets.items()}


def assess_health(z_scores: list, direction_counts: dict) -> dict:
    """评估模型分布健康度"""
    total = len(z_scores)
    if total == 0:
        return {"verdict": "NO_DATA"}

    strong = sum(1 for z in z_scores if abs(z) > 1.5)
    neutral = sum(1 for z in z_scores if abs(z) <= 0.5)
    strong_pct = strong / total
    neutral_pct = neutral / total

    buy_pct  = direction_counts.get("BUY", 0) / total
    sell_pct = direction_counts.get("SELL", 0) / total

    issues = []
    if strong_pct > 0.8:
        issues.append("⚠ 超过 80% 为强趋势信号，模型可能过度自信")
    if neutral_pct > 0.7:
        issues.append("⚠ 超过 70% 为中性信号，模型分辨能力不足")
    if buy_pct > 0.85 or sell_pct > 0.85:
        issues.append("⚠ 多空比例严重失衡，模型存在系统性偏向")
    if not issues:
        issues.append("✅ 信号分布基本健康，具备多空分化和强弱层次")

    return {
        "verdict":          "HEALTHY" if not any("⚠" in i for i in issues) else "WARNING",
        "strong_pct":       round(strong_pct * 100, 1),
        "neutral_pct":      round(neutral_pct * 100, 1),
        "buy_pct":          round(buy_pct * 100, 1),
        "sell_pct":         round(sell_pct * 100, 1),
        "observations":     issues,
    }


# ── 主入口 ────────────────────────────────────────────────────
def main():
    run_start = datetime.now().isoformat()
    print("=" * 70)
    print("  ECHO  沪深 300 横截面分布测试")
    print("  正在从 Baostock 拉取成分股列表...")
    print("=" * 70)

    tickers = get_hs300_tickers()
    total = len(tickers)
    print(f"\n  已加载 {total} 只成分股，启动 ThreadPool (8 线程) 并发推演...\n")

    results = []
    errors  = 0
    done_count = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(run_single, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            done_count += 1
            status = "OK " if not res["error"] else "ERR"
            print(f"  [{status}] [{done_count:3d}/{total}] {res['ticker']} ({res['name']})")
            if res["error"]:
                errors += 1

    # ── 提取各维度数值用于统计 ───────────────────────────────
    z_scores   = []
    pos_strs   = []
    o_scores   = []
    exp_rets   = []
    pred_rngs  = []
    uncertains = []
    direction_counts = {"BUY": 0, "SELL": 0, "HOLD": 0, "ERROR": 0}

    for r in results:
        if r["error"] or not r["signal"]:
            direction_counts["ERROR"] += 1
            continue
        s = r["signal"]
        direction = s.get("direction", "HOLD")
        direction_counts[direction] = direction_counts.get(direction, 0) + 1

        z = s.get("z_score")
        if z is not None:
            z_scores.append(float(z))

        ps = s.get("adjusted_position_strength")
        if ps is not None:
            pos_strs.append(float(ps))

        meta = s.get("metadata", {})
        os_val = meta.get("multi_factor_o_score")
        if os_val is not None:
            o_scores.append(float(os_val))

        er = s.get("mean_return") or s.get("expected_return")
        if er is not None:
            exp_rets.append(float(er))

        pr = s.get("predicted_range_pct")
        if pr is not None:
            pred_rngs.append(float(pr))

        uc = s.get("uncertainty")
        if uc is not None:
            uncertains.append(float(uc))

    # ── 组装统计结果 ─────────────────────────────────────────
    distribution = {
        "z_score":                    compute_distribution_stats(z_scores,  "Z-Score"),
        "adjusted_position_strength": compute_distribution_stats(pos_strs,  "仓位强度"),
        "o_score":                    compute_distribution_stats(o_scores,   "O-Score 多因子"),
        "expected_return":            compute_distribution_stats(exp_rets,   "预期收益"),
        "predicted_range_pct":        compute_distribution_stats(pred_rngs,  "预测振幅"),
        "uncertainty":                compute_distribution_stats(uncertains, "不确定性"),
    }

    z_buckets = bucket_z_scores(z_scores)
    health    = assess_health(z_scores, direction_counts)

    # ── 控制台汇总输出 ────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  信号分布汇总")
    print("=" * 70)
    print(f"  总标的: {total}   成功: {total - errors}   失败: {errors}")
    print(f"  BUY: {direction_counts.get('BUY', 0)}  |  SELL: {direction_counts.get('SELL', 0)}  |  HOLD: {direction_counts.get('HOLD', 0)}")
    print()
    print("  Z-Score 分桶分布:")
    for bucket, val in z_buckets.items():
        bar = "█" * int(val["pct"] / 2)
        print(f"    {bucket:<30} {val['count']:3d} ({val['pct']:5.1f}%) {bar}")
    print()
    print(f"  Z-Score 统计: mean={distribution['z_score'].get('mean','—')}, "
          f"std={distribution['z_score'].get('stdev','—')}, "
          f"min={distribution['z_score'].get('min','—')}, max={distribution['z_score'].get('max','—')}")
    print()
    print("  健康诊断:")
    for obs in health["observations"]:
        print(f"    {obs}")
    print()

    # ── 输出 JSON ─────────────────────────────────────────────
    output = {
        "meta": {
            "test_name":       "HS300 Kronos Cross-Section Distribution Test",
            "run_start":       run_start,
            "run_end":         datetime.now().isoformat(),
            "total":           total,
            "success":         total - errors,
            "errors":          errors,
            "direction_counts": direction_counts,
        },
        "health_assessment": health,
        "distribution":      distribution,
        "z_score_buckets":   z_buckets,
        "raw_results":       results,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"  完整结果已保存至: {OUTPUT_JSON}")
    print("=" * 70)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
