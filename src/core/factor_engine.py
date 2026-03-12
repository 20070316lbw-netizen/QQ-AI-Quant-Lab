"""
factor_engine.py — O-Score 多因子独立信号引擎
================================================
职责：
  1. 对单股提取 O-Score 原始分（raw_score）
  2. 对股票池进行横截面 O-Score 排名，输出独立 BUY/SELL/HOLD 方向
  3. 提供仓位强度（基于 O-Score 分位数，与 Kronos 完全无关）

接口：
  FactorEngine.get_raw_score(ticker)       → dict (score breakdown)
  FactorEngine.rank_universe(signals_list) → list[dict] with factor_direction added
  FactorEngine.get_factor_signal(ticker)   → dict (standalone factor signal)

说明：
  O-Score 是横截面概念（依赖样本中其他股票的相对排名），
  因此 BUY/SELL 方向只能在有一批股票时才能确定。
  单独调用 get_factor_signal 时，方向为 None，仅提供 raw score 供后续排名使用。
"""

from __future__ import annotations
import math
from typing import Optional


class FactorEngine:
    """O-Score 多因子引擎，独立于 Kronos，纯基于财务/技术质量因子"""

    # ── 单股原始分提取 ────────────────────────────────────────
    @staticmethod
    def get_raw_score(ticker: str) -> dict:
        """
        提取单股的 O-Score 分解（value / quality / size / momentum / volatility）。
        返回: {overall_score, value_score, quality_score, size_score,
               momentum_score, volatility_score, error}
        """
        from core.multi_factor.factor_extractor import extract_raw_factors
        from core.multi_factor.scoring_engine import ScoringEngine
        from crawlers.data_gateway import DataGateway

        result = {
            "ticker": ticker,
            "overall_score": 50.0,
            "value_score": 50.0,
            "quality_score": 50.0,
            "size_score": 50.0,
            "momentum_score": 50.0,
            "volatility_score": 50.0,
            "error": None,
        }

        if DataGateway.offline_mode:
            result["error"] = "DataGateway offline"
            return result

        try:
            raw_factors = extract_raw_factors(ticker)
            scores = ScoringEngine.process(raw_factors)
            result.update({
                "overall_score":    scores.get("overall_score",   50.0),
                "value_score":      scores.get("value_score",     50.0),
                "quality_score":    scores.get("quality_score",   50.0),
                "size_score":       scores.get("size_score",      50.0),
                "momentum_score":   scores.get("momentum_score",  50.0),
                "volatility_score": scores.get("volatility_score", 50.0),
            })
        except Exception as e:
            result["error"] = str(e)

        return result

    # ── 横截面排名 + 方向赋予 ─────────────────────────────────
    @staticmethod
    def rank_universe(
        items: list[dict],
        o_score_key: str = "o_score",
        top_pct: float = 0.30,
        bottom_pct: float = 0.30,
    ) -> list[dict]:
        """
        对一批已有 o_score 的记录做横截面排名，赋予 factor_direction 字段。

        参数:
          items        : [{"ticker":..., "o_score":...}, ...] 形式的列表
          o_score_key  : o_score 字段名
          top_pct      : 前 top_pct 比例做多
          bottom_pct   : 后 bottom_pct 比例做空
          中间部分 → HOLD（不纳入交易）

        返回:
          每条记录增加：
            factor_direction          : "BUY" / "SELL" / "HOLD"
            factor_position_strength  : float [0, 1]（基于 O-Score 分位数）
            factor_percentile         : float [0, 1]（O-Score 在全体中的分位）
        """
        valid = [x for x in items if x.get(o_score_key) is not None]
        if not valid:
            return items

        sorted_items = sorted(valid, key=lambda x: x[o_score_key], reverse=True)
        n = len(sorted_items)
        top_k    = max(1, int(n * top_pct))
        bottom_k = max(1, int(n * bottom_pct))

        # 分位数映射：排在前面 → 高分位（强多）；排在后面 → 低分位（强空）
        for rank, item in enumerate(sorted_items):
            percentile = 1.0 - (rank / n)   # 1.0 = 最高 O-Score
            o = item[o_score_key]

            if rank < top_k:
                direction = "BUY"
                # 仓位强度：O-Score 越高、排名越前 → 强度越高
                strength = 0.5 + 0.5 * (o / 100.0)
            elif rank >= n - bottom_k:
                direction = "SELL"
                strength = 0.5 + 0.5 * (1.0 - o / 100.0)
            else:
                direction = "HOLD"
                strength = 0.0

            item["factor_direction"]         = direction
            item["factor_position_strength"] = round(min(1.0, strength), 4)
            item["factor_percentile"]        = round(percentile, 4)

        # 确保未进入排序（o_score 为 None）的记录也有字段
        for item in items:
            if "factor_direction" not in item:
                item["factor_direction"]         = "HOLD"
                item["factor_position_strength"] = 0.0
                item["factor_percentile"]        = 0.5

        return items

    # ── 单股独立信号（无横截面排名，方向为 None）────────────────
    @staticmethod
    def get_factor_signal(ticker: str) -> dict:
        """
        获取单股的因子信号（包含 raw score，但不含 BUY/SELL 方向）。
        方向需要通过 rank_universe() 进行横截面排名才能确定。
        """
        score_data = FactorEngine.get_raw_score(ticker)
        return {
            "ticker":          ticker,
            "engine":          "o_score_factor",
            "o_score":         score_data["overall_score"],
            "factor_scores":   {
                k: score_data[k]
                for k in ("value_score", "quality_score", "size_score",
                          "momentum_score", "volatility_score")
            },
            "direction":       None,   # 需要 rank_universe() 后才有意义
            "position_strength": None, # 同上
            "error":           score_data.get("error"),
        }

    # ── 合并用工具：给 Kronos 信号附加因子层 ─────────────────────
    @staticmethod
    def attach_factor_to_signals(
        signals: list[dict],
        top_pct: float = 0.30,
        bottom_pct: float = 0.30,
    ) -> list[dict]:
        """
        给 generate_signal() 的批量输出结果附加 factor_signal 子结构。
        核心逻辑：O-Score 排名完全独立于 Kronos 方向，不覆盖 direction 字段。
        结果中每条记录增加：
          signal["factor_signal"]["factor_direction"]
          signal["factor_signal"]["factor_position_strength"]
          signal["factor_signal"]["factor_percentile"]
        """
        # 从已有 metadata 中提取 o_score（避免重复 API 调用）
        items = []
        for sig in signals:
            o = (sig.get("metadata") or {}).get("multi_factor_o_score")
            items.append({"_sig_ref": sig, "o_score": o})

        ranked = FactorEngine.rank_universe(
            items, top_pct=top_pct, bottom_pct=bottom_pct
        )

        for item in ranked:
            sig = item["_sig_ref"]
            sig["factor_signal"] = {
                "direction":         item["factor_direction"],
                "position_strength": item["factor_position_strength"],
                "o_score_percentile": item["factor_percentile"],
                "o_score": item.get("o_score"),
            }

        return signals
