"""
o_score_stability_test.py
==========================
O-Score 策略稳定性验证（Bootstrap 重采样）

测试逻辑：
  1. 对已有 237 只股票样本做 Bootstrap 重采样（有放回，N=500 次）
  2. 每次 Top/Bottom 30% 构建多空组合，计算多空价差
  3. 统计 spread 的均值、std、胜率、95% 置信区间
  4. t-stat 判断是否显著异于零
  5. 再做因子贡献拆解：哪个子分（value/quality/momentum）才是真正驱动力

补充验证：
  6. 单独测试各子因子的选股效果（用原始子分替换 overall_score 排名）
"""

import json
import os
import random
import math
import statistics

BASE = os.path.dirname(__file__)
SIGNAL_JSON = os.path.join(BASE, "hs300_cross_section.json")
RETURN_JSON = os.path.join(BASE, "long_short_alpha.json")

random.seed(2026)

# ── 数据加载 ──────────────────────────────────────────────────
with open(SIGNAL_JSON, "r", encoding="utf-8") as f:
    sig_data = json.load(f)

with open(RETURN_JSON, "r", encoding="utf-8") as f:
    ret_data = json.load(f)

actual_returns = {}
for pk in ("long_portfolio", "short_portfolio"):
    for ticker, info in (ret_data["t1_trailing"][pk].get("raw") or {}).items():
        if info and info.get("return") is not None:
            actual_returns[ticker] = info["return"]

records = []
for r in sig_data["raw_results"]:
    if not r.get("signal") or r.get("error"):
        continue
    sig = r["signal"]
    meta = sig.get("metadata") or {}
    fs   = meta.get("factor_scores") or {}
    t    = r["ticker"]
    ret  = actual_returns.get(t)
    if ret is None:
        continue
    records.append({
        "ticker":     t,
        "o_score":    meta.get("multi_factor_o_score", 50.0),
        "value":      fs.get("value_score",     50.0),
        "quality":    fs.get("quality_score",   50.0),
        "size":       fs.get("size_score",      50.0),
        "momentum":   fs.get("momentum_score",  50.0),
        "volatility": fs.get("volatility_score", 50.0),
        "actual_ret": ret,
    })

N = len(records)
print(f"有效样本: {N} 只")


# ── 工具函数 ───────────────────────────────────────────────────
def run_strategy(sample: list, score_key: str = "o_score", pct: float = 0.30) -> float | None:
    """对 sample 按 score_key 排序，前 pct 做多，后 pct 做空，返回多空价差"""
    valid = [x for x in sample if x.get(score_key) is not None]
    if not valid:
        return None
    sorted_s = sorted(valid, key=lambda x: x[score_key], reverse=True)
    n = len(sorted_s)
    k = max(1, int(n * pct))
    longs  = sorted_s[:k]
    shorts = sorted_s[-k:]
    if not longs or not shorts:
        return None
    lr = statistics.mean(x["actual_ret"] for x in longs)
    sr = statistics.mean(x["actual_ret"] for x in shorts)
    return lr - sr


def t_stat(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = statistics.mean(values)
    s = statistics.stdev(values)
    return m / (s / math.sqrt(n)) if s > 1e-9 else 0.0


def confidence_interval(values: list[float], ci: float = 0.95) -> tuple:
    sv = sorted(values)
    n  = len(sv)
    lo = sv[int(n * (1 - ci) / 2)]
    hi = sv[int(n * (1 - (1 - ci) / 2))]
    return lo, hi


# ════════════════════════════════════════════════════════════
# 测试 1: Bootstrap 稳定性（overall O-Score）
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("  测试 1: Bootstrap 重采样稳定性（N=500，Top/Bottom 30%）")
print("=" * 72)

N_BOOT = 500
boot_spreads = []
for _ in range(N_BOOT):
    sample = random.choices(records, k=N)  # 有放回采样
    spread = run_strategy(sample, "o_score", 0.30)
    if spread is not None:
        boot_spreads.append(spread)

boot_mean = statistics.mean(boot_spreads)
boot_std  = statistics.stdev(boot_spreads)
boot_wr   = sum(1 for s in boot_spreads if s > 0) / len(boot_spreads)
boot_t    = t_stat(boot_spreads)
ci_lo, ci_hi = confidence_interval(boot_spreads, 0.95)

print(f"\n  Bootstrap 均值价差:  {boot_mean*100:+.2f}%")
print(f"  Bootstrap 标准差:    {boot_std*100:.2f}%")
print(f"  Bootstrap 胜率:      {boot_wr:.1%}  （{sum(1 for s in boot_spreads if s>0)}/{len(boot_spreads)} 次正价差）")
print(f"  95% 置信区间:        [{ci_lo*100:+.2f}%, {ci_hi*100:+.2f}%]")
print(f"  t-statistic:         {boot_t:.3f}  {'✅ 显著 (|t|>2)' if abs(boot_t)>2 else '⚠️  不显著 (|t|<2)'}")
print(f"  原始样本实际价差:    +5.02%  {'（在置信区间内）' if ci_lo <= 0.0502 <= ci_hi else '（在置信区间外）'}")

if boot_mean > 0.01 and abs(boot_t) > 2:
    verdict = "✅ 策略统计显著，O-Score 在当前样本具有真实 Alpha 迹象"
elif boot_wr > 0.65:
    verdict = "⚠️  胜率高但置信度有限，需要更多时间点样本（目前仅 1 期）"
else:
    verdict = "❌ 在 95% 置信水平下不能排除偶然性"
print(f"\n  结论: {verdict}")


# ════════════════════════════════════════════════════════════
# 测试 2: 各子因子单独选股效果
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("  测试 2: 各子因子单独驱动力对比（全样本，Top/Bottom 30%）")
print("=" * 72)

factors = ["o_score", "value", "quality", "size", "momentum", "volatility"]
factor_results = {}

print(f"\n  {'因子':14s} {'多头':9s} {'空头':9s} {'价差':9s} {'贡献'}")
print("-" * 72)
for fac in factors:
    sorted_f = sorted(records, key=lambda x: x[fac], reverse=True)
    k = max(1, int(N * 0.30))
    longs  = sorted_f[:k]
    shorts = sorted_f[-k:]
    lr  = statistics.mean(x["actual_ret"] for x in longs)
    sr  = statistics.mean(x["actual_ret"] for x in shorts)
    sp  = lr - sr
    bar = "█" * max(0, int((sp + 0.02) * 200))
    mark = "✅" if sp > 0 else "❌"
    fname = fac.replace("_", " ").title()
    print(f"  {fname:14s}  {lr*100:+7.2f}%  {sr*100:+7.2f}%  {sp*100:+7.2f}%  {mark}  {bar}")
    factor_results[fac] = {"long_ret": lr, "short_ret": sr, "spread": sp}

best_factor = max(factor_results, key=lambda k: factor_results[k]["spread"])
print(f"\n  最强子因子: 【{best_factor.upper()}】  价差 {factor_results[best_factor]['spread']*100:+.2f}%")
print("  → 建议在 O-Score 权重设计上提高该因子的比重")


# ════════════════════════════════════════════════════════════
# 测试 3: 仓位加权 vs 等权（用 o_score 比例做权重）
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("  测试 3: 仓位方案对比（等权 / O-Score比例加权 / 极端值放大）")
print("=" * 72)

sorted_o = sorted(records, key=lambda x: x["o_score"], reverse=True)
k = max(1, int(N * 0.30))
top30    = sorted_o[:k]
bottom30 = sorted_o[-k:]

# 等权
eq_l = statistics.mean(x["actual_ret"] for x in top30)
eq_s = statistics.mean(x["actual_ret"] for x in bottom30)

# O-Score 比例加权（o_score / sum(o_score)）
w_top = [x["o_score"] for x in top30];     wt_l = sum(w_top)
w_bot = [(100 - x["o_score"]) for x in bottom30]; wt_b = sum(w_bot)
os_l = sum(x["actual_ret"] * x["o_score"] for x in top30) / wt_l if wt_l else 0
os_s = sum(x["actual_ret"] * (100-x["o_score"]) for x in bottom30) / wt_b if wt_b else 0

# 极端值放大：只取 O-Score 最高/最低 10%
k10 = max(1, int(N * 0.10))
ex_top = [sorted_o[i]["actual_ret"] for i in range(k10)]
ex_bot = [sorted_o[N - k10 + i]["actual_ret"] for i in range(k10)]
ex_l = statistics.mean(ex_top)
ex_s2 = statistics.mean(ex_bot)

schemes = [
    ("等权 30%", eq_l, eq_s),
    ("O-Score 比例加权 30%", os_l, os_s),
]
print(f"\n  {'方案':24s} {'多头':9s} {'空头':9s} {'价差':9s}")
print("-" * 72)
for name, l, s in schemes:
    sp = l - s
    mark = "✅" if sp > 0 else "❌"
    print(f"  {name:24s}  {l*100:+7.2f}%  {s*100:+7.2f}%  {sp*100:+7.2f}%  {mark}")

# 极端 10% 单独
ex_top = [sorted_o[i]["actual_ret"] for i in range(k10)]
ex_bot = [sorted_o[N - k10 + i]["actual_ret"] for i in range(k10)]
ex_l2 = statistics.mean(ex_top)
ex_s2 = statistics.mean(ex_bot)
sp2 = ex_l2 - ex_s2
mark2 = "✅" if sp2 > 0 else "❌"
label_ex = "极端 10% 集中"
print(f"  {label_ex:24s}  {ex_l2*100:+7.2f}%  {ex_s2*100:+7.2f}%  {sp2*100:+7.2f}%  {mark2}")


# ── 保存 ───────────────────────────────────────────────────
out = {
    "bootstrap": {
        "n_samples": N, "n_boot": N_BOOT,
        "mean_spread_pct": round(boot_mean*100, 4),
        "std_pct": round(boot_std*100, 4),
        "win_rate": round(boot_wr, 4),
        "t_stat": round(boot_t, 4),
        "ci_95_lo_pct": round(ci_lo*100, 4),
        "ci_95_hi_pct": round(ci_hi*100, 4),
        "verdict": verdict,
    },
    "sub_factors": {k: {kk: round(vv*100,4) if kk != "spread" else round(vv*100,4)
                        for kk, vv in v.items()} for k, v in factor_results.items()},
    "weighting_schemes": {
        "equal_weight_30pct": round((eq_l - eq_s)*100, 4),
        "o_score_weighted_30pct": round((os_l - os_s)*100, 4),
        "extreme_10pct": round(sp2*100, 4),
    }
}
out_path = os.path.join(BASE, "o_score_stability.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\n  结果已保存: {out_path}")
