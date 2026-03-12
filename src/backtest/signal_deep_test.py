"""
signal_deep_test.py
====================
两项深度测试，均基于已有 JSON 数据，无需重跑 Kronos：

测试 1：Z-Score 分位数收益检验
  - 将 237 只股票按 z_score 从低到高分成 10 个十分位
  - 看各分位的平均真实收益（Trailing 20 日）
  - 若收益从低分位到高分位单调递增 → Kronos 方向正确
  - 若递减或中间高两侧低 → Kronos 是逆向/无效信号

测试 2：O-Score 独立策略（排序 + 仓位调整）
  - 按 O-Score 排序，做多 Top K% / 做空 Bottom K%
  - 同时按 O-Score 高低做非等权（O-Score 越高 → 多头仓位越大）
  - 比较不同 K 值（10%/20%/30%/40%）的多空价差
  - 判断 O-Score 策略是否在不同分档口径下都稳定正收益
"""

import json
import os
import statistics

BASE = os.path.dirname(__file__)
SIGNAL_JSON = os.path.join(BASE, "hs300_cross_section.json")
RETURN_JSON = os.path.join(BASE, "long_short_alpha.json")

# ── 数据加载 ──────────────────────────────────────────────────
with open(SIGNAL_JSON, "r", encoding="utf-8") as f:
    sig_data = json.load(f)

with open(RETURN_JSON, "r", encoding="utf-8") as f:
    ret_data = json.load(f)

# 构建实际收益映射
actual_returns = {}
for pk in ("long_portfolio", "short_portfolio"):
    for ticker, info in (ret_data["t1_trailing"][pk].get("raw") or {}).items():
        if info and info.get("return") is not None:
            actual_returns[ticker] = info["return"]

# 构建信号映射（只取有信号且有实际收益的）
records = []
for r in sig_data["raw_results"]:
    if r.get("signal") and not r.get("error"):
        t   = r["ticker"]
        sig = r["signal"]
        z   = sig.get("z_score")
        o   = (sig.get("metadata") or {}).get("multi_factor_o_score")
        ps  = sig.get("adjusted_position_strength", 0.5)
        ret = actual_returns.get(t)
        if z is not None and o is not None and ret is not None:
            records.append({
                "ticker":   t,
                "z_score":  z,
                "o_score":  o,
                "pos_str":  ps,
                "actual_ret": ret,
            })

records.sort(key=lambda x: x["z_score"])
N = len(records)
print(f"有效样本: {N} 只")


# ════════════════════════════════════════════════════════════
# 测试 1: Z-Score 十分位 → 实际收益检验
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("  测试 1: Z-Score 十分位收益检验（验证 Kronos 方向是否有效）")
print("=" * 72)
print(f"  {'十分位':6s} {'Z范围':26s} {'只数':5s} {'平均收益':10s} {'胜率':8s} {'方向'}  {'图示'}")
print("-" * 72)

deciles = []
bucket_size = N // 10
for i in range(10):
    start = i * bucket_size
    end   = start + bucket_size if i < 9 else N
    bucket = records[start:end]
    rets   = [x["actual_ret"] for x in bucket]
    z_lo   = bucket[0]["z_score"]
    z_hi   = bucket[-1]["z_score"]
    mean_r = statistics.mean(rets)
    win_r  = sum(1 for r in rets if r > 0) / len(rets)
    arrow  = "↑" if z_lo > 0 else "↓" if z_hi < 0 else "→"
    bar_len = int((mean_r + 0.12) * 200)
    bar = "█" * max(0, bar_len)
    label = f"D{i+1:02d} (低→高 {i+1}/10)"
    print(f"  {label:16s} [{z_lo:+8.2f} ~ {z_hi:+8.2f}]  "
          f"{len(bucket):3d}只  {mean_r*100:+7.2f}%   {win_r:.0%}   {arrow}   {bar}")
    deciles.append({"decile": i+1, "z_lo": z_lo, "z_hi": z_hi,
                    "count": len(bucket), "mean_ret": mean_r, "win_rate": win_r})

print()
# 相关性判断
low5  = statistics.mean(d["mean_ret"] for d in deciles[:5])   # 低 z_score 组
high5 = statistics.mean(d["mean_ret"] for d in deciles[5:])   # 高 z_score 组
spread_decile = high5 - low5
print(f"  低 Z-Score 组（D1-D5）平均收益: {low5*100:+.2f}%")
print(f"  高 Z-Score 组（D6-D10）平均收益: {high5*100:+.2f}%")
print(f"  高 Z - 低 Z 价差: {spread_decile*100:+.2f}%")
if spread_decile > 0.01:
    print("  ✅ Kronos 方向正向有效：z 越高 → 实际收益越好")
elif spread_decile < -0.01:
    print("  ⚠️  Kronos 方向反向：z 越高 → 实际收益反而越差（Trailing 动量逆向）")
else:
    print("  🔘 Kronos z_score 与真实收益无明显关联（Trailing 无效）")

# 最低分位 vs 最高分位
d1_ret  = deciles[0]["mean_ret"]
d10_ret = deciles[9]["mean_ret"]
print(f"\n  D1（最低 Z）平均收益: {d1_ret*100:+.2f}%")
print(f"  D10（最高 Z）平均收益: {d10_ret*100:+.2f}%")


# ════════════════════════════════════════════════════════════
# 测试 2: O-Score 独立策略（多个分档 + 仓位调整）
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("  测试 2: O-Score 独立策略（排序 + 等权 / O-Score 加权 各档对比）")
print("=" * 72)

sorted_by_o = sorted(records, key=lambda x: x["o_score"], reverse=True)

def o_strategy(k_pct: float, weighted: bool = False) -> dict:
    k = max(1, int(N * k_pct))
    top    = sorted_by_o[:k]
    bottom = sorted_by_o[-k:]

    def leg_ret(group):
        if weighted:
            total_w = sum(x["o_score"] for x in group)
            return sum(x["actual_ret"] * x["o_score"] for x in group) / total_w if total_w else 0
        return statistics.mean(x["actual_ret"] for x in group)

    lr = leg_ret(top)
    sr = leg_ret(bottom)
    spread = lr - sr

    top_wr    = sum(1 for x in top    if x["actual_ret"] > 0) / len(top)
    bottom_wr = sum(1 for x in bottom if x["actual_ret"] > 0) / len(bottom)

    return {
        "k_pct": k_pct, "k": k, "weighted": weighted,
        "long_ret":  round(lr * 100, 4),
        "short_ret": round(sr * 100, 4),
        "spread":    round(spread * 100, 4),
        "long_wr":   round(top_wr, 4),
        "short_wr":  round(bottom_wr, 4),
    }

k_list = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]

print(f"\n  O-Score 等权策略（Top/Bottom K%）:")
print(f"  {'K%':6s} {'多只':5s} {'多头':8s} {'空头':8s} {'价差':8s} {'结论'}")
print("-" * 72)
eq_results = []
for k in k_list:
    r = o_strategy(k, weighted=False)
    mark = "✅" if r["spread"] > 0 else "❌"
    print(f"  {k*100:5.0f}%  {r['k']:3d}只  {r['long_ret']:+7.2f}%  {r['short_ret']:+7.2f}%  {r['spread']:+7.2f}%  {mark}")
    eq_results.append(r)

print(f"\n  O-Score 加权策略（按 O-Score 值加权，Top/Bottom K%）:")
print(f"  {'K%':6s} {'多只':5s} {'多头':8s} {'空头':8s} {'价差':8s} {'结论'}")
print("-" * 72)
wt_results = []
for k in k_list:
    r = o_strategy(k, weighted=True)
    mark = "✅" if r["spread"] > 0 else "❌"
    print(f"  {k*100:5.0f}%  {r['k']:3d}只  {r['long_ret']:+7.2f}%  {r['short_ret']:+7.2f}%  {r['spread']:+7.2f}%  {mark}")
    wt_results.append(r)

# 最优分档
best_eq = max(eq_results, key=lambda x: x["spread"])
best_wt = max(wt_results, key=lambda x: x["spread"])
stable_eq = sum(1 for r in eq_results if r["spread"] > 0)
stable_wt = sum(1 for r in wt_results if r["spread"] > 0)

print(f"\n  等权最优分档：K={best_eq['k_pct']*100:.0f}%  价差 {best_eq['spread']:+.2f}%  "
      f"（{stable_eq}/{len(k_list)} 档正价差）")
print(f"  加权最优分档：K={best_wt['k_pct']*100:.0f}%  价差 {best_wt['spread']:+.2f}%  "
      f"（{stable_wt}/{len(k_list)} 档正价差）")

# 整体结论
print("\n" + "=" * 72)
print("  综合结论:")
if stable_eq >= 5:
    print(f"  ✅ O-Score 策略在 {stable_eq}/{len(k_list)} 个分档下均为正价差，选股能力稳定。")
elif stable_eq >= 3:
    print(f"  ⚠️  O-Score 策略在 {stable_eq}/{len(k_list)} 个分档有正价差，能力不稳定，对 K 值敏感。")
else:
    print(f"  ❌ O-Score 策略仅 {stable_eq}/{len(k_list)} 档为正价差，在当前样本可能无效。")

if spread_decile < -0.01:
    print(f"  ⚠️  Z-Score 反向特性确认（+z → -ret），Kronos 目前在 Trailing 窗口中是抄底型信号。")
    print("      需要等 Forward 数据验证其是否具备 Contrarian Alpha。")

# ── 保存 ──────────────────────────────────────────────────────
out = {
    "test_z_decile": {
        "description": "Z-Score 十分位 vs 实际收益（Trailing 20D）",
        "deciles": deciles,
        "low5_ret":  round(low5 * 100, 4),
        "high5_ret": round(high5 * 100, 4),
        "spread":    round(spread_decile * 100, 4),
    },
    "test_o_score": {
        "description": "O-Score 独立策略（等权 + 加权，多档 K 值）",
        "equal_weight": eq_results,
        "o_score_weighted": wt_results,
        "best_eq_k_pct":  best_eq["k_pct"],
        "best_wt_k_pct":  best_wt["k_pct"],
        "stable_eq_count": stable_eq,
        "stable_wt_count": stable_wt,
    },
}
out_path = os.path.join(BASE, "signal_deep_test.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\n  完整结果: {out_path}")
