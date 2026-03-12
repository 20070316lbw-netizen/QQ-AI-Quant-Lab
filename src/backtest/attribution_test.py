"""
attribution_test.py
====================
归因测试：Kronos vs 多因子 O-Score vs 随机基准

数据来源：
  - hs300_cross_section.json  → 每只股票的 z_score / o_score / direction / position_strength
  - long_short_alpha.json     → 每只股票的 Trailing 20 日真实收益率（已从 Baostock 拿到）

4 个变体：
  Full     : z_score 方向 + position_strength 加权（当前完整管道）
  Kronos   : z_score 方向 + 等权（纯 Kronos）
  Factor   : O-Score 排名前30% BUY / 后30% SELL + 等权（纯因子）
  Random   : 随机 BUY/SELL + 等权（零假设基准）

每个变体输出：
  多头均值收益 / 空头均值收益 / 多空价差 / 胜率（多>空）
"""

import json
import random
import statistics
import os

# ── 数据路径 ─────────────────────────────────────────────────
BASE = os.path.dirname(__file__)
SIGNAL_JSON = os.path.join(BASE, "hs300_cross_section.json")
RETURN_JSON = os.path.join(BASE, "long_short_alpha.json")

random.seed(42)

# ── 加载信号 ─────────────────────────────────────────────────
with open(SIGNAL_JSON, "r", encoding="utf-8") as f:
    sig_data = json.load(f)

# 构建 {ticker: signal_dict}
signals = {}
for r in sig_data["raw_results"]:
    if r.get("signal") and not r.get("error"):
        sig = r["signal"]
        signals[r["ticker"]] = {
            "z_score":     sig.get("z_score", 0.0),
            "o_score":     (sig.get("metadata") or {}).get("multi_factor_o_score", 50.0),
            "pos_strength": sig.get("adjusted_position_strength", 0.5),
            "direction":   sig.get("direction", "HOLD"),
        }

# ── 加载实际收益 ─────────────────────────────────────────────
with open(RETURN_JSON, "r", encoding="utf-8") as f:
    ret_data = json.load(f)

# 汇总多头和空头的实际 trailing 收益（合并两侧）
actual_returns = {}
for portfolio_key in ("long_portfolio", "short_portfolio"):
    raw = ret_data["t1_trailing"][portfolio_key].get("raw", {}) or {}
    for ticker, info in raw.items():
        if info and info.get("return") is not None:
            actual_returns[ticker] = info["return"]

# 只保留同时有信号和实际收益的股票
universe = [t for t in signals if t in actual_returns]
print(f"有效样本数: {len(universe)} 只")
print()


# ── 组合收益计算工具 ─────────────────────────────────────────
def eval_portfolio(longs: list, shorts: list, weights: dict = None) -> dict:
    """
    计算等权（或加权）多空组合，返回统计结果。
    weights: {ticker: float} 若为 None 则等权。
    """
    def weighted_mean(tickers):
        if not tickers:
            return None
        if weights:
            w_sum = sum(weights.get(t, 1.0) for t in tickers)
            return sum(actual_returns[t] * weights.get(t, 1.0) for t in tickers) / w_sum
        else:
            return statistics.mean(actual_returns[t] for t in tickers)

    long_ret  = weighted_mean(longs)
    short_ret = weighted_mean(shorts)
    spread    = (long_ret - short_ret) if (long_ret is not None and short_ret is not None) else None

    return {
        "long_count":  len(longs),
        "short_count": len(shorts),
        "long_ret_pct":  round(long_ret  * 100, 4) if long_ret  is not None else None,
        "short_ret_pct": round(short_ret * 100, 4) if short_ret is not None else None,
        "spread_pct":    round(spread    * 100, 4) if spread     is not None else None,
        "long_gt_short": spread is not None and spread > 0,
    }


# ── 变体 Full: z_score 方向 + position_strength 加权 ─────────
longs_full  = [t for t in universe if signals[t]["direction"] == "BUY"]
shorts_full = [t for t in universe if signals[t]["direction"] == "SELL"]
weights_full = {t: signals[t]["pos_strength"] for t in universe}
result_full = eval_portfolio(longs_full, shorts_full, weights=weights_full)

# ── 变体 Kronos: z_score 方向 + 等权 ─────────────────────────
result_kronos = eval_portfolio(longs_full, shorts_full, weights=None)

# ── 变体 Factor: O-Score 排序前/后30% + 等权 ─────────────────
sorted_by_o = sorted(universe, key=lambda t: signals[t]["o_score"], reverse=True)
k = max(1, int(len(sorted_by_o) * 0.30))
longs_factor  = sorted_by_o[:k]
shorts_factor = sorted_by_o[-k:]
result_factor = eval_portfolio(longs_factor, shorts_factor, weights=None)

# ── 变体 Random: 随机分组 + 等权 ─────────────────────────────
shuffled = universe[:]
random.shuffle(shuffled)
half = len(shuffled) // 2
longs_rand  = shuffled[:half]
shorts_rand = shuffled[half:]
result_random = eval_portfolio(longs_rand, shorts_rand, weights=None)


# ── 输出报告 ─────────────────────────────────────────────────
def fmt(r: dict, name: str):
    return (
        f"  {name:25s} | 多头 {r['long_count']:3d}只 {r['long_ret_pct']:+7.2f}%"
        f"  空头 {r['short_count']:3d}只 {r['short_ret_pct']:+7.2f}%"
        f"  价差 {r['spread_pct']:+7.2f}%"
        f"  {'✅多>空' if r['long_gt_short'] else '❌空>多'}"
    )

print("=" * 90)
print("  归因测试 — Trailing 20 日 (2026-01-26 → 2026-02-28)  样本：沪深300")
print("=" * 90)
print(f"  {'变体':25s} | 多头               空头               价差      结论")
print("-" * 90)
print(fmt(result_full,    "Full (Kronos + O-Score权重)"))
print(fmt(result_kronos,  "Kronos Only (等权)"))
print(fmt(result_factor,  "Factor Only (O-Score排序30%)"))
print(fmt(result_random,  "Random Baseline (等权)"))
print("=" * 90)

# 额外：多空绝对价差 ranking
print("\n  多空价差排名（越大 = 策略越优）:")
results = [
    ("Full (Kronos + O-Score)",  result_full["spread_pct"]),
    ("Kronos Only",              result_kronos["spread_pct"]),
    ("Factor Only (O-Score)",    result_factor["spread_pct"]),
    ("Random Baseline",          result_random["spread_pct"]),
]
for rank, (name, spread) in enumerate(sorted(results, key=lambda x: x[1], reverse=True), 1):
    bar = "█" * max(0, int((spread + 10) * 2))
    print(f"  #{rank}  {name:30s}  {spread:+.2f}%  {bar}")

# ── 因子贡献拆解 ────────────────────────────────────────────
factor_delta  = (result_factor["spread_pct"] or 0) - (result_random["spread_pct"] or 0)
kronos_delta  = (result_kronos["spread_pct"] or 0) - (result_random["spread_pct"] or 0)
full_delta    = (result_full["spread_pct"]   or 0) - (result_random["spread_pct"] or 0)

print("\n  相对随机基准的增量贡献（↑ = 有 Alpha 贡献）:")
print(f"  Kronos 方向贡献  = {kronos_delta:+.2f}%")
print(f"  Factor 排序贡献  = {factor_delta:+.2f}%")
print(f"  Full 管道总贡献  = {full_delta:+.2f}%")

# 推断组合增益
combo_expected = kronos_delta + factor_delta
synergy = full_delta - combo_expected
print(f"\n  若 Kronos 与 Factor 完全独立可叠加，理论总贡献 ≈ {combo_expected:+.2f}%")
print(f"  实际总贡献 {full_delta:+.2f}%  →  协同效应 = {synergy:+.2f}%")

print("\n  结论:")
main_driver = max([("Kronos", kronos_delta), ("O-Score 因子", factor_delta)], key=lambda x: x[1])
print(f"  主要 Alpha 贡献来自: 【{main_driver[0]}】（+{main_driver[1]:.2f}% vs 随机）")
if synergy > 0:
    print(f"  两者结合存在正向协同效应（叠加增益 +{synergy:.2f}%），组合优于各单独使用")
elif synergy < -0.5:
    print(f"  两者存在负向干扰（-{abs(synergy):.2f}%），可能存在信号冲突")
else:
    print(f"  两者基本线性叠加，无显著协同或对冲效应")

# ── 保存 JSON ────────────────────────────────────────────────
out = {
    "test": "Attribution Test — Trailing 20D",
    "universe_size": len(universe),
    "variants": {
        "full":    result_full,
        "kronos":  result_kronos,
        "factor":  result_factor,
        "random":  result_random,
    },
    "attribution": {
        "kronos_delta_pct": round(kronos_delta, 4),
        "factor_delta_pct": round(factor_delta, 4),
        "full_delta_pct":   round(full_delta, 4),
        "synergy_pct":      round(synergy, 4),
        "main_driver":      main_driver[0],
    }
}
out_path = os.path.join(BASE, "attribution_result.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\n  完整结果已保存: {out_path}")
