"""
cap_aware_weights.py
====================
市值分层的 LambdaRank 推理权重配置。
基于 IC Decay 实证发现:
- HS300(大盘): 屏蔽 vol_60d_res 5d/20d 短线信号, 保留长线价值基因
- ZZ500(中盘): 降低 mom_60d 权重, 增强 vol_60d_res 防御权重

调仓频率决策 (2026-03-12):
  月度 (20d) vs 季度 (60d) 对比:
  - vol_60d_res(ZZ500): 20d t=-2.84 (峰值) >> 60d t=-2.37
  - mom_60d(HS300):     20d t=-2.18 (显著)  > 60d t=-1.82 (边际)
  - sp_ratio:           全周期均显著，不敏感
  ✅ 结论: 采用月度调仓 (20d)，三大基因在此频率下统一处于最优点。
"""

# 全局调仓频率配置 (单位: 交易日)
REBALANCE_FREQUENCY_DAYS = 20   # 月度调仓

# -----------------------------------------------------------
# HS300 (大盘) 推理权重配置
# 依据: vol_60d_res 在 HS300 短期 t-stat 仅 -0.75/-1.24, 不显著 (平时屏蔽)。
#       🚩 重要修正 (2026-03-12): 美股审计证实 Bear 状态下大盘 vol IC 高达 0.178。
#       策略: 状态机稳定后，需实现 if regime=='Bear' then weight=0.6 的动态逻辑。
#       sp_ratio 在全周期 t-stat > 2.2, 为长线核心锚点。
#       mom_60d 在 20d 周期 t=-2.18 显著 (反转效应，IC 为负)；
#       权重设为 -0.5 以确保 Alpha 得分与预期收益正相关。
# -----------------------------------------------------------
HS300_FEATURE_WEIGHTS = {
    "sp_ratio_rank":    1.0,   # 价值核心 (IC>0)
    "mom_60d_rank":    -0.5,   # 短期反转 (M_short, IC<0)
    "mom_12m_minus_1m_rank": 0.2, # 长期动量 (M_long, IC>0)
    "vol_60d_res_rank":-0.15,  # 屏蔽期低权
    "turn_20d_rank":    0.5,
}

# 大盘短线屏蔽开关 (5d/20d 持仓频率时生效)
HS300_SHORT_TERM_DISABLED = ["vol_60d_res_rank"]

# -----------------------------------------------------------
# ZZ500 (中盘) 推理权重配置
# 依据: vol_60d_res 在 ZZ500 20d 周期 t=-2.84, 显著有效 (低波效应，IC 为负)。
#       mom_60d 在 ZZ500 全周期 t < 1.96, 信号噪声较大 (反转效应，IC 为负)。
#       sp_ratio 在 ZZ500 120d IC = +0.103, 为最强慢基因 (价值效应，IC 为正)。
# -----------------------------------------------------------
ZZ500_FEATURE_WEIGHTS = {
    "sp_ratio_rank":    1.0,   # 万年长青 (IC>0)
    "mom_60d_rank":    -0.35,  # 中盘反转 (M_short, IC<0)
    "mom_12m_minus_1m_rank": 0.4, # 趋势核心 (M_long, IC>0)
    "vol_60d_res_rank":-0.9,   # 中盘防御核心 (IC<0)
    "turn_20d_rank":    0.5,
}

ZZ500_SHORT_TERM_DISABLED = []   # 中盘 vol 短线信号保留

# -----------------------------------------------------------
# 权重加载接口
# -----------------------------------------------------------
def get_weights(index_group: str, horizon_days: int = 20) -> dict:
    """
    根据市值组别和持有期返回因子权重。
    horizon_days: 5, 20, 60, 120
    """
    if index_group == "HS300":
        weights = HS300_FEATURE_WEIGHTS.copy()
        if horizon_days <= 20:
            # 大盘短线: 额外屏蔽 vol 信号
            for key in HS300_SHORT_TERM_DISABLED:
                if key in weights:
                    weights[key] = 0.0
        return weights
    elif index_group == "ZZ500":
        return ZZ500_FEATURE_WEIGHTS.copy()
    else:
        # 默认使用等权
        return {k: 0.6 for k in HS300_FEATURE_WEIGHTS}


if __name__ == "__main__":
    print("[HS300 短线 5d 权重]")
    w = get_weights("HS300", horizon_days=5)
    for k, v in w.items():
        print(f"  {k:25s}: {v}")

    print("\n[ZZ500 月度 20d 权重]")
    w = get_weights("ZZ500", horizon_days=20)
    for k, v in w.items():
        print(f"  {k:25s}: {v}")
